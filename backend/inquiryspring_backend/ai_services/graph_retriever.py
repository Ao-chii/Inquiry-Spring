# backend/inquiryspring_backend/ai_services/graph_retriever.py
import logging
from typing import List, Optional, Any
from pydantic import BaseModel, Field

from langchain.schema import BaseRetriever, Document as LangchainDocument
from langchain.callbacks.manager import CallbackManagerForRetrieverRun
from .neo4j_manager import _GLOBAL_NEO4J

logger = logging.getLogger(__name__)

# Pydantic模型用于从查询中提取实体
class QueryEntities(BaseModel):
    """从用户查询中提取的实体列表"""
    entities: List[str] = Field(
        description="从用户查询中识别出的关键实体或概念列表，用于知识图谱查询。"
    )

class Neo4jKnowledgeGraphRetriever(BaseRetriever):
    """
    一个基于Neo4j知识图谱的智能检索器。
    它使用LLM从查询中提取实体，然后在Neo4j图数据库中查找相关信息，
    并返回完整的原始文本块作为上下文。
    """
    document_id: Optional[str] = None
    k: int = 5
    llm_client: Optional[Any] = None

    def _extract_entities_from_query(self, query: str) -> List[str]:
        """使用LLM从用户查询中提取实体"""
        if not self.llm_client:
            logger.warning("LLM客户端未提供，回退到简单的关键词拆分。")
            return [term for term in query.lower().split() if len(term) > 1]
            
        try:
            from .structured_output import StructuredOutputProcessor
            processor = StructuredOutputProcessor()
            
            prompt = f"从以下用户问题中提取出最关键的实体和概念，用于在知识图谱中进行精确查找。请只关注核心名词。用户问题: '{query}'"
            
            # 使用结构化输出确保返回的是实体列表
            validated_response = processor.validate_and_fix(
                text=f'{{"entities": []}}', # 提供一个dummy text，让修复流程启动
                model_class=QueryEntities,
                llm_client=self.llm_client,
                task_type="entity_extraction",
                # 重写prompt以进行修复
                correction_prompt=prompt
            )
            
            entities = validated_response.entities
            logger.info(f"从查询 '{query}' 中提取到实体: {entities}")
            return entities if entities else [query] # 如果没提取到，使用整个查询作为关键词
        except Exception as e:
            logger.error(f"从查询中提取实体失败: {e}，回退到关键词拆分。")
            return [term for term in query.lower().split() if len(term) > 1]

    def _get_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[LangchainDocument]:
        """
        从Neo4j知识图谱中检索与查询相关的文档（三元组）。
        """
        if not _GLOBAL_NEO4J or not _GLOBAL_NEO4J.is_connected():
            logger.warning("Neo4j知识图谱未连接，无法执行检索")
            return []

        try:
            # 1. 从查询中提取实体
            query_entities = self._extract_entities_from_query(query)
            
            if not query_entities:
                return []
            
            # 2. 使用提取的实体查询图谱，获取相关的完整文本块
            document_chunks = _GLOBAL_NEO4J.query_graph_for_chunks(
                query_entities=query_entities,
                document_id=self.document_id,
                limit=self.k
            )
            
            # 3. 将DocumentChunk对象转换为Langchain文档格式
            results = []
            for chunk in document_chunks:
                metadata = {
                    'source': 'graph',
                    'document_id': str(chunk.document_id),
                    'chunk_id': str(chunk.id),
                }
                results.append(LangchainDocument(page_content=chunk.content, metadata=metadata))
            
            return results
        except Exception as e:
            logger.error(f"在Neo4j知识图谱检索过程中出错: {e}")
            return []

    async def _aget_relevant_documents(
        self, query: str, *, run_manager: CallbackManagerForRetrieverRun
    ) -> List[LangchainDocument]:
        # 当前非异步实现，直接调用同步方法
        return self._get_relevant_documents(query, run_manager=run_manager)


# 为了向后兼容，保留原始类名但使用Neo4j实现
class KnowledgeGraphRetriever(Neo4jKnowledgeGraphRetriever):
    """兼容层，保持原始类名但使用Neo4j实现"""
    pass 