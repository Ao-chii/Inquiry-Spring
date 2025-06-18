"""
管理命令：处理已存在文档的RAG向量化
用于修复已上传但未进行RAG处理的文档
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from inquiryspring_backend.documents.models import Document, DocumentChunk
from inquiryspring_backend.ai_services.rag_engine import RAGEngine
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = '处理已存在文档的RAG向量化，确保所有文档都能用于智能问答'

    def add_arguments(self, parser):
        parser.add_argument(
            '--document-id',
            type=int,
            help='指定处理特定文档ID',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='强制重新处理所有文档（包括已处理的）',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='仅显示需要处理的文档，不实际处理',
        )

    def handle(self, *args, **options):
        document_id = options.get('document_id')
        force = options.get('force', False)
        dry_run = options.get('dry_run', False)

        self.stdout.write(self.style.SUCCESS('开始处理文档RAG向量化...'))

        if document_id:
            # 处理指定文档
            try:
                document = Document.objects.get(id=document_id)
                documents = [document]
                self.stdout.write(f'处理指定文档: {document.title}')
            except Document.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f'文档ID {document_id} 不存在')
                )
                return
        else:
            # 处理所有符合条件的文档
            if force:
                documents = Document.objects.filter(is_processed=True)
                self.stdout.write(f'强制处理所有已处理文档: {documents.count()} 个')
            else:
                # 查找已处理但没有chunks的文档
                documents_without_chunks = []
                for doc in Document.objects.filter(is_processed=True):
                    chunk_count = DocumentChunk.objects.filter(document=doc).count()
                    if chunk_count == 0:
                        documents_without_chunks.append(doc)
                
                documents = documents_without_chunks
                self.stdout.write(f'发现需要RAG处理的文档: {len(documents)} 个')

        if not documents:
            self.stdout.write(self.style.SUCCESS('没有需要处理的文档'))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN 模式 - 仅显示需要处理的文档:'))
            for doc in documents:
                chunk_count = DocumentChunk.objects.filter(document=doc).count()
                self.stdout.write(f'  - ID: {doc.id}, 标题: {doc.title}, 现有chunks: {chunk_count}')
            return

        # 实际处理文档
        success_count = 0
        error_count = 0

        for document in documents:
            try:
                self.stdout.write(f'处理文档: {document.title} (ID: {document.id})')
                
                # 检查文档内容
                if not document.content:
                    self.stdout.write(
                        self.style.WARNING(f'  跳过: 文档内容为空')
                    )
                    continue

                # 创建RAG引擎并处理文档
                with transaction.atomic():
                    rag_engine = RAGEngine(document_id=document.id)
                    result = rag_engine.process_and_embed_document(force_reprocess=force)
                    
                    if result:
                        chunk_count = DocumentChunk.objects.filter(document=document).count()
                        self.stdout.write(
                            self.style.SUCCESS(f'  ✓ 成功处理，生成 {chunk_count} 个chunks')
                        )
                        success_count += 1
                    else:
                        self.stdout.write(
                            self.style.ERROR(f'  ✗ 处理失败')
                        )
                        error_count += 1

            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'  ✗ 处理异常: {str(e)}')
                )
                error_count += 1
                logger.exception(f"处理文档 {document.id} 时出错: {e}")

        # 输出处理结果
        self.stdout.write(self.style.SUCCESS(
            f'\n处理完成! 成功: {success_count}, 失败: {error_count}'
        ))

        if success_count > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'已成功处理 {success_count} 个文档，现在可以用于智能问答了！'
                )
            )
