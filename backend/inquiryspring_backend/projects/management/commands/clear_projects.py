from django.core.management.base import BaseCommand
from django.conf import settings
from inquiryspring_backend.projects.models import Project, ProjectDocument, ProjectStats
from inquiryspring_backend.documents.models import Document
import os
import shutil
import glob


class Command(BaseCommand):
    help = '清理项目数据库中的所有内容，包括关联的文档和文件'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='确认删除所有项目数据',
        )
        parser.add_argument(
            '--keep-files',
            action='store_true',
            help='保留文件，只删除数据库记录',
        )

    def handle(self, *args, **options):
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    '这将删除所有项目数据！请使用 --confirm 参数确认操作'
                )
            )
            return

        self.stdout.write('开始清理项目数据...')
        
        # 统计信息
        project_count = Project.objects.count()
        document_count = Document.objects.count()
        project_doc_count = ProjectDocument.objects.count()
        stats_count = ProjectStats.objects.count()
        
        self.stdout.write(f'找到 {project_count} 个项目')
        self.stdout.write(f'找到 {document_count} 个文档')
        self.stdout.write(f'找到 {project_doc_count} 个项目-文档关联')
        self.stdout.write(f'找到 {stats_count} 个项目统计记录')

        try:
            # 1. 删除文件（如果不保留文件）
            if not options['keep_files']:
                self.stdout.write('删除文档文件...')
                
                # 删除media/documents目录下的所有文档文件
                documents_dir = os.path.join(settings.MEDIA_ROOT, 'documents')
                if os.path.exists(documents_dir):
                    shutil.rmtree(documents_dir, ignore_errors=True)
                    self.stdout.write(f'已删除文档目录: {documents_dir}')
                
                # 删除media/uploads目录下的临时文件
                uploads_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
                if os.path.exists(uploads_dir):
                    shutil.rmtree(uploads_dir, ignore_errors=True)
                    self.stdout.write(f'已删除上传目录: {uploads_dir}')
                
                # 删除vector_store目录下的向量数据库文件
                vector_store_dir = os.path.join(settings.BASE_DIR, 'vector_store')
                if os.path.exists(vector_store_dir):
                    shutil.rmtree(vector_store_dir, ignore_errors=True)
                    self.stdout.write(f'已删除向量存储目录: {vector_store_dir}')

            # 2. 删除数据库记录
            self.stdout.write('删除数据库记录...')
            
            # 删除项目统计
            deleted_stats = ProjectStats.objects.all().delete()
            self.stdout.write(f'已删除 {deleted_stats[0]} 个项目统计记录')
            
            # 删除项目-文档关联
            deleted_project_docs = ProjectDocument.objects.all().delete()
            self.stdout.write(f'已删除 {deleted_project_docs[0]} 个项目-文档关联')
            
            # 删除文档
            deleted_documents = Document.objects.all().delete()
            self.stdout.write(f'已删除 {deleted_documents[0]} 个文档记录')
            
            # 删除项目
            deleted_projects = Project.objects.all().delete()
            self.stdout.write(f'已删除 {deleted_projects[0]} 个项目记录')

            self.stdout.write(
                self.style.SUCCESS('项目数据清理完成！')
            )

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'清理过程中出现错误: {e}')
            )
