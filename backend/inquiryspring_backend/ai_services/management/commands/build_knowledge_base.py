"""
构建通用知识库的管理命令
"""
import os
import logging
import json
from typing import List, Dict, Any, Optional
from django.core.management.base import BaseCommand
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document as LangchainDocument
from langchain_community.vectorstores import Chroma
from django.conf import settings

from inquiryspring_backend.ai_services.rag_engine import _GLOBAL_EMBEDDINGS, GENERAL_KNOWLEDGE_DIR

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = '构建通用知识库，从指定目录读取知识文档并构建向量索引'

    def add_arguments(self, parser):
        parser.add_argument('--source_dir', type=str, required=True, help='知识源文件目录')
        parser.add_argument('--subjects', nargs='+', type=str, help='处理的学科列表，例如: math physics chinese english')
        parser.add_argument('--chunk_size', type=int, default=1000, help='文本分块大小')
        parser.add_argument('--chunk_overlap', type=int, default=100, help='文本分块重叠大小')
        parser.add_argument('--clear', action='store_true', help='清除现有知识库并重新构建')

    def handle(self, *args, **options):
        source_dir = options['source_dir']
        subjects = options['subjects'] or ['math', 'physics', 'chemistry', 'biology', 'history', 'chinese', 'english']
        chunk_size = options['chunk_size']
        chunk_overlap = options['chunk_overlap']
        clear = options['clear']
        
        # 检查源目录是否存在
        if not os.path.exists(source_dir):
            self.stderr.write(self.style.ERROR(f"知识源目录 {source_dir} 不存在"))
            return
            
        # 检查是否需要清除现有知识库
        if clear and os.path.exists(GENERAL_KNOWLEDGE_DIR):
            self.stdout.write(f"清除现有知识库 {GENERAL_KNOWLEDGE_DIR}...")
            # 递归删除目录内容但保留目录
            for file_name in os.listdir(GENERAL_KNOWLEDGE_DIR):
                file_path = os.path.join(GENERAL_KNOWLEDGE_DIR, file_name)
                try:
                    if os.path.isfile(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        import shutil
                        shutil.rmtree(file_path)
                except Exception as e:
                    self.stderr.write(self.style.ERROR(f"删除文件 {file_path} 时出错: {e}"))
            self.stdout.write(self.style.SUCCESS("现有知识库已清除"))
            
        # 确保知识库目录存在
        os.makedirs(GENERAL_KNOWLEDGE_DIR, exist_ok=True)
        
        # 初始化文本分割器
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size, 
            chunk_overlap=chunk_overlap
        )
        
        # 处理每个学科的知识
        all_documents = []
        
        for subject in subjects:
            self.stdout.write(f"处理学科: {subject}")
            subject_dir = os.path.join(source_dir, subject)
            
            if not os.path.exists(subject_dir):
                self.stderr.write(self.style.WARNING(f"学科目录 {subject_dir} 不存在，跳过"))
                continue
                
            # 处理目录中的所有文本文件
            for root, _, files in os.walk(subject_dir):
                for file in files:
                    if file.endswith(('.txt', '.md', '.json', '.csv')):
                        file_path = os.path.join(root, file)
                        try:
                            # 读取文件内容
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                
                            # 根据文件类型处理内容
                            if file.endswith('.json'):
                                # JSON文件特殊处理
                                try:
                                    json_data = json.loads(content)
                                    if isinstance(json_data, list):
                                        for item in json_data:
                                            if isinstance(item, dict) and 'content' in item:
                                                # 提取内容并添加元数据
                                                text = item.get('content', '')
                                                metadata = {
                                                    'source': file_path,
                                                    'subject': subject,
                                                    'title': item.get('title', file),
                                                    'topic': item.get('topic', subject),
                                                    'type': 'knowledge'
                                                }
                                                # 分块处理
                                                chunks = text_splitter.split_text(text)
                                                for i, chunk in enumerate(chunks):
                                                    metadata_with_index = {**metadata, 'chunk_index': i}
                                                    all_documents.append(LangchainDocument(
                                                        page_content=chunk,
                                                        metadata=metadata_with_index
                                                    ))
                                    else:
                                        self.stderr.write(self.style.WARNING(f"JSON文件 {file_path} 不是列表格式，跳过"))
                                except json.JSONDecodeError:
                                    self.stderr.write(self.style.ERROR(f"解析JSON文件 {file_path} 失败"))
                            else:
                                # 普通文本文件处理
                                metadata = {
                                    'source': file_path,
                                    'subject': subject,
                                    'title': os.path.splitext(file)[0],
                                    'type': 'knowledge'
                                }
                                # 分块处理
                                chunks = text_splitter.split_text(content)
                                for i, chunk in enumerate(chunks):
                                    metadata_with_index = {**metadata, 'chunk_index': i}
                                    all_documents.append(LangchainDocument(
                                        page_content=chunk,
                                        metadata=metadata_with_index
                                    ))
                                    
                            self.stdout.write(f"处理文件: {file_path}")
                        except Exception as e:
                            self.stderr.write(self.style.ERROR(f"处理文件 {file_path} 时出错: {e}"))
        
        # 创建向量存储
        if all_documents:
            self.stdout.write(f"创建向量存储，共 {len(all_documents)} 个文档块")
            try:
                # 使用全局嵌入模型
                vector_store = Chroma.from_documents(
                    documents=all_documents,
                    embedding=_GLOBAL_EMBEDDINGS,
                    persist_directory=GENERAL_KNOWLEDGE_DIR
                )
                vector_store.persist()
                self.stdout.write(self.style.SUCCESS(f"通用知识库构建成功，存储在 {GENERAL_KNOWLEDGE_DIR}"))
            except Exception as e:
                self.stderr.write(self.style.ERROR(f"创建向量存储失败: {e}"))
        else:
            self.stderr.write(self.style.WARNING("没有找到任何有效的知识文档")) 