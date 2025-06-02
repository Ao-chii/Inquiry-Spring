"""
RAG引擎模块 - 负责文档处理、向量化、检索和生成
"""
import logging
import json
import re
import time
import os
from typing import List, Dict, Any, Optional

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_huggingface import HuggingFaceEmbeddings  # 新版本导入方式
from langchain.chains import RetrievalQA

from apps.documents.models import Document, DocumentChunk
from .llm_client import LLMClientFactory
from .prompt_manager import PromptManager
from apps.quiz.models import Quiz, Question
from django.conf import settings

logger = logging.getLogger(__name__)

# 创建向量存储的根目录
VECTOR_STORE_DIR = os.path.join(settings.BASE_DIR, "vector_store")
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)

class RAGEngine:
    """
    RAG引擎，用于处理文档和生成答案
    
    主要功能:
    1. 文档处理：将文档分割成块并向量化存储
    2. 检索功能：根据查询检索相关文档块
    3. 答案生成：根据检索结果生成回答
    4. 测验生成：基于文档或主题生成测验题目
    5. 摘要生成：为文档生成摘要
    6. 对话管理：支持多轮对话和上下文维护
    
    多轮对话使用说明:
    - 对话历史格式: 列表，每个元素是包含 'is_user'(布尔值) 和 'content'(字符串) 的字典
    - 例如: [{'is_user': True, 'content': '用户问题'}, {'is_user': False, 'content': '系统回答'}]
    - 使用 process_chat_query 方法处理对话，自动处理有/无文档情况
    - 系统会自动优化长对话历史，包括过滤不相关内容和生成摘要
    """
    
    # 默认配置参数
    DEFAULT_CONFIG = {
        # 文档处理参数
        'chunk_size': 1000,  # 文本块大小
        'chunk_overlap': 100,  # 文本块重叠大小
        
        # 检索参数
        'top_k_retrieval': 3,  # 检索结果数量
        'retrieval_threshold': 0.6,  # 检索相似度阈值
        
        # 向量数据库
        'vector_store_dir': VECTOR_STORE_DIR,  # 向量存储目录
        
        # 测验生成参数
        'default_question_count': 5,  # 默认题目数量
        'default_question_types': ['MC', 'TF'],  # 默认题型
        'default_difficulty': 'medium',  # 默认难度
        
        # 摘要生成参数
        'default_summary_length': 'medium',  # 默认摘要长度
        'default_include_outline': True,  # 默认是否包含大纲
    }
    
    def __init__(self, document_id: int = None, llm_client = None, config: Dict = None):
        self.document = None
        self.document_chunks = []
        self.vector_store = None
        
        # 合并配置
        self.config = self.DEFAULT_CONFIG.copy()
        if config:
            self.config.update(config)
        
        if document_id:
            try:
                self.document = Document.objects.get(id=document_id)
                self.document_chunks = list(self.document.chunks.all())
            except Document.DoesNotExist:
                logger.error(f"文档ID {document_id} 不存在.")
                # 可以选择抛出异常或允许在没有文档的情况下初始化

        # 初始化LLM客户端
        self.llm_client = llm_client if llm_client else LLMClientFactory.create_client()
        
        # 修改嵌入模型初始化
        self.embeddings = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-mpnet-base-v2"  # 明确指定模型名称
        )
        
        # 如果文档已处理，则加载向量存储
        if self.document and self.document.is_processed and self.document_chunks:
            self._load_vector_store()

    def _split_document(self, content: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
        """将文档内容分割成文本块"""
        if chunk_size is None:
            chunk_size = self.config['chunk_size']
        if chunk_overlap is None:
            chunk_overlap = self.config['chunk_overlap']
            
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
        )
        chunks = text_splitter.split_text(content)
        return chunks

    def process_and_embed_document(self, force_reprocess: bool = False) -> bool:
        """处理并嵌入文档"""
        if not self.document:
            logger.error("未加载文档，无法处理。")
            return False

        if self.document.is_processed and not force_reprocess:
            logger.info(f"文档 {self.document.title} 已处理，跳过。")
            if not self.vector_store:
                self._load_vector_store()
            return True

        try:
            logger.info(f"开始处理文档: {self.document.title}")
            
            # 1. 获取文档内容 (优先使用文件内容，其次是文本内容字段)
            doc_content = ""
            if self.document.file:
                try:
                    doc_content = self.document.file.read().decode('utf-8')
                except Exception as e:
                    logger.error(f"读取文件内容失败: {e}")
                    doc_content = self.document.content # 后备方案
            else:
                doc_content = self.document.content
            
            if not doc_content:
                logger.error(f"文档 {self.document.title} 内容为空，无法处理。")
                return False

            # 2. 分割文档
            text_chunks = self._split_document(doc_content)
            if not text_chunks:
                logger.error(f"文档 {self.document.title} 分块失败。")
                return False

            # 3. 清理旧的文档分块 (如果存在)
            self.document.chunks.all().delete()
            self.document_chunks = []

            # 4. 创建并存储DocumentChunk对象
            chunk_objects = []
            current_char_offset = 0
            for i, chunk_text in enumerate(text_chunks):
                chunk_obj = DocumentChunk(
                    document=self.document,
                    content=chunk_text,
                    chunk_index=i,
                    start_char=current_char_offset,
                    end_char=current_char_offset + len(chunk_text) -1
                )
                chunk_objects.append(chunk_obj)
                current_char_offset += len(chunk_text)
            
            DocumentChunk.objects.bulk_create(chunk_objects)
            self.document_chunks = list(self.document.chunks.all())
            logger.info(f"文档 {self.document.title} 分块完成，共 {len(self.document_chunks)} 块。")

            # 5. 创建或更新向量存储
            # 使用Chroma作为向量数据库并启用持久化
            persist_directory = os.path.join(self.config['vector_store_dir'], str(self.document.id))
            os.makedirs(persist_directory, exist_ok=True)
            
            # 为每个chunk准备metadata，包含chunk_id和document_id
            metadatas = [{'chunk_id': str(chunk.id), 'document_id': str(self.document.id)} for chunk in self.document_chunks]
            
            self.vector_store = Chroma.from_texts(
                texts=[chunk.content for chunk in self.document_chunks],
                embedding=self.embeddings,
                ids=[str(chunk.id) for chunk in self.document_chunks],  # 使用DocumentChunk的ID作为向量ID
                metadatas=metadatas,  # 添加元数据以便检索时能够直接获取chunk_id
                persist_directory=persist_directory  # 启用持久化
            )
            # 持久化到磁盘
            self.vector_store.persist()
            logger.info(f"文档 {self.document.title} 向量化完成并持久化到 {persist_directory}。")

            # 6. 更新文档状态
            self.document.is_processed = True
            self.document.save()
            
            return True

        except Exception as e:
            logger.exception(f"处理文档 {self.document.title} 失败: {e}")
            self.document.is_processed = False # 出错时标记为未处理
            self.document.save()
            return False

    def _load_vector_store(self):
        """从持久化存储加载向量数据库"""
        if not self.document or not self.document.is_processed:
            logger.warning("无法加载向量存储：文档未处理。")
            return

        try:
            logger.info(f"加载文档 {self.document.title} 的向量存储...")
            
            # 检查持久化目录是否存在
            persist_directory = os.path.join(self.config['vector_store_dir'], str(self.document.id))
            if os.path.exists(persist_directory):
                # 从持久化目录加载向量存储
                self.vector_store = Chroma(
                    persist_directory=persist_directory,
                    embedding_function=self.embeddings
                )
                logger.info(f"从持久化目录 {persist_directory} 加载向量存储成功。")
            else:
                logger.warning(f"持久化向量存储目录 {persist_directory} 不存在，重新创建")
                # 如果持久化目录不存在，重新嵌入
                if self.document_chunks:
                    success = self.process_and_embed_document(force_reprocess=True)
                    if not success:
                        logger.error("重新创建向量存储失败")
                else:
                    logger.error("文档没有分块，无法创建向量存储")

        except Exception as e:
            logger.exception(f"加载向量存储失败: {e}")
            self.vector_store = None # 加载失败则清空

    def retrieve_relevant_chunks(self, query: str, top_k: int = 3) -> List[DocumentChunk]:
        """根据查询检索相关的文档分块"""
        if not self.vector_store:
            logger.warning("向量存储未初始化，无法检索。")
            # 尝试加载或处理文档
            if self.document and not self.document.is_processed:
                success = self.process_and_embed_document()
                if not success or not self.vector_store:
                    return []
            elif self.document and self.document.is_processed and not self.vector_store:
                 self._load_vector_store()
                 if not self.vector_store:
                     return []
            else:
                return []

        try:
            # 从向量存储中检索相似文档
            retrieved_langchain_docs = self.vector_store.similarity_search_with_score(query, k=top_k)
            
            # 使用metadata中的chunk_id直接获取DocumentChunk对象
            retrieved_chunks = []
            for lc_doc, score in retrieved_langchain_docs:
                try:
                    # 从metadata中获取chunk_id
                    chunk_id = lc_doc.metadata.get('chunk_id')
                    
                    if chunk_id:
                        # 通过ID从数据库获取DocumentChunk
                        chunk = DocumentChunk.objects.get(id=chunk_id)
                        # 添加相似度分数作为临时属性
                        chunk.similarity_score = score
                        retrieved_chunks.append(chunk)
                    else:
                        # 后备方案：通过内容匹配（低效）
                        logger.warning("检索结果中未找到chunk_id，使用内容匹配")
                        matched_chunk = next((c for c in self.document_chunks if c.content == lc_doc.page_content), None)
                        if matched_chunk:
                            matched_chunk.similarity_score = score
                            retrieved_chunks.append(matched_chunk)
                        else:
                            logger.warning(f"无法匹配检索结果: {lc_doc.page_content[:100]}...")
                except DocumentChunk.DoesNotExist:
                    logger.warning(f"检索到的chunk ID {chunk_id} 在数据库中不存在")
                except Exception as e:
                    logger.error(f"从检索结果映射回DocumentChunk时出错: {e}")
            
            logger.info(f"为查询 '{query}' 检索到 {len(retrieved_chunks)} 个相关分块。")
            return retrieved_chunks
        
        except Exception as e:
            logger.exception(f"检索相关分块失败: {e}")
            return []

    def _format_conversation_history(self, conversation_history: List[Dict[str, Any]], max_rounds: int = 5) -> str:
        """
        格式化对话历史为提示词中可用的格式
        
        Args:
            conversation_history: 对话历史列表，支持两种格式:
                1. [{'is_user': bool, 'content': str}, ...]
                2. [{'role': 'user'/'assistant', 'content': str}, ...]
            max_rounds: 最多保留的对话轮数
            
        Returns:
            格式化的对话历史字符串
        """
        if not conversation_history:
            return ""
            
        # 限制历史长度，避免超过token限制
        recent_history = conversation_history[-max_rounds*2:] if len(conversation_history) > max_rounds*2 else conversation_history
        
        formatted = ""
        for msg in recent_history:
            # 处理不同格式的对话历史
            if 'is_user' in msg:
                role = "用户" if msg.get('is_user', False) else "助手"
            elif 'role' in msg:
                role = "用户" if msg.get('role', '') == 'user' else "助手"
            else:
                # 无法确定角色时的默认处理
                logger.warning("对话历史消息缺少角色信息，默认设为用户")
                role = "未知"
                
            content = msg.get('content', '').strip()
            if content:
                formatted += f"{role}: {content}\n\n"
        
        return formatted.strip()
    
    def answer_query_with_history(self, query: str, conversation_history: List[Dict[str, Any]], 
                                 top_k_retrieval: int = None) -> Dict[str, Any]:
        """
        基于对话历史回答用户查询
        
        Args:
            query: 当前用户查询
            conversation_history: 对话历史列表，每个项目包含 {'is_user': bool, 'content': str}
            top_k_retrieval: 检索结果数量
            
        Returns:
            包含生成答案的字典
        """
        if top_k_retrieval is None:
            top_k_retrieval = self.config['top_k_retrieval']
        
        start_time = time.time()
        
        try:
            # 1. 提取对话历史以构建上下文
            formatted_history = self._format_conversation_history(conversation_history)
            
            # 2. 准备变量字典
            variables = {
                'query': query,
                'conversation_history': formatted_history
            }
            
            # 3. 如果有文档，检索相关文档块并添加到变量中
            has_document_context = False
            if self.document:
                relevant_chunks = self.retrieve_relevant_chunks(query, top_k=top_k_retrieval)
                if relevant_chunks:
                    has_document_context = True
                    references = "\n\n".join([chunk.content for chunk in relevant_chunks])
                    variables['reference_text'] = references
                    
                    # 保存检索到的文档块，用于返回源引用
                    retrieved_chunks = relevant_chunks
                else:
                    # 文档存在但没有检索到相关内容
                    retrieved_chunks = []
            else:
                # 无文档模式
                retrieved_chunks = []
            
            # 4. 使用带有对话历史的聊天提示模板
            prompt = PromptManager.render_by_type('chat_with_history_response', variables)
            
            # 5. 调用LLM生成答案
            result = self.llm_client.generate_text(
                prompt=prompt,
                task_type="chat"
            )
            
            processing_time = time.time() - start_time
            
            # 6. 准备返回结果
            response = {
                'answer': result.get('text', '无法生成回答'),
                'sources': [{'chunk_id': chunk.id, 'content': chunk.content[:200] + '...' if len(chunk.content) > 200 else chunk.content} 
                           for chunk in retrieved_chunks],
                'processing_time': processing_time,
                'is_generic_answer': not has_document_context
            }
            
            return response
            
        except Exception as e:
            logger.exception(f"使用对话历史回答查询失败: {str(e)}")
            processing_time = time.time() - start_time
            
            return {
                'answer': f"生成回答时出错: {str(e)}",
                'sources': [],
                'processing_time': processing_time,
                'error': str(e),
                'is_generic_answer': True
            }

    def generate_answer(self, query: str, relevant_chunks: List[DocumentChunk]) -> Dict[str, Any]:
        """根据查询和相关文档块生成答案"""
        if not relevant_chunks:
            # 如果没有相关文档，可以直接调用LLM进行通用回答，或返回特定提示
            logger.info("没有检索到相关文档，尝试通用回答。")
            # 可以选择使用一个特定的"无上下文"提示词模板
            prompt = PromptManager.render_by_type(
                template_type='chat_response', 
                variables={'query': query, 'reference_text': '没有可用的特定上下文信息。'}
            )
            system_prompt = "你是一个专业的学习助手。请基于你的知识尽可能准确地回答用户的问题，明确指出这是基于你的知识而非特定文档的回答。"
        else:
            context_text = "\n\n---\n\n".join([chunk.content for chunk in relevant_chunks])
            prompt_variables = {
                'query': query,
                'reference_text': context_text
            }
            prompt = PromptManager.render_by_type(
                template_type='chat_response', 
                variables=prompt_variables
            )
            system_prompt = "你是一个专业的学习助手。请基于提供的参考资料回答用户的问题。只使用参考资料中的信息，不要编造内容。如果参考资料中没有足够的信息，请坦诚告知。每当引用参考资料中的内容时，请标明信息来源。"

        # 使用LLM客户端生成答案，传递系统提示词
        response = self.llm_client.generate_text(
            prompt=prompt, 
            system_prompt=system_prompt,
            task_type='chat'
        )
        
        # 可以在这里添加答案的后处理逻辑，比如提取引用等
        response['retrieved_chunks'] = [
            {'id': chunk.id, 'content': chunk.content[:200] + "..."} for chunk in relevant_chunks
        ]
        
        return response

    def answer_query(self, query: str, top_k_retrieval: int = None) -> Dict[str, Any]:
        """处理用户查询，包括检索和生成"""
        if top_k_retrieval is None:
            top_k_retrieval = self.config['top_k_retrieval']
            
        if not self.document and not self.vector_store:
             # 非文档模式，直接调用LLM
            logger.info(f"非文档模式回答查询: {query}")
            
            # 准备变量字典 - 不包含reference_text
            variables = {
                'query': query
            }
            
            prompt = PromptManager.render_by_type(
                template_type='chat_response', 
                variables=variables
            )
            
            response = self.llm_client.generate_text(prompt=prompt, task_type='chat')
            response['retrieved_chunks'] = []
            response['is_generic_answer'] = True
            return response

        # 1. 确保文档已处理和向量库已加载
        if self.document and not self.document.is_processed:
            success = self.process_and_embed_document()
            if not success:
                return {"error": "文档处理失败", "text": "抱歉，处理您的文档时遇到问题。"}
        elif self.document and self.document.is_processed and not self.vector_store:
            self._load_vector_store()
            if not self.vector_store:
                 return {"error": "向量库加载失败", "text": "抱歉，加载文档知识库时遇到问题。"}

        # 2. 检索相关文档块
        relevant_chunks = self.retrieve_relevant_chunks(query, top_k=top_k_retrieval)
        
        # 3. 生成答案
        has_document_context = len(relevant_chunks) > 0
        
        # 准备变量字典
        variables = {
            'query': query
        }
        
        # 如果有相关文档块，添加到变量中
        if has_document_context:
            context_text = "\n\n".join([chunk.content for chunk in relevant_chunks])
            variables['reference_text'] = context_text
        
        # 使用聊天回复模板
        prompt = PromptManager.render_by_type(
            template_type='chat_response', 
            variables=variables
        )
        
        # 调用LLM生成答案
        response = self.llm_client.generate_text(
            prompt=prompt, 
            task_type='chat'
        )
        
        # 添加检索结果到响应中
        response['retrieved_chunks'] = [
            {'id': chunk.id, 'content': chunk.content[:200] + "..."} for chunk in relevant_chunks
        ]
        
        response['is_generic_answer'] = not has_document_context
        
        return response

    def generate_quiz(self, question_count: int = None, question_types: List[str] = None, difficulty: str = None) -> Dict[str, Any]:
        """为当前文档生成测验
        
        Args:
            question_count: 生成题目的数量
            question_types: 题目类型列表，可包含 'MC'(单选), 'MCM'(多选), 'TF'(判断), 'FB'(填空), 'SA'(简答)
            difficulty: 难度级别，'easy'=简单，'medium'=中等，'hard'=困难, 'master'=极难
            
        Returns:
            包含生成测验结果的字典
        """
        # 使用配置的默认值
        if question_count is None:
            question_count = self.config['default_question_count']
        if question_types is None:
            question_types = self.config['default_question_types']
        if difficulty is None:
            difficulty = self.config['default_difficulty']
            
        if not self.document:
            return {"error": "未加载文档，无法生成测验。请使用 generate_quiz_without_doc 方法生成无文档测验。"}
        
        if not self.document.is_processed:
            success = self.process_and_embed_document()
            if not success:
                return {"error": "文档处理失败，无法生成测验。"}

        # 获取文档完整内容
        doc_content = self.document.content
        if self.document.file:
            try:
                doc_content = self.document.file.read().decode('utf-8')
            except Exception:
                pass # 使用数据库中的content作为后备
        
        if not question_types:
            question_types = ['MC', 'TF'] # 默认单选题和判断题
        
        # 确保所有题型有效
        valid_types = ['MC', 'MCM', 'TF', 'FB', 'SA']
        question_types = [t for t in question_types if t in valid_types]
        
        if not question_types:
            question_types = ['MC'] # 如果没有有效题型，默认使用单选题
        
        # 添加system_prompt，引导LLM生成更标准的格式
        system_prompt = """你是一个专业的教育测验出题专家。请严格按照指定格式生成测验题目。每个题目必须包含完整的字段信息，尤其是:
1. 确保每个题目都包含 knowledge_points 字段，列出该题目涉及的知识点
2. 对多选题 (MCM)，正确答案必须是选项字母的数组，如 ["A", "C"]
3. 题目难度需符合要求
4. JSON 格式必须完全正确
5. 答案解析必须详细且引用原文

请仔细检查生成的 JSON 格式，确保其完整有效。"""
        
        prompt_variables = {
            'content': doc_content,
            'question_count': question_count,
            'question_types': ", ".join(question_types), # LLM可能更喜欢字符串形式
            'difficulty': difficulty
        }
        
        prompt = PromptManager.render_by_type(
            template_type='quiz_generation', 
            variables=prompt_variables
        )
        
        # 调用LLM生成测验题目
        response = self.llm_client.generate_text(
            prompt=prompt, 
            system_prompt=system_prompt, 
            task_type='quiz_generation'
        )
        
        # 解析LLM返回的JSON格式题目，并存入数据库 (Question模型)
        # 这里需要健壮的JSON解析和错误处理
        try:
            # 尝试从LLM响应中提取JSON部分
            text_response = response.get("text", "")
            json_str = text_response
            
            # 如果响应包含```json和```标记，提取其中的内容
            json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            json_match = re.search(json_pattern, text_response)
            if json_match:
                json_str = json_match.group(1)
            
            # 尝试多种方式解析JSON
            try:
                quiz_data = json.loads(json_str)
            except json.JSONDecodeError:
                # 可能是LLM生成的JSON不标准，尝试清理一下
                # 例如，处理注释、尾部逗号等
                cleaned_json = re.sub(r'//.*?(\n|$)', '', json_str)  # 移除单行注释
                cleaned_json = re.sub(r'/\*.*?\*/', '', cleaned_json, flags=re.DOTALL)  # 移除多行注释
                cleaned_json = re.sub(r',(\s*[\]}])', r'\1', cleaned_json)  # 移除尾部逗号
                
                try:
                    quiz_data = json.loads(cleaned_json)
                except json.JSONDecodeError:
                    # 如果仍然失败，尝试提取可能的JSON部分
                    possible_json = re.search(r'\[\s*{.*}\s*\]', cleaned_json, re.DOTALL)
                    if possible_json:
                        try:
                            quiz_data = json.loads(possible_json.group(0))
                        except json.JSONDecodeError:
                            raise json.JSONDecodeError("无法解析JSON", json_str, 0)
                    else:
                        raise json.JSONDecodeError("无法解析JSON", json_str, 0)
            
            # 验证和规范化每个题目的格式
            processed_quiz_data = []
            for i, question in enumerate(quiz_data):
                # 确保必要字段存在
                if 'content' not in question or 'type' not in question or 'correct_answer' not in question:
                    logger.warning(f"题目 #{i+1} 缺少必要字段，将被跳过")
                    continue
                    
                # 规范化题目类型
                q_type = question['type'].upper()
                if q_type not in valid_types:
                    logger.warning(f"题目 #{i+1} 类型无效: {q_type}，将被设为MC")
                    q_type = 'MC'
                
                # 验证选项（选择题）
                if q_type in ['MC', 'MCM'] and ('options' not in question or not isinstance(question['options'], list)):
                    logger.warning(f"题目 #{i+1} 选项格式无效，将被跳过")
                    continue
                
                # 验证答案格式
                correct_answer = question['correct_answer']
                if q_type == 'MC' and not isinstance(correct_answer, str):
                    logger.warning(f"题目 #{i+1} 单选题答案格式无效，将被跳过")
                    continue
                elif q_type == 'MCM' and not isinstance(correct_answer, list):
                    # 尝试将可能的字符串答案转换为列表
                    if isinstance(correct_answer, str):
                        try:
                            correct_answer = json.loads(correct_answer)
                        except:
                            # 如果是逗号分隔的字符串，也尝试转换
                            if ',' in correct_answer:
                                correct_answer = [a.strip() for a in correct_answer.split(',')]
                            else:
                                logger.warning(f"题目 #{i+1} 多选题答案格式无效，将被跳过")
                                continue
                    else:
                        logger.warning(f"题目 #{i+1} 多选题答案格式无效，将被跳过")
                        continue
                
                # 确保知识点字段存在
                if 'knowledge_points' not in question or not question['knowledge_points']:
                    # 如果没有知识点，尝试从问题内容和解释中提取关键词作为知识点
                    content = question.get('content', '')
                    explanation = question.get('explanation', '')
                    
                    # 使用简单的启发式方法提取可能的知识点
                    # 这只是一个简单示例，实际中可能需要更复杂的NLP方法
                    combined_text = f"{content} {explanation}"
                    
                    # 尝试从解析中找出关键概念（通常是粗体或引用的文本）
                    key_concepts = re.findall(r'\*\*(.*?)\*\*|\*(.*?)\*|"(.*?)"|\'(.*?)\'|「(.*?)」', combined_text)
                    extracted_concepts = []
                    for concept_match in key_concepts:
                        # findall返回的是一个元组，需要找出非空元素
                        concept = next((c for c in concept_match if c), None)
                        if concept and len(concept) > 1:  # 忽略太短的概念
                            extracted_concepts.append(concept)
                    
                    if extracted_concepts:
                        question['knowledge_points'] = extracted_concepts
                    else:
                        # 如果没有明显的关键概念，使用题目的主题作为知识点
                        question['knowledge_points'] = ["基础概念"]
                
                # 更新题目并添加到处理后的列表
                question['type'] = q_type
                if q_type == 'MCM':
                    question['correct_answer'] = correct_answer  # 已处理为列表
                
                processed_quiz_data.append(question)
            
            # 更新响应中的quiz_data
            response['quiz_data'] = processed_quiz_data
            
            quiz_obj = Quiz.objects.create(
                document=self.document,
                title=f"{self.document.title} 测验",
                description=f"基于文档《{self.document.title}》自动生成的测验",
                difficulty_level=difficulty,
                total_questions=len(processed_quiz_data),
                config={
                    'question_types': question_types,
                    'question_count': question_count,
                    'generated_time': time.time()
                }
            )
            
            for i, q_data in enumerate(processed_quiz_data):
                Question.objects.create(
                    quiz=quiz_obj,
                    content=q_data['content'],
                    question_type=q_data['type'],
                    options=q_data.get('options', None),
                    correct_answer=q_data['correct_answer'],
                    explanation=q_data.get('explanation', ''),
                    source_passage=q_data.get('source_passage', ''),
                    difficulty=q_data.get('difficulty', difficulty),
                    knowledge_points=q_data.get('knowledge_points', []),
                    order=i + 1
                )
            
            response['quiz_id'] = quiz_obj.id
            
        except json.JSONDecodeError as e:
            logger.error(f"解析测验题目JSON失败: {e}. LLM原始输出: {response.get('text')}")
            response['error'] = f"解析测验题目失败: {str(e)}"
            response['quiz_data'] = []
        except Exception as e:
            logger.exception(f"处理测验数据时出错: {e}")
            response['error'] = f"处理测验数据时出错: {str(e)}"
            response['quiz_data'] = []
            
        return response

    def generate_summary(self, summary_length: str = None, include_outline: bool = None) -> Dict[str, Any]:
        """为当前文档生成摘要
        
        Args:
            summary_length: 摘要长度，可选值 'short'（短）, 'medium'（中）, 'long'（长）
            include_outline: 是否包含结构大纲
            
        Returns:
            包含生成摘要结果的字典
        """
        # 使用配置的默认值
        if summary_length is None:
            summary_length = self.config['default_summary_length']
        if include_outline is None:
            include_outline = self.config['default_include_outline']
            
        if not self.document:
            return {"error": "未加载文档，无法生成摘要。"}

        doc_content = self.document.content
        if self.document.file:
            try:
                doc_content = self.document.file.read().decode('utf-8')
            except Exception:
                pass
        
        # 设置系统提示词
        system_prompt = """你是一个专业的文档分析和总结专家。请基于提供的文档内容生成一个全面、结构清晰的摘要。
摘要应该忠实原文，不添加不存在的内容，保持客观和准确。按照要求的长度和格式进行组织。"""
        
        if include_outline:
            system_prompt += "请先生成一个结构化的大纲，然后再提供详细摘要。大纲应当清晰地展示文档的主要章节和关键点。"
        
        # 根据长度设置指导
        length_guide = {
            'short': "生成一个简短摘要，约为原文的5-10%，只包含最核心的信息点。",
            'medium': "生成一个中等长度的摘要，约为原文的10-15%，包含主要论点和关键细节。",
            'long': "生成一个详细摘要，约为原文的15-25%，包含主要论点、关键证据和重要细节，但仍保持简洁。"
        }
        
        # 确保长度参数有效
        if summary_length not in length_guide:
            summary_length = 'medium'
            
        prompt_variables = {
            'content': doc_content,
            'length_requirement': length_guide[summary_length],
            'outline_requirement': "请先提供一个结构化大纲，然后再给出详细摘要。" if include_outline else ""
        }
        
        # 获取渲染后的提示词
        prompt = PromptManager.render_by_type(
            template_type='summary',
            variables=prompt_variables
        )
        
        # 调用LLM生成摘要
        response = self.llm_client.generate_text(
            prompt=prompt, 
            system_prompt=system_prompt,
            task_type='summary'
        )
        
        # 添加额外信息到响应
        response['summary_config'] = {
            'length': summary_length,
            'include_outline': include_outline,
            'document_title': self.document.title,
            'document_id': self.document.id
        }
        
        return response

    def generate_explanation(self, question_content: str, user_wrong_answer: str, correct_answer: str) -> Dict[str, Any]:
        """为错误答案生成解释"""
        if not self.document:
            # 也可以允许在没有文档上下文的情况下生成通用解释
            # 或者要求必须有文档上下文
            logger.warning("未加载文档，生成的解释可能不包含特定上下文。")
            doc_content_for_explanation = "通用知识。"
        else:
            doc_content_for_explanation = self.document.content
            if self.document.file:
                try:
                    doc_content_for_explanation = self.document.file.read().decode('utf-8')
                except Exception:
                    pass # 使用数据库中的content

        prompt_variables = {
            'content': doc_content_for_explanation, # 学习材料原文
            'question': question_content,
            'wrong_answer': user_wrong_answer,
            'correct_answer': correct_answer
        }
        
        prompt = PromptManager.render_by_type(
            template_type='explanation',
            variables=prompt_variables
        )
        
        response = self.llm_client.generate_text(prompt=prompt, task_type='explanation')
        return response

    def generate_quiz_without_doc(self, topic: str, constraints: str = "", 
                           question_count: int = None, question_types: List[str] = None, 
                           difficulty: str = None) -> Dict[str, Any]:
        """生成无需文档的测验
        
        Args:
            topic: 测验主题
            constraints: 额外约束条件
            question_count: 生成题目的数量
            question_types: 题目类型列表，可包含 'MC'(单选), 'MCM'(多选), 'TF'(判断), 'FB'(填空), 'SA'(简答)
            difficulty: 难度级别，'easy'=简单，'medium'=中等，'hard'=困难, 'master'=极难
            
        Returns:
            包含生成测验结果的字典
        """
        # 使用配置的默认值
        if question_count is None:
            question_count = self.config['default_question_count']
        if question_types is None:
            question_types = self.config['default_question_types']
        if difficulty is None:
            difficulty = self.config['default_difficulty']
            
        if not question_types:
            question_types = ['MC', 'TF'] # 默认单选题和判断题
        
        # 确保所有题型有效
        valid_types = ['MC', 'MCM', 'TF', 'FB', 'SA']
        question_types = [t for t in question_types if t in valid_types]
        
        if not question_types:
            question_types = ['MC'] # 如果没有有效题型，默认使用单选题
        
        prompt_variables = {
            'topic': topic,
            'constraints': constraints,
            'question_count': question_count,
            'question_types': ", ".join(question_types),
            'difficulty': difficulty
        }
        
        prompt = PromptManager.render_by_type(
            template_type='quiz_without_doc', 
            variables=prompt_variables
        )
        
        # 调用LLM生成测验题目
        response = self.llm_client.generate_text(prompt=prompt, task_type='quiz_generation')
        
        # 解析LLM返回的JSON格式题目，并存入数据库 (Question模型)
        try:
            # 尝试从LLM响应中提取JSON部分
            text_response = response.get("text", "")
            json_str = text_response
            
            # 如果响应包含```json和```标记，提取其中的内容
            json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            json_match = re.search(json_pattern, text_response)
            if json_match:
                json_str = json_match.group(1)
            
            quiz_data = json.loads(json_str)
            
            # 验证和规范化每个题目的格式
            processed_quiz_data = []
            for i, question in enumerate(quiz_data):
                # 确保必要字段存在
                if 'content' not in question or 'type' not in question or 'correct_answer' not in question:
                    logger.warning(f"题目 #{i+1} 缺少必要字段，将被跳过")
                    continue
                    
                # 规范化题目类型
                q_type = question['type'].upper()
                if q_type not in ['MC', 'MCM', 'TF', 'FB', 'SA']:
                    logger.warning(f"题目 #{i+1} 类型无效: {q_type}，将被设为MC")
                    q_type = 'MC'
                
                # 验证选项（选择题）
                if q_type in ['MC', 'MCM'] and ('options' not in question or not isinstance(question['options'], list)):
                    logger.warning(f"题目 #{i+1} 选项格式无效，将被跳过")
                    continue
                
                # 验证答案格式
                correct_answer = question['correct_answer']
                if q_type == 'MC' and not isinstance(correct_answer, str):
                    logger.warning(f"题目 #{i+1} 单选题答案格式无效，将被跳过")
                    continue
                elif q_type == 'MCM' and not isinstance(correct_answer, list):
                    # 尝试将可能的字符串答案转换为列表
                    if isinstance(correct_answer, str):
                        try:
                            correct_answer = json.loads(correct_answer)
                        except:
                            # 如果是逗号分隔的字符串，也尝试转换
                            if ',' in correct_answer:
                                correct_answer = [a.strip() for a in correct_answer.split(',')]
                            else:
                                logger.warning(f"题目 #{i+1} 多选题答案格式无效，将被跳过")
                                continue
                    else:
                        logger.warning(f"题目 #{i+1} 多选题答案格式无效，将被跳过")
                        continue
                
                # 更新题目并添加到处理后的列表
                question['type'] = q_type
                if q_type == 'MCM':
                    question['correct_answer'] = correct_answer  # 已处理为列表
                
                processed_quiz_data.append(question)
            
            # 更新响应中的quiz_data
            response['quiz_data'] = processed_quiz_data
            
            # 创建测验对象 (无文档)
            quiz_obj = Quiz.objects.create(
                document=None,  # 无文档
                title=f"{topic} 测验",
                description=f"基于主题《{topic}》自动生成的测验",
                difficulty_level=difficulty,
                total_questions=len(processed_quiz_data),
                config={
                    'topic': topic,
                    'constraints': constraints,
                    'question_types': question_types,
                    'question_count': question_count,
                    'generated_time': time.time()
                }
            )
            
            for i, q_data in enumerate(processed_quiz_data):
                Question.objects.create(
                    quiz=quiz_obj,
                    content=q_data['content'],
                    question_type=q_data['type'],
                    options=q_data.get('options', None),
                    correct_answer=q_data['correct_answer'],
                    explanation=q_data.get('explanation', ''),
                    source_passage=q_data.get('source_passage', ''),
                    difficulty=q_data.get('difficulty', difficulty),
                    order=i + 1
                )
            
            response['quiz_id'] = quiz_obj.id
            
        except json.JSONDecodeError as e:
            logger.error(f"解析测验题目JSON失败: {e}. LLM原始输出: {response.get('text')}")
            response['error'] = f"解析测验题目失败: {str(e)}"
            response['quiz_data'] = []
        except Exception as e:
            logger.exception(f"处理测验数据时出错: {e}")
            response['error'] = f"处理测验数据时出错: {str(e)}"
            response['quiz_data'] = []
            
        return response

    def process_quiz_constraints(self, user_query: str) -> Dict[str, Any]:
        """处理用户对测验内容的约束请求
        
        Args:
            user_query: 用户的约束请求，例如"我需要一个关于Python基础的测验，包含列表和字典的内容"
            
        Returns:
            包含处理结果的字典，包括提取的主题和约束
        """
        # 使用LLM提取用户查询中的主题和约束
        system_prompt = """
        你是一个专业的教育测验分析专家。你的任务是从用户的请求中提取测验主题和具体约束条件。
        请按照以下JSON格式返回结果：
        {
            "topic": "主题名称",
            "constraints": "具体约束条件的详细描述",
            "suggested_question_types": ["MC", "TF", "MCM", "FB", "SA"],
            "suggested_difficulty": "easy/medium/hard/master"
        }
        
        只返回JSON格式，不要有其他文字。确保JSON格式正确。
        """
        
        response = self.llm_client.generate_text(
            prompt=user_query,
            system_prompt=system_prompt,
            task_type='quiz_constraints'
        )
        
        try:
            # 尝试从LLM响应中提取JSON
            text_response = response.get("text", "")
            json_str = text_response
            
            # 如果响应包含```json和```标记，提取其中的内容
            json_pattern = r'```(?:json)?\s*([\s\S]*?)\s*```'
            json_match = re.search(json_pattern, text_response)
            if json_match:
                json_str = json_match.group(1)
                
            constraints_data = json.loads(json_str)
            
            # 确保返回的数据包含必要字段
            if 'topic' not in constraints_data or 'constraints' not in constraints_data:
                return {
                    "error": "无法正确解析约束条件",
                    "topic": "未指定主题",
                    "constraints": "无具体约束",
                    "suggested_question_types": ["MC", "TF"],
                    "suggested_difficulty": "medium"
                }
                
            return constraints_data
            
        except Exception as e:
            logger.exception(f"处理测验约束时出错: {e}")
            return {
                "error": f"处理约束条件时出错: {str(e)}",
                "topic": "未指定主题",
                "constraints": "无具体约束",
                "suggested_question_types": ["MC", "TF"],
                "suggested_difficulty": "medium"
            }
    
    def generate_quiz_from_conversation(self, conversation_history: List[Dict[str, str]], 
                                      question_count: int = 5, 
                                      question_types: List[str] = None,
                                      difficulty: str = 'medium') -> Dict[str, Any]:
        """基于对话历史生成测验
        
        Args:
            conversation_history: 对话历史列表，每个元素包含 'role' 和 'content' 键
            question_count: 生成题目的数量
            question_types: 题目类型列表，可包含 'MC'(单选), 'MCM'(多选), 'TF'(判断), 'FB'(填空), 'SA'(简答)
            difficulty: 难度级别，'easy'=简单，'medium'=中等，'hard'=困难, 'master'=极难
            
        Returns:
            包含生成测验结果的字典
        """
        # 提取最后一条用户消息作为主要约束
        user_messages = [msg['content'] for msg in conversation_history if msg['role'] == 'user']
        
        if not user_messages:
            return {"error": "没有找到用户消息，无法生成测验"}
            
        # 使用最后一条用户消息作为主要约束
        last_user_message = user_messages[-1]
        
        # 处理约束
        constraints_data = self.process_quiz_constraints(last_user_message)
        
        # 使用提取的主题和约束生成测验
        topic = constraints_data.get('topic', '未指定主题')
        constraints = constraints_data.get('constraints', '')
        
        # 如果未指定题型和难度，使用建议值
        if not question_types:
            question_types = constraints_data.get('suggested_question_types', ['MC', 'TF'])
            
        if difficulty == 'medium':  # 只有当用户没有明确指定难度时才使用建议值
            difficulty = constraints_data.get('suggested_difficulty', 'medium')
            
        # 生成测验
        return self.generate_quiz_without_doc(
            topic=topic,
            constraints=constraints,
            question_count=question_count,
            question_types=question_types,
            difficulty=difficulty
        )

    def _summarize_conversation(self, conversation_history: List[Dict[str, Any]], max_tokens: int = 1000) -> str:
        """
        将长对话历史摘要为简短的上下文描述
        
        Args:
            conversation_history: 对话历史列表
            max_tokens: 最大token数
            
        Returns:
            对话摘要
        """
        if not conversation_history or len(conversation_history) < 5:
            return ""
            
        # 准备摘要提示词
        formatted_history = self._format_conversation_history(conversation_history)
        
        prompt = f"""请将以下对话历史摘要为一个简短的上下文描述，用于后续对话。
摘要应该包含关键信息点、重要概念和用户特别关注的内容。

对话历史：
{formatted_history}

请提供简明扼要的摘要，不超过200字："""
        
        response = self.llm_client.generate_text(
            prompt=prompt,
            system_prompt="你是一个专业的对话摘要助手，擅长提取对话中的关键信息和重要上下文。",
            max_tokens=max_tokens,
            task_type="summary"
        )
        
        return response.get('text', '')
    
    def _filter_relevant_history(self, conversation_history: List[Dict[str, Any]], 
                                query: str, max_turns: int = 5) -> List[Dict[str, Any]]:
        """
        根据当前查询过滤出最相关的对话历史记录
        
        Args:
            conversation_history: 对话历史列表
            query: 当前查询
            max_turns: 最大对话轮数
            
        Returns:
            过滤后的对话历史
        """
        if not conversation_history or len(conversation_history) < max_turns * 2:
            return conversation_history
        
        # 1. 先保留最近的几轮对话
        recent_turns = conversation_history[-max_turns * 2:]
        
        # 如果对话历史很长，尝试使用语义相似度找出相关的历史消息
        if len(conversation_history) > max_turns * 3:
            try:
                # 提取用户消息
                user_messages = [msg for msg in conversation_history[:-max_turns * 2] if msg.get('is_user', False)]
                if user_messages:
                    # 简单方法：使用关键词匹配
                    query_words = set(query.lower().split())
                    relevant_messages = []
                    
                    for msg in user_messages:
                        content = msg.get('content', '').lower()
                        # 计算匹配的关键词数量
                        matching_words = len([word for word in query_words if word in content])
                        if matching_words > 0:
                            # 找出对应的回复
                            idx = conversation_history.index(msg)
                            if idx + 1 < len(conversation_history) and not conversation_history[idx + 1].get('is_user', True):
                                relevant_messages.append(msg)
                                relevant_messages.append(conversation_history[idx + 1])
                    
                    # 限制额外相关消息的数量
                    max_additional = max_turns * 2
                    if relevant_messages and len(relevant_messages) <= max_additional:
                        # 将相关消息添加到结果中
                        return relevant_messages + recent_turns
            except Exception as e:
                logger.warning(f"过滤相关历史记录时出错: {e}")
        
        return recent_turns
    
    def _optimize_conversation_history(self, conversation_history: List[Dict[str, Any]], 
                                      query: str, max_turns: int = 5) -> List[Dict[str, Any]]:
        """
        优化对话历史，包括过滤和摘要
        
        Args:
            conversation_history: 对话历史列表
            query: 当前查询
            max_turns: 最大对话轮数
            
        Returns:
            优化后的对话历史
        """
        if not conversation_history:
            return []
            
        # 如果对话历史较短，直接返回
        if len(conversation_history) <= max_turns * 2:
            return conversation_history
            
        # 1. 过滤出最相关的历史
        filtered_history = self._filter_relevant_history(conversation_history, query, max_turns)
        
        # 2. 如果历史仍然很长，考虑生成摘要
        if len(filtered_history) > max_turns * 3:
            # 生成前半部分历史的摘要
            summary_part = filtered_history[:-max_turns * 2]
            recent_part = filtered_history[-max_turns * 2:]
            
            summary_text = self._summarize_conversation(summary_part)
            
            if summary_text:
                # 用摘要替换前半部分历史
                optimized_history = [
                    {'is_user': False, 'content': f"[历史摘要] {summary_text}"}
                ] + recent_part
                return optimized_history
        
        return filtered_history
    
    def process_chat_query(self, query: str, conversation_history: List[Dict[str, Any]] = None, 
                         document_id: int = None, normalize_history: bool = True) -> Dict[str, Any]:
        """
        处理聊天查询的统一接口，支持有文档和无文档模式，支持使用对话历史
        
        Args:
            query: 用户查询
            conversation_history: 对话历史列表，可选，支持多种格式
            document_id: 文档ID，可选，如果提供则使用该文档作为上下文
            normalize_history: 是否标准化对话历史格式，设为True可自动处理不同格式
            
        Returns:
            包含生成答案的字典
        """
        start_time = time.time()
        
        # 检查对话历史是否为空
        if conversation_history is None:
            conversation_history = []
        
        # 标准化对话历史格式，确保统一的格式 {'is_user': bool, 'content': str}
        if normalize_history and conversation_history:
            normalized_history = []
            for msg in conversation_history:
                if 'is_user' in msg:
                    # 已经是标准格式
                    normalized_history.append(msg)
                elif 'role' in msg:
                    # 转换 'role' 格式到 'is_user' 格式
                    normalized_history.append({
                        'is_user': msg['role'] == 'user',
                        'content': msg.get('content', '')
                    })
                else:
                    # 无法识别的格式，尽量猜测
                    logger.warning("遇到未知格式的对话历史消息，尝试猜测格式")
                    if any(key in msg for key in ['user', 'is_user', 'sender', 'from_user']):
                        # 尝试猜测是否为用户消息
                        is_user = bool(msg.get('user') or msg.get('is_user') or 
                                      msg.get('sender') == 'user' or msg.get('from_user'))
                        content = msg.get('content', msg.get('message', msg.get('text', '')))
                        if content:
                            normalized_history.append({
                                'is_user': is_user,
                                'content': content
                            })
            
            # 替换为标准化后的历史
            conversation_history = normalized_history
            
        # 优化对话历史，控制长度和相关性
        if len(conversation_history) > 4:  # 只在对话超过2轮时优化
            optimized_history = self._optimize_conversation_history(conversation_history, query)
            logger.info(f"对话历史优化: 原始长度={len(conversation_history)}, 优化后长度={len(optimized_history)}")
            conversation_history = optimized_history
        
        # 根据不同情况调用相应方法
        if document_id:
            # 如果指定了文档，确保文档已加载
            if not self.document or self.document.id != document_id:
                # 重新初始化RAG引擎
                self.__init__(document_id=document_id, llm_client=self.llm_client, config=self.config)
                
            # 如果有对话历史，使用对话历史版本的方法
            if conversation_history:
                result = self.answer_query_with_history(query, conversation_history)
            else:
                # 无对话历史，使用普通方法
                result = self.answer_query(query)
        else:
            # 无文档模式
            if conversation_history:
                # 有对话历史的无文档模式
                result = self.generate_general_answer_with_history(query, conversation_history)
            else:
                # 无对话历史的无文档模式
                # 使用LLM客户端直接生成回答
                llm_response = self.llm_client.generate_text(
                    prompt=query,
                    system_prompt="你是一个专业的学习助手。请清晰、准确地回答用户的问题。",
                    task_type="chat"
                )
                
                result = {
                    'answer': llm_response.get('text', '无法生成回答'),
                    'sources': [],
                    'processing_time': time.time() - start_time,
                    'is_generic_answer': True
                }
        
        # 添加处理时间
        if 'processing_time' not in result:
            result['processing_time'] = time.time() - start_time
            
        return result
    
    def generate_general_answer_with_history(self, query: str, conversation_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成通用对话的回答（不依赖特定文档），但使用对话历史作为上下文
        
        Args:
            query: 用户查询
            conversation_history: 对话历史列表，每个项目包含 {'is_user': bool, 'content': str}
            
        Returns:
            包含生成答案的字典
        """
        start_time = time.time()
        
        # 格式化对话历史
        formatted_history = self._format_conversation_history(conversation_history)
        
        # 准备变量字典 - 不包含reference_text
        variables = {
            'query': query,
            'conversation_history': formatted_history
        }
        
        # 使用带有对话历史的聊天提示模板
        prompt = PromptManager.render_by_type('chat_with_history_response', variables)
        
        # 调用LLM生成回答
        result = self.llm_client.generate_text(
            prompt=prompt,
            task_type="chat"
        )
        
        processing_time = time.time() - start_time
        
        # 准备返回结果
        return {
            'answer': result.get('text', '无法生成回答'),
            'sources': [],
            'processing_time': processing_time,
            'is_generic_answer': True
        }

# 可以在这里添加一些辅助函数，例如初始化默认模板等
def initialize_ai_services():
    """初始化AI服务，例如创建默认的提示词模板"""
    try:
        from django.db import connection
        from .prompt_manager import PromptManager
        
        # 检查表是否存在
        table_names = connection.introspection.table_names()
        if 'ai_services_prompttemplate' not in table_names:
            logger.warning("提示词模板表不存在，跳过创建默认模板")
            return
            
        # 创建默认提示词模板
        PromptManager.create_default_templates()
        logger.info("AI服务初始化完成，默认提示词模板已检查/创建。")
    except Exception as e:
        if 'no such table' in str(e).lower():
            logger.warning("AI服务相关表不存在，跳过初始化")
        else:
            logger.exception(f"初始化AI服务时出错: {str(e)}")