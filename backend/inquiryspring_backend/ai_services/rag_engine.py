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
from langchain_community.retrievers.bm25 import BM25Retriever
from langchain.retrievers.ensemble import EnsembleRetriever
from langchain.retrievers.contextual_compression import ContextualCompressionRetriever
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain.schema import Document as LangchainDocument # Alias to avoid confusion

# Model imports for reranking
# from sentence_transformers import CrossEncoder # This is now wrapped by the LangChain community class
from langchain_community.cross_encoders import HuggingFaceCrossEncoder

# Chinese tokenization for BM25
import jieba

from inquiryspring_backend.documents.models import Document, DocumentChunk
from .llm_client import LLMClientFactory
from .prompt_manager import PromptManager
from inquiryspring_backend.quiz.models import Quiz, Question
from django.conf import settings
from .structured_output import StructuredOutputProcessor, ChatResponse, Quiz as QuizModel, SummaryResponse

logger = logging.getLogger(__name__)

# 用户知识库存储目录
VECTOR_STORE_DIR = os.path.join(settings.BASE_DIR, "vector_store")
# 通用知识库存储目录
GENERAL_KNOWLEDGE_DIR = os.path.join(settings.BASE_DIR, "general_knowledge")
os.makedirs(VECTOR_STORE_DIR, exist_ok=True)
os.makedirs(GENERAL_KNOWLEDGE_DIR, exist_ok=True)


# ---- 全局嵌入模型单例 ----
# 默认使用 BAAI/bge-m3，如需切换请设置环境变量 EMBEDDING_MODEL_NAME
EMBEDDING_MODEL_NAME = os.getenv("EMBEDDING_MODEL_NAME", "BAAI/bge-m3")
try:
    # 使用 HuggingFaceEmbeddings 包装 SentenceTransformer 模型，使其兼容 LangChain
    _GLOBAL_EMBEDDINGS = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
    logger.info(f"已加载全局嵌入模型: {EMBEDDING_MODEL_NAME}")
except Exception as e:
    logger.warning(f"加载嵌入模型 {EMBEDDING_MODEL_NAME} 失败: {e}，回退到 'sentence-transformers/all-mpnet-base-v2'")
    _GLOBAL_EMBEDDINGS = HuggingFaceEmbeddings(model_name="sentence-transformers/all-mpnet-base-v2")


# ---- 全局重排模型单例 ----
RERANKER_MODEL_NAME = os.getenv("RERANKER_MODEL_NAME", "BAAI/bge-reranker-v2-m3")
try:
    # Use LangChain's wrapper to ensure compatibility with CrossEncoderReranker.
    # The underlying sentence_transformers model is accessible via the `.client` attribute.
    _GLOBAL_RERANKER = HuggingFaceCrossEncoder(model_name=RERANKER_MODEL_NAME)
    logger.info(f"已加载全局重排模型: {RERANKER_MODEL_NAME}")
except Exception as e:
    logger.error(f"加载重排模型 {RERANKER_MODEL_NAME} 失败: {e}。重排功能将不可用。")
    _GLOBAL_RERANKER = None

# ---- Jieba Tokenizer for BM25 ----
def chinese_tokenizer(text: str) -> List[str]:
    """使用Jieba进行中文分词"""
    return jieba.lcut(text)

logger.info("Jieba分词器已初始化用于BM25。")

