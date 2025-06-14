# AI Services app

import logging

logger = logging.getLogger(__name__)


def process_document_for_rag(document_id: int, force_reprocess: bool = False) -> bool:
    """
    为文档进行RAG处理（分块和向量化）

    Args:
        document_id: 文档ID
        force_reprocess: 是否强制重新处理

    Returns:
        bool: 处理是否成功
    """
    try:
        from .rag_engine import RAGEngine

        # 创建RAG引擎实例
        rag_engine = RAGEngine(document_id=document_id)

        # 处理文档
        result = rag_engine.process_and_embed_document(force_reprocess=force_reprocess)

        if result:
            logger.info(f"文档 {document_id} RAG处理成功")
        else:
            logger.warning(f"文档 {document_id} RAG处理失败")

        return result

    except Exception as e:
        logger.error(f"文档 {document_id} RAG处理异常: {e}")
        return False


def get_document_chunks_count(document_id: int) -> int:
    """
    获取文档的chunks数量

    Args:
        document_id: 文档ID

    Returns:
        int: chunks数量
    """
    try:
        from inquiryspring_backend.documents.models import DocumentChunk
        return DocumentChunk.objects.filter(document_id=document_id).count()
    except Exception as e:
        logger.error(f"获取文档 {document_id} chunks数量失败: {e}")
        return 0



