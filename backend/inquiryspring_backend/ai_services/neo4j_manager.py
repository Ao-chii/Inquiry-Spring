"""
Neo4j图数据库管理器 - 负责Neo4j连接、创建和查询
"""
import os
import logging
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError
from langchain.schema import Document as LangchainDocument
from langchain_community.graphs import Neo4jGraph
from django.conf import settings

from inquiryspring_backend.documents.models import DocumentChunk

logger = logging.getLogger(__name__)

# 从环境变量获取Neo4j连接信息
NEO4J_URI = os.environ.get("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.environ.get("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "password")


class Neo4jKnowledgeGraph:
    """Neo4j知识图谱管理器"""
    
    def __init__(self, uri=None, user=None, password=None):
        """初始化Neo4j连接"""
        self.uri = uri or NEO4J_URI
        self.user = user or NEO4J_USER
        self.password = password or NEO4J_PASSWORD
        self.driver = None
        self._connect()
        
    def _connect(self):
        """建立与Neo4j数据库的连接"""
        try:
            self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.password))
            # 测试连接
            with self.driver.session() as session:
                session.run("RETURN 1")
            logger.info(f"成功连接到Neo4j数据库: {self.uri}")
        except (ServiceUnavailable, AuthError) as e:
            logger.error(f"无法连接到Neo4j数据库: {str(e)}")
            self.driver = None
            
    def close(self):
        """关闭Neo4j连接"""
        if self.driver:
            self.driver.close()
            self.driver = None
            
    def is_connected(self) -> bool:
        """检查是否已连接到Neo4j"""
        if not self.driver:
            return False
            
        try:
            with self.driver.session() as session:
                session.run("RETURN 1")
            return True
        except Exception:
            return False
            
    def clear_document_graph(self, document_id: str):
        """清除特定文档的图谱数据"""
        if not self.is_connected():
            logger.error("未连接到Neo4j，无法清除图谱")
            return False
            
        try:
            with self.driver.session() as session:
                # 删除与文档关联的所有节点和关系
                session.run(
                    """
                    MATCH (n)
                    WHERE n.document_id = $document_id
                    DETACH DELETE n
                    """,
                    document_id=str(document_id)
                )
            logger.info(f"已清除文档 {document_id} 的知识图谱")
            return True
        except Exception as e:
            logger.error(f"清除知识图谱时出错: {str(e)}")
            return False
    
    def create_document_graph(self, document_id: str, entities_relations: List[Dict]):
        """
        从实体和关系列表创建文档知识图谱
        
        Args:
            document_id: 文档ID
            entities_relations: 包含实体和关系的列表
        """
        if not self.is_connected():
            logger.error("未连接到Neo4j，无法创建图谱")
            return False
            
        if not entities_relations:
            logger.warning("没有实体和关系数据，跳过图谱创建")
            return False
            
        # 首先清除现有的文档图谱
        self.clear_document_graph(document_id)
        
        # 处理实体和关系
        try:
            entities_added = set()  # 跟踪已添加的实体以避免重复
            
            with self.driver.session() as session:
                # 批量创建节点和关系
                for item in entities_relations:
                    source_entity = item.get("source")
                    target_entity = item.get("target")
                    relation = item.get("relation")
                    chunk_id = item.get("chunk_id", "unknown")
                    
                    if not source_entity or not target_entity or not relation:
                        continue
                        
                    # 创建源实体节点（如果尚未创建）
                    if source_entity not in entities_added:
                        session.run(
                            """
                            MERGE (s:Entity {name: $name})
                            ON CREATE SET s.document_id = $document_id
                            """,
                            name=source_entity,
                            document_id=str(document_id)
                        )
                        entities_added.add(source_entity)
                        
                    # 创建目标实体节点（如果尚未创建）
                    if target_entity not in entities_added:
                        session.run(
                            """
                            MERGE (t:Entity {name: $name})
                            ON CREATE SET t.document_id = $document_id
                            """,
                            name=target_entity,
                            document_id=str(document_id)
                        )
                        entities_added.add(target_entity)
                        
                    # 创建关系
                    session.run(
                        """
                        MATCH (s:Entity {name: $source}), (t:Entity {name: $target})
                        MERGE (s)-[r:RELATED {type: $relation}]->(t)
                        ON CREATE SET r.document_id = $document_id, r.chunk_id = $chunk_id
                        """,
                        source=source_entity,
                        target=target_entity,
                        relation=relation,
                        document_id=str(document_id),
                        chunk_id=str(chunk_id)
                    )
                    
            logger.info(f"成功为文档 {document_id} 创建知识图谱，包含 {len(entities_added)} 个实体")
            return True
        except Exception as e:
            logger.error(f"创建知识图谱时出错: {str(e)}")
            return False
            
    def query_graph_for_chunks(self, query_entities: List[str], document_id: str = None, limit: int = 10) -> List[DocumentChunk]:
        """
        根据实体查询图谱，并返回相关的完整DocumentChunk对象。
        这是优化的核心：返回丰富上下文，而非简单三元组。
        
        Args:
            query_entities: 从用户查询中提取的实体列表
            document_id: 可选的文档ID过滤
            limit: 返回结果的最大数量
            
        Returns:
            相关的DocumentChunk对象列表
        """
        if not self.is_connected():
            logger.error("未连接到Neo4j，无法执行查询")
            return []
            
        if not query_entities:
            return []
            
        try:
            chunk_ids = set()
            with self.driver.session() as session:
                # 构建查询，匹配任何一个实体
                # Cypher查询：查找包含任何一个查询实体的关系，并收集这些关系关联的chunk_id
                query = f"""
                UNWIND $entities AS entityName
                MATCH (s:Entity)-[r:RELATED]->(t:Entity)
                WHERE s.name CONTAINS entityName OR t.name CONTAINS entityName
                {'AND s.document_id = $document_id' if document_id else ''}
                RETURN COLLECT(DISTINCT r.chunk_id) AS chunkIds
                LIMIT 1
                """
                
                params = {"entities": query_entities}
                if document_id:
                    params["document_id"] = str(document_id)
                
                result = session.run(query, **params)
                record = result.single()
                if record and record["chunkIds"]:
                    chunk_ids.update(record["chunkIds"])
            
            if not chunk_ids:
                return []
            
            # 根据chunk_ids一次性从数据库中获取所有DocumentChunk对象
            # 限制返回数量
            final_chunk_ids = list(chunk_ids)[:limit]
            
            # 使用Django ORM获取完整的块数据
            # 使用 in_bulk 来保持chunk_id的顺序，并方便查找
            chunks_map = DocumentChunk.objects.in_bulk(final_chunk_ids)
            # 按照 final_chunk_ids 的顺序返回结果
            ordered_chunks = [chunks_map[cid] for cid in final_chunk_ids if cid in chunks_map]

            logger.info(f"图谱检索找到 {len(ordered_chunks)} 个相关文本块。")
            return ordered_chunks
            
        except Exception as e:
            logger.error(f"查询知识图谱时出错: {str(e)}")
            return []
            
    def process_entities_from_llm(self, langchain_docs: List[LangchainDocument], llm, document_id: str) -> bool:
        """
        使用LLM提取文档的实体和关系，并将其存储到Neo4j
        
        Args:
            langchain_docs: LangChain文档列表
            llm: LLM接口
            document_id: 文档ID
            
        Returns:
            处理是否成功
        """
        try:
            from langchain.chains import create_extraction_chain
            
            # 定义实体关系提取模式
            schema = {
                "properties": {
                    "source": {"type": "string"},
                    "relation": {"type": "string"},
                    "target": {"type": "string"}
                },
                "required": ["source", "relation", "target"]
            }
            
            all_entities_relations = []
            
            # 处理每个文档块
            for i, doc in enumerate(langchain_docs):
                chunk_content = doc.page_content
                chunk_id = doc.metadata.get('chunk_id', f"chunk_{i}")
                
                if not chunk_content.strip():
                    continue
                    
                prompt = f"""
                从以下文本中提取实体和它们之间的关系：
                
                {chunk_content}
                
                请确保提取重要的命名实体（人物、组织、概念、地点等）和它们之间的具体关系。
                每个关系应包含源实体、目标实体和它们之间的关系类型。
                """
                
                # 调用LLM提取实体关系
                try:
                    chain = create_extraction_chain(schema=schema, llm=llm)
                    result = chain.run(prompt)
                    
                    # 为每个提取的关系添加chunk_id
                    for item in result:
                        item['chunk_id'] = chunk_id
                    
                    all_entities_relations.extend(result)
                except Exception as e:
                    logger.warning(f"处理文档块 {chunk_id} 时提取实体关系失败: {str(e)}")
                    continue
            
            # 将提取的实体关系保存到Neo4j
            success = self.create_document_graph(document_id, all_entities_relations)
            
            # 记录实体和关系的数量
            entity_count = len({er['source'] for er in all_entities_relations} | {er['target'] for er in all_entities_relations})
            relation_count = len(all_entities_relations)
            
            logger.info(f"从文档 {document_id} 中提取了 {entity_count} 个实体和 {relation_count} 个关系")
            
            return success
        except Exception as e:
            logger.error(f"处理文档实体时出错: {str(e)}")
            return False


# 全局Neo4j知识图谱管理器单例
_GLOBAL_NEO4J = None

def initialize_neo4j():
    """初始化全局Neo4j知识图谱管理器"""
    global _GLOBAL_NEO4J
    try:
        _GLOBAL_NEO4J = Neo4jKnowledgeGraph()
        if _GLOBAL_NEO4J.is_connected():
            logger.info("Neo4j知识图谱管理器初始化成功")
            return True
        else:
            logger.warning("Neo4j知识图谱管理器初始化失败：无法连接到数据库")
            _GLOBAL_NEO4J = None
            return False
    except Exception as e:
        logger.error(f"初始化全局Neo4j知识图谱管理器失败: {str(e)}")
        _GLOBAL_NEO4J = None
        return False 