class RAGEngine:
    """
    RAG引擎，通过"召回-重排"混合检索和LLM提供三种核心AI服务：
    1. 聊天 (Chat): 支持有/无文档上下文的对话。
    2. 测验 (Quiz): 支持有/无文档上下文的测验生成。
    3. 摘要 (Summary): 为指定文档生成摘要。
    """
    DEFAULT_CONFIG = {
        'chunk_size': 1000, 'chunk_overlap': 100, 'initial_retrieval_k': 20, # 初始检索阶段（BM25+向量），每个检索器召回的数量
        'top_n_rerank': 5,         # 重排后，最终选择的文档数量
        'ensemble_weights': [0.5, 0.5], # 混合检索权重 [BM25, Vector]
        'vector_store_dir': VECTOR_STORE_DIR, 'default_question_count': 5,
        'default_question_types': ['MC', 'TF'], 'default_difficulty': 'medium',
        'structured_output': True,  # 是否使用结构化输出处理
        'max_retries': 2,          # 结构化输出失败时的最大重试次数
    }
    
    def __init__(self, document_id: int = None, llm_client = None, config: Dict = None):
        self.document = None
        self.retriever = None  # 将使用带重排的混合检索器
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        
        if document_id:
            try: self.document = Document.objects.get(id=document_id)
            except Document.DoesNotExist: logger.error(f"文档ID {document_id} 不存在.")

        self.llm_client = llm_client or LLMClientFactory.create_client()
        # 使用全局单例嵌入模型
        self.embeddings = _GLOBAL_EMBEDDINGS
        
        # 初始化结构化输出处理器
        if self.config.get('structured_output', True):
            self.output_processor = StructuredOutputProcessor(
                max_retries=self.config.get('max_retries', 2),
                retry_delay=self.config.get('retry_delay', 1)
            )
        else:
            self.output_processor = None
        
        # 初始化通用知识库检索器
        self.kb_retriever = None
        self.init_general_knowledge_base()
        
        if self.document and self.document.is_processed:
            self._initialize_retrievers()

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
        
        # 查询重写：如果有对话历史，将原始查询改写为包含上下文的完整查询
        original_query = query
        rewritten_query = self._rewrite_query_with_history(query, history)
        
        prompt_vars = {
            'query': original_query,  # 在显示给用户时使用原始查询
            'conversation_history': self._format_conversation_history(history)
        }
        
        # 使用混合检索获取上下文
        retrieved_results = self.retrieve_with_hybrid_sources(rewritten_query)
        has_context = bool(retrieved_results)

        if has_context:
            prompt_vars['reference_text'] = "\n\n---\n\n".join([r['content'] for r in retrieved_results])
            
            # 为LLM的溯源功能准备source信息
            sources_for_prompt = []
            for i, r in enumerate(retrieved_results):
                source_info = {
                    'id': i + 1,
                    'type': r['source_type'],
                    'title': r['document_title']
                }
                sources_for_prompt.append(source_info)
            prompt_vars['sources_info'] = sources_for_prompt # 添加到prompt变量中

        # 获取聊天示例
        chat_examples = PromptManager._get_or_create_examples('chat')
        
        # 使用支持JSON Schema的提示词渲染
        prompt = PromptManager.render_with_schema(
            'chat', 
            prompt_vars, 
            output_schema=ChatResponse,
            examples=chat_examples
        )
            
        system_prompt = "你是一个学习助手。请基于参考资料回答问题。" if has_context else "你是一个学习助手。请清晰地回答问题。"
            
        llm_response = self.llm_client.generate_text(prompt=prompt, system_prompt=system_prompt, task_type="chat", **log_context)
        
        # 使用结构化输出处理
        if self.output_processor and self.config.get('structured_output', True):
            try:
                validated_response = self.output_processor.validate_and_fix(
                    llm_response.get('text', ''), 
                    ChatResponse, 
                    self.llm_client,
                    task_type="chat_fix",
                    **log_context
                )
                
                # 返回验证后的结构化结果
                result = {
                    'answer': validated_response.answer,
                    'sources': validated_response.sources if validated_response.sources else [],
                    'processing_time': time.time() - start_time,
                    'is_generic_answer': not has_context,
                    'error': llm_response.get('error')
                }
            except ValueError as e:
                logger.warning(f"结构化输出验证失败: {str(e)}，回退到非结构化输出")
                result = {
                    'answer': llm_response.get('text', '无法生成回答'),
                    'sources': retrieved_results, # 回退时返回原始检索结果
                    'processing_time': time.time() - start_time,
                    'is_generic_answer': not has_context,
                    'error': llm_response.get('error') or str(e)
                }
        else:
            # 原始非结构化输出处理
            result = {
                'answer': llm_response.get('text', '无法生成回答'),
                'sources': retrieved_results, # 返回原始检索结果
                'processing_time': time.time() - start_time,
                'is_generic_answer': not has_context,
                'error': llm_response.get('error')
            }
            
        # 如果查询被重写了，将重写信息添加到结果中（仅用于调试）
        if rewritten_query != original_query:
            logger.debug(f"查询重写: '{original_query}' -> '{rewritten_query}'")
            if settings.DEBUG:
                result['debug_info'] = {
                    'original_query': original_query,
                    'rewritten_query': rewritten_query
                }
            
        return result

    def handle_quiz(self, user_query: str, document_id: int = None, 
                    question_count: int = None, question_types: List[str] = None, difficulty: str = None, 
                    user: Any = None, session_id: str = None) -> Dict[str, Any]:
        """统一处理测验生成请求，并增强了结构化输出的健壮性。"""
        start_time = time.time()
        
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
        }
        log_context = {'user': user, 'session_id': session_id, 'document': self.document}
        
        # 使用混合检索获取上下文
        retrieved_results = self.retrieve_with_hybrid_sources(params['topic'])
        
        # 准备提示词变量
        prompt_vars = {**params}
        if retrieved_results:
            prompt_vars['reference_text'] = "\n\n".join([r['content'] for r in retrieved_results])
            source_types = {r['source_type'] for r in retrieved_results}
            if 'document' in source_types and 'knowledge_base' in source_types:
                prompt_vars['knowledge_source'] = "文档和通用知识库"
            elif 'document' in source_types:
                prompt_vars['knowledge_source'] = "文档"
            else:
                prompt_vars['knowledge_source'] = "通用知识库"
        else:
            logger.warning(f"在任何来源中都未找到与'{params['topic']}'相关的内容，将使用模型的固有知识")
            prompt_vars['reference_text'] = ""

        # 调用LLM生成测验
        quiz_examples = PromptManager._get_or_create_examples('quiz')
        prompt = PromptManager.render_with_schema('quiz', prompt_vars, output_schema=QuizModel, examples=quiz_examples)
        system_prompt = "你是一个测验出题专家。请严格按照JSON Schema格式生成题目。"
        llm_response = self.llm_client.generate_text(prompt, system_prompt=system_prompt, task_type='quiz', **log_context)
        
        # 结构化输出处理与健壮的回退机制
        if self.output_processor and self.config.get('structured_output', True):
            try:
                # 验证并修复LLM输出
                validated_response = self.output_processor.validate_and_fix(
                    llm_response.get('text', ''), 
                    QuizModel, 
                    self.llm_client,
                    task_type="quiz_fix",
                    **log_context
                )
                
                # 成功后，处理并保存测验数据
                quiz_data = [q.model_dump() for q in validated_response.questions]
                quiz_id = self._save_quiz_to_db(quiz_data, params['topic'], params['difficulty'])
                
                return {
                    'quiz_id': quiz_id,
                    'quiz_data': quiz_data,
                    'processing_time': time.time() - start_time,
                    'knowledge_source': prompt_vars.get('knowledge_source', '模型固有知识'),
                    'error': None
                }
            except ValueError as e:
                logger.error(f"测验结构化输出验证和修复失败: {str(e)}")
                # 优雅回退：返回错误信息和原始文本，而不是尝试保存
                return {
                    'quiz_id': None,
                    'quiz_data': [],
                    'processing_time': time.time() - start_time,
                    'knowledge_source': prompt_vars.get('knowledge_source', '模型固有知识'),
                    'error': f"无法生成结构化的测验，请稍后重试。错误: {str(e)}",
                    'raw_output': llm_response.get('text', '') # 包含原始输出，便于调试
                }
        
        # 非结构化输出的传统路径
        try:
            quiz_data = self.output_processor._extract_and_parse_json(llm_response.get("text", "[]"))
            quiz_id = self._save_quiz_to_db(quiz_data, params['topic'], params['difficulty'])
            return {
                'quiz_id': quiz_id,
                'quiz_data': quiz_data,
                'processing_time': time.time() - start_time,
                'knowledge_source': prompt_vars.get('knowledge_source', '模型固有知识'),
                'error': llm_response.get('error')
            }
        except Exception as e:
            logger.error(f"处理非结构化测验数据时失败: {e}")
            return {'error': "解析或保存测验失败", 'quiz_data': [], 'raw_output': llm_response.get('text', '')}

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
        
        # 使用支持JSON Schema的提示词渲染
        summary_examples = PromptManager._get_or_create_examples('summary')
        prompt = PromptManager.render_with_schema(
            'summary',
            {'content': doc_content}, 
            output_schema=SummaryResponse,
            examples=summary_examples
        )
        system_prompt = "你是一个专业的文档分析和总结专家。"
        log_context = {'user': user, 'session_id': session_id, 'document': self.document}
        
        response = self.llm_client.generate_text(prompt=prompt, system_prompt=system_prompt, task_type='summary', **log_context)
        
        # 使用结构化输出处理
        if self.output_processor and self.config.get('structured_output', True):
            try:
                validated_response = self.output_processor.validate_and_fix(
                    response.get('text', ''), 
                    SummaryResponse, 
                    self.llm_client,
                    task_type="summary_fix",
                    **log_context
                )
                
                # 更新响应结果
                response['text'] = validated_response.summary
            except ValueError as e:
                logger.warning(f"摘要结构化输出验证失败: {str(e)}，保留原始输出")
                # 原始输出保持不变
        
        response['document_id'] = self.document.id
        return response

    # --- Document Processing ---
    def process_and_embed_document(self, force_reprocess: bool = False) -> bool:
        """处理并嵌入文档"""
        if not self.document: return False
        if self.document.is_processed and not force_reprocess:
            self._initialize_retrievers() # 确保即使不重新处理，检索器也被初始化
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
            vector_store = Chroma.from_texts([c.content for c in document_chunks], self.embeddings, metadatas=metadatas, persist_directory=persist_dir)
            vector_store.persist()

            self.document.is_processed = True
            self.document.save()
            self._initialize_retrievers() # 处理完成后，立即初始化检索器
            return True
        except Exception as e:
            logger.exception(f"处理文档失败: {e}")
            return False

    def retrieve_relevant_chunks(self, query: str) -> List[DocumentChunk]:
        """根据查询使用"召回-重排"混合检索流程，检索相关的文档分块"""
        if not self.retriever:
            logger.warning(f"检索器未初始化 (文档ID: {self.document.id if self.document else 'N/A'})。尝试现在初始化。")
            if self.document:
                self._initialize_retrievers()
            if not self.retriever:
                logger.error("初始化检索器失败。无法继续检索。")
                return []
        
        try:
            results = self.retriever.get_relevant_documents(query)
            
            # 使用有序的chunk_id列表从数据库中一次性获取，并保持顺序
            chunk_ids = [doc.metadata.get('chunk_id') for doc in results if doc.metadata.get('chunk_id')]
            if not chunk_ids:
                return []

            # 保持从reranker得到的顺序
            chunks_map = {str(c.id): c for c in DocumentChunk.objects.filter(id__in=chunk_ids)}
            ordered_chunks = [chunks_map[cid] for cid in chunk_ids if cid in chunks_map]
            
            return ordered_chunks
        except Exception as e:
            logger.exception(f"检索-重排流程失败 (查询: '{query}'): {e}")
            return []

    def retrieve_with_hybrid_sources(self, query: str) -> List[Dict[str, Any]]:
        """
        统一检索接口，同时从用户文档和通用知识库检索内容，并进行统一排序。
        支持混合检索模式，返回统一的检索结果格式。
        
        Args:
            query: 查询文本
            
        Returns:
            统一格式的混合检索结果列表，每项包含内容、来源类型和元数据
        """
        start_time = time.time()
        unified_results = []
        
        # 并行检索两种来源（如果可用）
        doc_chunks = []
        if self.document and self.retriever:
            doc_chunks = self.retrieve_relevant_chunks(query)
        
        kb_results = []
        if self.kb_retriever:
            kb_results = self.retrieve_from_knowledge_base(query)
        
        # 统一结果格式
        # 1. 添加文档结果
        for chunk in doc_chunks:
            unified_results.append({
                'content': chunk.content,
                'source_type': 'document',
                'source_id': chunk.id,
                'document_title': self.document.title if self.document else None,
                'chunk_index': chunk.chunk_index,
                'metadata': {'chunk_id': str(chunk.id), 'document_id': str(self.document.id)}
            })
        
        # 2. 添加知识库结果
        for result in kb_results:
            metadata = result.get('metadata', {})
            unified_results.append({
                'content': result['content'],
                'source_type': 'knowledge_base',
                'source_id': result['id'],
                'document_title': metadata.get('title', '通用知识'),
                'chunk_index': metadata.get('chunk_index', 0),
                'metadata': metadata
            })
        
        # 如果没有任何结果，返回空列表
        if not unified_results:
            return []
        
        # 混合重排序
        reranked_results = self._rerank_hybrid_results(unified_results, query)
        
        logger.info(f"混合检索完成，耗时: {time.time() - start_time:.2f}秒，文档结果数: {len(doc_chunks)}，知识库结果数: {len(kb_results)}，重排后结果数: {len(reranked_results)}")
        
        return reranked_results
    
    def _rerank_hybrid_results(self, results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        对混合来源的结果进行统一重排序
        
        Args:
            results: 混合检索结果
            query: 原始查询
            
        Returns:
            重排序后的结果列表
        """
        if not results:
            return []
            
        # 如果没有重排模型，直接返回原始结果（按原顺序）
        if not _GLOBAL_RERANKER:
            logger.warning("重排模型不可用，混合结果将保持原始排序")
            return results[:self.config.get('top_n_rerank', 5)]
        
        try:
            # 提取文本内容，用于重排
            texts = [r['content'] for r in results]
            
            # 生成查询与每个文本的相似度分数
            pairs = [[query, text] for text in texts]
            # Access the underlying sentence-transformer model via the `.client` attribute for direct prediction
            scores = _GLOBAL_RERANKER.client.predict(pairs)
            
            # 为每个结果添加分数，并根据知识来源进行适度调整
            for i, score in enumerate(scores):
                final_score = score
                # Handle cases where the reranker returns multiple scores (e.g., [dissimilarity, similarity])
                # We assume the last score is the one indicating relevance.
                if isinstance(score, (list, tuple)) or (hasattr(score, 'shape') and len(score.shape) > 0):
                    logger.debug(f"Reranker returned multiple scores: {score}. Using the last one.")
                    final_score = score[-1]

                # 自定义规则: 根据来源类型进行细微调整
                source_boost = 1.0
                if results[i]['source_type'] == 'document' and self.document:
                    # 当用户上传了文档时，给特定文档来源略微加分
                    source_boost = 1.05  # 5%的提升
                
                # 存储调整后的分数
                results[i]['relevance_score'] = final_score * source_boost
            
            # 重排序
            reranked_results = sorted(results, key=lambda x: x.get('relevance_score', 0), reverse=True)
            
            # 截断到配置的长度
            top_n = self.config.get('top_n_rerank', 5)
            return reranked_results[:top_n]
            
        except Exception as e:
            logger.exception(f"混合结果重排序失败: {str(e)}")
            # 出错时返回原始列表，但仍然截断
            return results[:self.config.get('top_n_rerank', 5)]

    # --- Private Helpers ---
    def _initialize_retrievers(self):
        """初始化一个带重排的混合检索管道."""
        if not self.document:
            logger.warning("无文档加载，无法初始化检索器。")
            return

        all_chunks = list(self.document.chunks.all())
        if not all_chunks:
            logger.warning(f"文档 {self.document.id} 不包含任何文本块，跳过检索器初始化。")
            return

        langchain_docs = [
            LangchainDocument(page_content=c.content, metadata={'chunk_id': str(c.id)}) for c in all_chunks
        ]
        
        k = self.config.get('initial_retrieval_k', 20)
        
        # 1. 初始化 BM25 检索器
        bm25_retriever = BM25Retriever.from_documents(
            documents=langchain_docs,
            preprocess_func=chinese_tokenizer,
            k=k
        )

        # 2. 初始化向量存储检索器
        vector_retriever = None
        persist_dir = os.path.join(self.config['vector_store_dir'], str(self.document.id))
        if os.path.exists(persist_dir):
            vector_store = Chroma(persist_directory=persist_dir, embedding_function=self.embeddings)
            vector_retriever = vector_store.as_retriever(search_kwargs={"k": k})
        else:
            logger.warning(f"未找到文档 {self.document.id} 的向量存储。混合检索将只依赖BM25。")

        # 3. 组合成基础的混合检索器
        if vector_retriever:
            base_retriever = EnsembleRetriever(
                retrievers=[bm25_retriever, vector_retriever],
                weights=self.config['ensemble_weights']
            )
        else: # 回退到只有BM25
            base_retriever = bm25_retriever
        
        # 4. 如果重排模型加载成功，则创建带重排的压缩检索器
        if _GLOBAL_RERANKER:
            compressor = CrossEncoderReranker(model=_GLOBAL_RERANKER, top_n=self.config.get('top_n_rerank', 5))
            self.retriever = ContextualCompressionRetriever(
                base_compressor=compressor, 
                base_retriever=base_retriever
            )
            logger.info(f"已为文档 {self.document.id} 初始化带重排的混合检索器。")
        else:
            # Fallback if reranker model failed to load
            self.retriever = base_retriever
            logger.warning(f"重排模型加载失败。已为文档 {self.document.id} 初始化仅混合检索的回退检索器。")

    def _split_document(self, content: str) -> List[str]:
        splitter = RecursiveCharacterTextSplitter(chunk_size=self.config['chunk_size'], chunk_overlap=self.config['chunk_overlap'])
        return splitter.split_text(content)

    def _extract_quiz_constraints(self, user_query: str) -> Dict[str, Any]:
        system_prompt = """从用户请求中提取测验的主题、题型、难度和数量。按以下JSON格式返回：
        {"topic": "主题", "question_types": ["MC"], "difficulty": "medium", "question_count": 5}"""
        response = self.llm_client.generate_text(prompt=user_query, system_prompt=system_prompt, task_type='quiz')
        try:
            # 解析响应并确保它是一个字典
            parsed_result = self.output_processor._extract_and_parse_json(response.get("text", "{}"))
            
            # 如果解析结果不是字典（例如是列表或其他类型），返回默认字典
            if not isinstance(parsed_result, dict):
                logger.warning(f"解析测验约束时得到了非字典结果: {type(parsed_result)}，使用默认字典")
                return {"topic": user_query}
                
            return parsed_result
        except Exception as e:
            logger.exception(f"提取测验约束时出错: {e}")
            return {"topic": user_query}

    def _format_conversation_history(self, history: List[Dict[str, Any]]) -> str:
        """
        将对话历史格式化为文本，特殊处理包含摘要的对话轮次。
        """
        formatted_turns = []
        for message in history:
            content = message.get('content', '')
            # 检查是否是摘要轮次（前面有[历史对话摘要]标记）
            if not message.get('is_user') and content.startswith('[历史对话摘要]:'):
                # 特殊格式化摘要轮次，使其在视觉上区分开来
                formatted_turns.append(f"===历史对话摘要===\n{content.replace('[历史对话摘要]:', '').strip()}\n=================")
            else:
                # 常规对话轮次的格式化
                formatted_turns.append(f"{'用户' if message.get('is_user') else '助手'}: {content}")
                
        return "\n\n".join(formatted_turns)

    def _rewrite_query_with_history(self, query: str, conversation_history: List[Dict[str, Any]]) -> str:
        """
        根据对话历史，将用户的最新查询重写为一个独立的、完整的查询。
        这对于处理多轮对话中的省略引用（"它是什么？"，"为什么会这样？"等）至关重要。
        
        Args:
            query: 用户的原始查询
            conversation_history: 对话历史记录
            
        Returns:
            重写后的查询，如果原查询已经足够明确则返回原查询
        """
        # 如果没有历史或历史太短，直接返回原始查询
        if not conversation_history or len(conversation_history) < 1:
            return query
            
        try:
            # 直接使用优化后的对话历史（可能包含摘要）
            history_text = self._format_conversation_history(conversation_history)
            
            # 构建提示语，要求LLM保持简洁，仅在需要时重写查询
            system_prompt = "你是一个专业的查询重写助手。你的任务是根据对话历史，将用户的最新查询重写为一个完整、独立、明确的查询。"
            prompt = f"""基于以下对话历史和用户的最新问题，判断是否需要重写：

                        对话历史:
                        {history_text}

                        用户最新问题: {query}

                        要求:
                        1. 如果最新问题已经清晰完整，可以独立理解，则直接返回原问题。
                        2. 如果最新问题包含代词引用（如"它"、"他们"、"这个"等）或上下文省略，请重写为完整、独立的问题。
                        3. 回答格式: 只返回重写后的问题，不要包含任何解释或其他文字。
                        4. 保持简洁，不要添加不必要的内容。
                        5. 充分利用对话历史（包括摘要部分）提供的上下文信息。

                        重写后的问题:"""

            # 调用LLM进行查询重写
            response = self.llm_client.generate_text(prompt=prompt, system_prompt=system_prompt, task_type="query_rewrite")
            rewritten_query = response.get('text', '').strip()
            
            # 检查重写结果是否有效
            if not rewritten_query or len(rewritten_query) < len(query) / 2:
                # 如果重写结果无效或过短，使用原始查询
                logger.warning(f"查询重写结果无效或过短: '{rewritten_query}'，使用原始查询: '{query}'")
                return query
                
            logger.info(f"查询重写: '{query}' -> '{rewritten_query}'")
            return rewritten_query
            
        except Exception as e:
            logger.exception(f"查询重写过程中出错: {e}")
            # 出错时回退到原始查询
            return query

    def _optimize_conversation_history(self, history: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
        """
        优化对话历史，使用滑动窗口+摘要的方式来处理长对话，
        保持最近几轮对话的细节，同时为较早的对话生成摘要。
        
        Args:
            history: 完整的对话历史
            query: 当前的查询（作为上下文，不会直接处理）
            
        Returns:
            优化后的对话历史，包含"摘要+最近对话"的组合
        """
        # 配置参数
        recent_turns_keep = 4  # 保留完整信息的最近轮数
        max_total_turns = 10   # 总共保留的最大轮数（包括摘要）
        
        # 如果历史不够长，不需要生成摘要，直接返回原始历史或截取最近部分
        if len(history) <= recent_turns_keep:
            return history  # 不做特殊处理，对于短对话直接使用完整历史
            
        try:
            # 当历史长度超过阈值，生成较早部分的摘要
            recent_turns = history[-recent_turns_keep:]  # 保留最近的几轮完整对话
            earlier_turns = history[:-recent_turns_keep]  # 较早的对话，需要生成摘要
            
            # 如果较早部分都很短，可以保留更多轮数而不是生成摘要
            if sum(len(str(turn.get('content', ''))) for turn in earlier_turns) < 1000:
                # 历史不长，保留尽可能多的轮数直到max_total_turns
                return history[-(max_total_turns):]
                
            # 否则为较早部分生成摘要
            summarized_history = self._generate_conversation_summary(earlier_turns)
            
            # 构造摘要伪对话轮次
            summary_turn = {
                'is_user': False,
                'content': f"[历史对话摘要]: {summarized_history}",
                'timestamp': earlier_turns[-1].get('timestamp', None)
            }
            
            # 组合摘要和最近对话
            optimized_history = [summary_turn] + recent_turns
            return optimized_history
            
        except Exception as e:
            logger.exception(f"优化对话历史失败: {e}")
            # 出错则回退到简单截取最近的对话
            return history[-recent_turns_keep:]
            
    def _generate_conversation_summary(self, conversation_turns: List[Dict[str, Any]]) -> str:
        """
        生成对话历史的摘要
        
        Args:
            conversation_turns: 要总结的对话轮次
            
        Returns:
            对话摘要
        """
        try:
            # 对话为空，返回空摘要
            if not conversation_turns:
                return ""
                
            # 格式化对话，准备输入给LLM
            formatted_conversation = "\n".join([
                f"{'用户' if turn.get('is_user') else '助手'}: {turn.get('content', '')}" 
                for turn in conversation_turns
            ])
            
            # 构建提示词
            system_prompt = "你是一个专业的对话摘要生成器。你的任务是为对话历史生成简短、信息丰富的摘要。"
            prompt = f"""请为以下对话历史生成一个简短的摘要（150字以内）。
            
                        对话历史:
                        {formatted_conversation}

                        要求:
                        1. 摘要应包含对话中的主要主题、关键问题和重要结论
                        2. 保持客观，不添加原对话中没有的信息
                        3. 简明扼要，控制在150字以内
                        4. 使用第三人称，例如"用户询问了..."，"助手解释了..."

                        对话摘要:"""

            # 调用LLM生成摘要
            response = self.llm_client.generate_text(
                prompt=prompt, 
                system_prompt=system_prompt, 
                task_type="conversation_summary"
            )
            
            summary = response.get('text', '').strip()
            if not summary:
                # 如果摘要生成失败，返回一个简单的默认描述
                return f"早先的对话包含了{len(conversation_turns)}轮交流。"
                
            return summary
            
        except Exception as e:
            logger.exception(f"生成对话摘要失败: {e}")
            # 出错时返回简单描述
            return f"早先的对话包含了{len(conversation_turns)}轮交流。"

    def init_general_knowledge_base(self):
        """初始化通用知识库检索器"""
        if os.path.exists(GENERAL_KNOWLEDGE_DIR):
            try:
                # 检查知识库是否已经存在
                if os.listdir(GENERAL_KNOWLEDGE_DIR):
                    # 加载通用知识库的向量存储
                    kb_vector_store = Chroma(
                        persist_directory=GENERAL_KNOWLEDGE_DIR,
                        embedding_function=self.embeddings
                    )
                    
                    # 使用向量存储创建检索器，配置相同的重排参数
                    self.kb_retriever = kb_vector_store.as_retriever(
                        search_kwargs={"k": self.config.get('top_n_rerank', 5)}
                    )
                    
                    # 如果有重排模型，应用与文档检索相同的重排策略
                    if _GLOBAL_RERANKER:
                        compressor = CrossEncoderReranker(
                            model=_GLOBAL_RERANKER, 
                            top_n=self.config.get('top_n_rerank', 5)
                        )
                        self.kb_retriever = ContextualCompressionRetriever(
                            base_compressor=compressor,
                            base_retriever=self.kb_retriever
                        )
                    
                    logger.info("通用知识库检索器已初始化")
                else:
                    logger.warning("通用知识库目录存在但为空，暂不可用")
            except Exception as e:
                logger.error(f"初始化通用知识库失败: {str(e)}")
                self.kb_retriever = None
        else:
            logger.info("通用知识库不存在，跳过初始化")
            self.kb_retriever = None

    def retrieve_from_knowledge_base(self, query: str) -> List[Dict[str, Any]]:
        """从通用知识库检索相关内容
        
        Args:
            query: 查询文本
            
        Returns:
            知识库检索结果列表，每项包含内容和元数据
        """
        if not self.kb_retriever:
            logger.warning("通用知识库检索器未初始化，无法执行检索")
            return []
            
        try:
            results = self.kb_retriever.get_relevant_documents(query)
            
            # 将LangChain文档对象转换为带有源信息的字典
            processed_results = []
            for idx, doc in enumerate(results):
                processed_results.append({
                    'content': doc.page_content,
                    'metadata': doc.metadata,
                    'id': idx + 1  # 为了与文档块ID保持一致的引用方式
                })
                
            return processed_results
        except Exception as e:
            logger.exception(f"从通用知识库检索失败: {str(e)}")
            return []

    def _save_quiz_to_db(self, quiz_data: List[Dict], topic: str, difficulty: str) -> Optional[int]:
        """将通过验证的测验数据保存到数据库。"""
        if not quiz_data:
            return None
            
        try:
            # 确定测验标题
            if self.document:
                quiz_title = f"{self.document.title} - {topic}"
            else:
                quiz_title = f"通用知识 - {topic}"
                
            # 创建测验记录，document可以为None表示通用知识库生成
            quiz_obj = Quiz.objects.create(
                document=self.document, 
                title=quiz_title, 
                difficulty_level=difficulty,
                total_questions=len(quiz_data),
                metadata={
                    'is_general_knowledge': self.document is None,
                    'knowledge_source': "通用知识库" if self.document is None else "文档"
                }
            )
            
            # 使用bulk_create提高效率
            questions_to_create = []
            for i, q_data in enumerate(quiz_data):
                if 'type' in q_data:
                    q_data['question_type'] = q_data.pop('type')
                questions_to_create.append(Question(quiz=quiz_obj, **q_data, order=i + 1))
            
            Question.objects.bulk_create(questions_to_create)
            
            return quiz_obj.id
        except Exception as e:
            logger.error(f"保存测验数据到数据库失败: {e}")
            return None

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