# RAG引擎模块 - 负责文档处理、向量化、检索和生成
import logging
import json
import re
import time
import os
from typing import List, Dict, Any, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from inquiryspring_backend.documents.models import Document, DocumentChunk
from .llm_client import LLMClientFactory
from .prompt_manager import PromptManager
from inquiryspring_backend.quiz.models import Quiz, Question
from django.conf import settings

logger = logging.getLogger(__name__)

VECTOR_STORE_DIR = os.path.join(settings.BASE_DIR, "vector_store")
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

class RAGEngine:
    """
    RAG引擎，提供三种核心AI服务：
    1. 聊天 (Chat): 支持有/无文档上下文的对话。
    2. 测验 (Quiz): 支持有/无文档上下文的测验生成，可理解自然语言需求。
    3. 摘要 (Summary): 必须有文档，为文档生成摘要。
    """
    DEFAULT_CONFIG = {
        'chunk_size': 1000, 'chunk_overlap': 100, 'top_k_retrieval': 3,
        'vector_store_dir': VECTOR_STORE_DIR, 'default_question_count': 5,
        'default_question_types': ['MC', 'TF'], 'default_difficulty': 'medium',
    }
    
    def __init__(self, document_id: int = None, llm_client = None, config: Dict = None):
        self.document = None
        self.vector_store = None
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
        if document_id:
            try: self.document = Document.objects.get(id=document_id)
            except Document.DoesNotExist: logger.error(f"文档ID {document_id} 不存在.")

        self.llm_client = llm_client or LLMClientFactory.create_client()
        self.embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")
        
        if self.document and self.document.is_processed:
            self._load_vector_store()

    # --- Public API ---

    def handle_chat(self, query: str, document_id: int = None, 
                    conversation_history: List[Dict[str, Any]] = None, 
                    user: Any = None, session_id: str = None) -> Dict[str, Any]:
        """统一处理聊天请求。"""
        start_time = time.time()
        
        if document_id and (not self.document or self.document.id != document_id):
            self.__init__(document_id=document_id, llm_client=self.llm_client, config=self.config)
            
        history = self._optimize_conversation_history(conversation_history or [], query)
        log_context = {'user': user, 'session_id': session_id, 'document': self.document}
        prompt_vars = {'query': query, 'conversation_history': self._format_conversation_history(history)}
        retrieved_chunks, has_doc_context = [], False

        if self.document:
            retrieved_chunks = self.retrieve_relevant_chunks(query)
            if retrieved_chunks:
                has_doc_context = True
                prompt_vars['reference_text'] = "\n\n---\n\n".join([c.content for c in retrieved_chunks])
                prompt_vars['chunk_ids'] = [c.id for c in retrieved_chunks]
                prompt_vars['chunk_positions'] = [f"第{c.chunk_index+1}段" for c in retrieved_chunks]

        prompt = PromptManager.render_by_type('chat', prompt_vars)
        system_prompt = "你是一个学习助手。请基于参考资料回答问题。" if has_doc_context else "你是一个学习助手。请清晰地回答问题。"
            
        llm_response = self.llm_client.generate_text(prompt=prompt, system_prompt=system_prompt, task_type="chat", **log_context)
        
        return {
            'answer': llm_response.get('text', '无法生成回答'),
            'sources': [{'id': c.id, 'content': c.content} for c in retrieved_chunks],
            'processing_time': time.time() - start_time,
            'is_generic_answer': not has_doc_context,
            'error': llm_response.get('error')
        }

    def handle_quiz(self, user_query: str, document_id: int = None, 
                    question_count: int = None, question_types: List[str] = None, difficulty: str = None, 
                    user: Any = None, session_id: str = None) -> Dict[str, Any]:
        """统一处理测验生成请求。"""
        if document_id and (not self.document or self.document.id != document_id):
            self.__init__(document_id=document_id, llm_client=self.llm_client, config=self.config)

        constraints = self._extract_quiz_constraints(user_query)
        if "error" in constraints: return constraints
            
        params = {
            'topic': constraints.get('topic', user_query),
            'user_requirements': user_query,
            'question_count': question_count or constraints.get('question_count') or self.config['default_question_count'],
            'question_types': question_types or constraints.get('question_types') or self.config['default_question_types'],
            'difficulty': difficulty or constraints.get('difficulty') or self.config['default_difficulty'],
            'user': user, 'session_id': session_id
        }
        
        generator = self._generate_quiz_with_doc if self.document else self._generate_quiz_without_doc
        return generator(**params)

    def handle_summary(self, document_id: int, user: Any = None, session_id: str = None) -> Dict[str, Any]:
        """处理摘要生成请求（必须有文档）。"""
        if not document_id: return {"error": "生成摘要必须提供文档ID。"}
        if not self.document or self.document.id != document_id:
            self.__init__(document_id=document_id, llm_client=self.llm_client, config=self.config)
        if not self.document: return {"error": f"找不到ID为 {document_id} 的文档。"}
        
        doc_content = self.document.content
        if self.document.file:
            try: doc_content = self.document.file.read().decode('utf-8')
            except Exception: pass
        
        prompt = PromptManager.render_by_type('summary', {'content': doc_content})
        system_prompt = "你是一个专业的文档分析和总结专家。"
        log_context = {'user': user, 'session_id': session_id, 'document': self.document}
        
        response = self.llm_client.generate_text(prompt=prompt, system_prompt=system_prompt, task_type='summary', **log_context)
        response['document_id'] = self.document.id
        return response

    # --- Document Processing ---
    def process_and_embed_document(self, force_reprocess: bool = False) -> bool:
        """处理并嵌入文档"""
        if not self.document: return False
        if self.document.is_processed and not force_reprocess:
            if not self.vector_store: self._load_vector_store()
            return True
        try:
            doc_content = self.document.content
            if self.document.file:
                try: doc_content = self.document.file.read().decode('utf-8')
                except Exception: pass
            if not doc_content: return False

            text_chunks = self._split_document(doc_content)
            self.document.chunks.all().delete()
            chunk_objects = [DocumentChunk(document=self.document, content=text, chunk_index=i) for i, text in enumerate(text_chunks)]
            DocumentChunk.objects.bulk_create(chunk_objects)
            
            persist_dir = os.path.join(self.config['vector_store_dir'], str(self.document.id))
            document_chunks = list(self.document.chunks.all())
            metadatas = [{'chunk_id': str(c.id)} for c in document_chunks]
            self.vector_store = Chroma.from_texts([c.content for c in document_chunks], self.embeddings, metadatas=metadatas, persist_directory=persist_dir)
            self.vector_store.persist()

            self.document.is_processed = True
            self.document.save()
            return True
        except Exception as e:
            logger.exception(f"处理文档失败: {e}")
            return False

    def retrieve_relevant_chunks(self, query: str) -> List[DocumentChunk]:
        """根据查询检索相关的文档分块"""
        if not self.vector_store: self._load_vector_store()
        if not self.vector_store: return []
        try:
            results = self.vector_store.similarity_search(query, k=self.config['top_k_retrieval'])
            chunk_ids = [doc.metadata.get('chunk_id') for doc in results]
            return list(DocumentChunk.objects.filter(id__in=[cid for cid in chunk_ids if cid]))
        except Exception as e:
            logger.exception(f"检索失败: {e}")
            return []

    # --- Private Helpers ---
    def _load_vector_store(self):
        persist_dir = os.path.join(self.config['vector_store_dir'], str(self.document.id))
        if os.path.exists(persist_dir):
            self.vector_store = Chroma(persist_directory=persist_dir, embedding_function=self.embeddings)

    def _split_document(self, content: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.config['chunk_size'], chunk_overlap=self.config['chunk_overlap'])
        return splitter.split_text(content)

    def _extract_quiz_constraints(self, user_query: str) -> Dict[str, Any]:
        system_prompt = """从用户请求中提取测验的主题、题型、难度和数量。按以下JSON格式返回：
        {"topic": "主题", "question_types": ["MC"], "difficulty": "medium", "question_count": 5}"""
        response = self.llm_client.generate_text(prompt=user_query, system_prompt=system_prompt, task_type='quiz')
        try:
            # 解析响应并确保它是一个字典
            parsed_result = self._parse_json_from_response(response.get("text", "{}"))
            
            # 如果解析结果不是字典（例如是列表或其他类型），返回默认字典
            if not isinstance(parsed_result, dict):
                logger.warning(f"解析测验约束时得到了非字典结果: {type(parsed_result)}，使用默认字典")
                return {"topic": user_query}
                
            return parsed_result
        except Exception as e:
            logger.exception(f"提取测验约束时出错: {e}")
            return {"topic": user_query}

    def _generate_quiz_with_doc(self, **kwargs) -> Dict[str, Any]:
        relevant_chunks = self.retrieve_relevant_chunks(kwargs['topic'])
        if not relevant_chunks: return {"error": "未找到相关内容。"}
        kwargs['reference_text'] = "\n\n".join([chunk.content for chunk in relevant_chunks])
        return self._call_quiz_llm(**kwargs)
        
    def _generate_quiz_without_doc(self, **kwargs) -> Dict[str, Any]:
        kwargs.pop('reference_text', None)
        return self._call_quiz_llm(**kwargs)

    def _call_quiz_llm(self, **kwargs) -> Dict[str, Any]:
        prompt = PromptManager.render_by_type('quiz', kwargs)
        system_prompt = "你是一个测验出题专家。请严格按照JSON格式生成题目。"
        log_context = {'user': kwargs.get('user'), 'session_id': kwargs.get('session_id'), 'document': self.document}
        response = self.llm_client.generate_text(prompt, system_prompt=system_prompt, task_type='quiz', **log_context)
        return self._process_quiz_response(response, kwargs.get('topic'), kwargs.get('difficulty'))

    def _process_quiz_response(self, response: Dict, topic: str, difficulty: str) -> Dict:
        try:
            quiz_data = self._parse_json_from_response(response.get("text", "[]"))
            quiz_title = f"{self.document.title} - {topic}" if self.document else topic
            quiz_obj = Quiz.objects.create(document=self.document, title=quiz_title, difficulty_level=difficulty, total_questions=len(quiz_data))
            for i, q_data in enumerate(quiz_data):
                # 字段映射：将 "type" 映射到 "question_type"
                if 'type' in q_data:
                    q_data['question_type'] = q_data.pop('type')
                
                Question.objects.create(quiz=quiz_obj, **q_data, order=i + 1)
            response.update({'quiz_id': quiz_obj.id, 'quiz_data': quiz_data})
        except Exception as e:
            logger.error(f"处理测验数据失败: {e}")
            response.update({'error': "解析或保存测验失败", 'quiz_data': []})
        return response

    def _parse_json_from_response(self, text: str) -> Any:
        """解析LLM响应中的JSON，处理各种格式和注释"""
        # 首先尝试从Markdown代码块中提取JSON
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
        json_str = match.group(1) if match else text
        
        # 移除JSON注释 (// 和 /* */ 形式的注释)
        json_str = re.sub(r'//.*?$', '', json_str, flags=re.MULTILINE)  # 移除单行注释
        json_str = re.sub(r'/\*.*?\*/', '', json_str, flags=re.DOTALL)  # 移除多行注释
        
        # 处理尾随逗号
        json_str = re.sub(r',(\s*[\]}])', r'\1', json_str)
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败: {e}, 尝试进一步清理")
            # 进一步尝试清理，移除可能导致问题的所有非标准JSON内容
            # 移除所有注释形式的行
            clean_lines = []
            for line in json_str.split('\n'):
                if not re.search(r'^\s*//|^\s*/\*|\*/', line):
                    clean_lines.append(line)
            clean_json = '\n'.join(clean_lines)
            
            try:
                return json.loads(clean_json)
            except json.JSONDecodeError:
                # 如果仍然失败，返回空列表或空字典
                logger.error(f"JSON解析彻底失败，返回空结果")
                return [] if json_str.strip().startswith('[') else {}

    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        return "\n\n".join([f"{'用户' if m.get('is_user') else '助手'}: {m.get('content')}" for m in history])

    def _optimize_conversation_history(self, history: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        return history[-10:]

def initialize_ai_services():
    """初始化所有AI服务相关组件"""
    try:
        # 初始化提示词模板
        from .prompt_manager import PromptManager
        logger.info("正在初始化提示词模板...")
        PromptManager.create_default_templates()
        
        # 确保向量存储目录存在
        os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
        
        # 初始化默认的LLM客户端（验证连接）
        from .llm_client import LLMClientFactory
        logger.info("正在初始化LLM客户端...")
        client = LLMClientFactory.create_client()
        
        # 检查本地模型路径是否有效
        local_model_path = os.environ.get('LOCAL_MODEL_PATH')
        if local_model_path and os.path.exists(local_model_path):
            logger.info(f"检测到有效的本地模型路径: {local_model_path}")
        
        # 检查是否需要处理未处理的文档
        from inquiryspring_backend.documents.models import Document
        unprocessed_docs = Document.objects.filter(is_processed=False).count()
        if unprocessed_docs > 0:
            logger.info(f"发现 {unprocessed_docs} 个未处理的文档。可以使用process_documents管理命令进行处理。")
        
        logger.info("AI服务初始化完成。")
    except Exception as e:
        logger.exception(f"初始化AI服务时出错: {e}")