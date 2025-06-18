#!/usr/bin/env python
"""
RAG处理失败诊断工具
"""

import os
import sys
import django

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inquiryspring_backend.settings')
django.setup()

from inquiryspring_backend.documents.models import Document
from inquiryspring_backend.ai_services.rag_engine import RAGEngine
from inquiryspring_backend.ai_services import process_document_for_rag
import logging

# 设置详细日志
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def diagnose_document(document_id):
    """诊断特定文档的RAG处理问题"""
    print(f"🔍 诊断文档 {document_id} 的RAG处理问题...")
    
    try:
        # 1. 检查文档是否存在
        try:
            document = Document.objects.get(id=document_id)
            print(f"✅ 文档存在: {document.title}")
            print(f"   文件类型: {document.file_type}")
            print(f"   文件大小: {document.file_size} bytes")
            print(f"   是否已处理: {document.is_processed}")
            print(f"   内容长度: {len(document.content or '')} 字符")
        except Document.DoesNotExist:
            print(f"❌ 文档 {document_id} 不存在")
            return False
        
        # 2. 检查文件是否可访问
        if document.file:
            try:
                document.file.seek(0)
                file_content = document.file.read()
                print(f"✅ 文件可读取: {len(file_content)} bytes")
                
                # 检查文件内容
                if len(file_content) == 0:
                    print("❌ 文件内容为空")
                    return False
                    
            except Exception as e:
                print(f"❌ 文件读取失败: {e}")
                return False
        else:
            print("❌ 文件对象不存在")
            return False
        
        # 3. 检查文档内容提取
        print(f"\n🔍 检查文档内容提取...")
        if document.content:
            print(f"✅ 文档已有内容: {len(document.content)} 字符")
            print(f"   内容预览: {document.content[:200]}...")
        else:
            print("⚠️ 文档内容为空，尝试提取...")
            
            # 尝试手动提取内容
            try:
                from inquiryspring_backend.documents.document_processor import DocumentProcessor
                processor = DocumentProcessor()

                # 保存文件到临时位置进行处理
                import tempfile
                with tempfile.NamedTemporaryFile(delete=False, suffix=f'.{document.file_type}') as temp_file:
                    document.file.seek(0)
                    temp_file.write(document.file.read())
                    temp_file_path = temp_file.name

                # 使用DocumentProcessor提取内容
                result = processor.extract_text(temp_file_path, document.title)

                # 清理临时文件
                os.unlink(temp_file_path)

                if result['success']:
                    extracted_content = result['content']
                else:
                    print(f"❌ 文档处理器提取失败: {result['error']}")
                    extracted_content = ""
                
                if extracted_content:
                    print(f"✅ 成功提取内容: {len(extracted_content)} 字符")
                    print(f"   内容预览: {extracted_content[:200]}...")
                    
                    # 更新文档内容
                    document.content = extracted_content
                    document.save()
                    print("✅ 文档内容已保存")
                else:
                    print("❌ 内容提取失败或为空")
                    return False
                    
            except Exception as e:
                print(f"❌ 内容提取异常: {e}")
                return False
        
        # 4. 检查RAG引擎初始化
        print(f"\n🔍 检查RAG引擎初始化...")
        try:
            rag_engine = RAGEngine(document_id=document.id)
            print("✅ RAG引擎初始化成功")
            
            # 检查文档是否正确加载
            if rag_engine.document:
                print(f"✅ 文档已加载到RAG引擎: {rag_engine.document.title}")
            else:
                print("❌ 文档未加载到RAG引擎")
                return False
                
        except Exception as e:
            print(f"❌ RAG引擎初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
        
        # 5. 检查向量存储目录
        print(f"\n🔍 检查向量存储...")
        vector_store_dir = f"vector_store/{document.id}"
        if os.path.exists(vector_store_dir):
            print(f"✅ 向量存储目录存在: {vector_store_dir}")
            files = os.listdir(vector_store_dir)
            print(f"   文件数量: {len(files)}")
            for file in files[:5]:  # 只显示前5个文件
                print(f"   - {file}")
        else:
            print(f"⚠️ 向量存储目录不存在: {vector_store_dir}")
        
        # 6. 尝试RAG处理
        print(f"\n🔍 尝试RAG处理...")
        try:
            result = rag_engine.process_and_embed_document(force_reprocess=True)
            if result:
                print("✅ RAG处理成功")
                
                # 更新文档状态
                document.is_processed = True
                document.save()
                print("✅ 文档状态已更新")
                
                return True
            else:
                print("❌ RAG处理返回False")
                return False
                
        except Exception as e:
            print(f"❌ RAG处理异常: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    except Exception as e:
        print(f"❌ 诊断过程异常: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_rag_environment():
    """检查RAG环境配置"""
    print("🔍 检查RAG环境配置...")
    
    # 检查向量存储根目录
    vector_store_root = "vector_store"
    if os.path.exists(vector_store_root):
        print(f"✅ 向量存储根目录存在: {vector_store_root}")
        print(f"   权限: {oct(os.stat(vector_store_root).st_mode)[-3:]}")
    else:
        print(f"❌ 向量存储根目录不存在: {vector_store_root}")
        try:
            os.makedirs(vector_store_root, exist_ok=True)
            print(f"✅ 已创建向量存储目录")
        except Exception as e:
            print(f"❌ 创建向量存储目录失败: {e}")
    
    # 检查embedding模型
    print(f"\n🔍 检查embedding模型...")
    try:
        from sentence_transformers import SentenceTransformer
        model = SentenceTransformer('sentence-transformers/all-mpnet-base-v2')
        print("✅ Embedding模型加载成功")
        
        # 测试编码
        test_text = "这是一个测试文本"
        embedding = model.encode([test_text])
        print(f"✅ 文本编码成功: {embedding.shape}")
        
    except Exception as e:
        print(f"❌ Embedding模型加载失败: {e}")
    
    # 检查Chroma
    print(f"\n🔍 检查Chroma向量数据库...")
    try:
        import chromadb
        print("✅ Chroma库可用")
        
        # 测试创建客户端
        client = chromadb.Client()
        print("✅ Chroma客户端创建成功")
        
    except Exception as e:
        print(f"❌ Chroma检查失败: {e}")

def find_latest_failed_document():
    """查找最新的失败文档"""
    print("🔍 查找最新的失败文档...")
    
    # 查找最新的未处理文档
    failed_docs = Document.objects.filter(is_processed=False).order_by('-id')[:5]
    
    if failed_docs:
        print(f"📄 找到 {len(failed_docs)} 个未处理文档:")
        for doc in failed_docs:
            print(f"   ID: {doc.id}, 标题: {doc.title}, 类型: {doc.file_type}")
        
        return failed_docs[0].id
    else:
        print("📄 没有找到未处理的文档")
        return None

def main():
    """主函数"""
    print("🔧 RAG处理失败诊断工具")
    print("=" * 50)
    
    # 检查环境
    check_rag_environment()
    
    print("\n" + "=" * 50)
    
    # 查找失败的文档
    if len(sys.argv) > 1:
        document_id = int(sys.argv[1])
    else:
        document_id = find_latest_failed_document()
        if not document_id:
            print("❌ 没有找到需要诊断的文档")
            return
    
    # 诊断文档
    success = diagnose_document(document_id)
    
    print("\n" + "=" * 50)
    if success:
        print("🎉 RAG处理问题已解决！")
    else:
        print("❌ RAG处理仍有问题，需要进一步调查")
        print("\n💡 可能的解决方案:")
        print("1. 检查文件是否损坏")
        print("2. 检查磁盘空间是否充足")
        print("3. 检查向量存储目录权限")
        print("4. 重新安装sentence-transformers")
        print("5. 检查GPU/CUDA配置")

if __name__ == "__main__":
    main()
