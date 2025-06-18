import logging
import os
import re
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.conf import settings
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
from django.utils import timezone

from .models import Document
from ..ai_services.rag_engine import RAGEngine
from .document_processor import document_processor

logger = logging.getLogger(__name__)

# 支持的文件格式
ALLOWED_EXTENSIONS = {
    # 文本文件
    'txt', 'csv', 'json', 'xml', 'html', 'htm',
    # Office文档
    'docx',
    # PDF文件
    'pdf'
}


def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


def secure_filename(filename):
    """安全的文件名处理"""
    # 移除路径分隔符和危险字符
    filename = re.sub(r'[^\w\s\-\.]', '', filename).strip()
    # 替换空格为下划线
    filename = re.sub(r'[\-\s]+', '_', filename)
    return filename


# 删除了低级的FileUploadView，使用高级的DocumentProcessView代替


@method_decorator(csrf_exempt, name='dispatch')
class SummarizeView(View):
    """文档总结视图 - 兼容前端调用方式"""

    def post(self, request):
        """处理文件上传并生成文档 - 使用高级文档处理"""
        try:
            if 'file' not in request.FILES:
                return JsonResponse({'error': '没有选择文件'}, status=400)

            file = request.FILES['file']

            if file.name == '':
                return JsonResponse({'error': '没有选择文件'}, status=400)

            if not allowed_file(file.name):
                return JsonResponse({'error': '不支持的文件类型'}, status=400)

            # 检查文档处理器是否可用
            if not document_processor.available:
                return JsonResponse({
                    'error': '文档处理功能不可用'
                }, status=500)

            # 使用高级文档处理
            filename = secure_filename(file.name)
            upload_dir = os.path.join(settings.MEDIA_ROOT, 'uploads')
            os.makedirs(upload_dir, exist_ok=True)

            file_path = os.path.join(upload_dir, filename)

            with open(file_path, 'wb+') as destination:
                for chunk in file.chunks():
                    destination.write(chunk)

            # 验证文件
            validation = document_processor.validate_file(file_path, filename)
            if not validation['valid']:
                if os.path.exists(file_path):
                    os.remove(file_path)
                return JsonResponse({'error': validation['error']}, status=400)

            # 创建Document记录
            document = Document.objects.create(
                title=filename,
                file_type=validation['file_type'],
                file_size=validation['file_size'],
                processing_status='processing'
            )

            # 移动文件到最终位置
            final_dir = os.path.join(settings.MEDIA_ROOT, 'documents', str(document.id))
            os.makedirs(final_dir, exist_ok=True)
            final_path = os.path.join(final_dir, filename)
            os.rename(file_path, final_path)

            # 更新document记录
            document.file.name = f'documents/{document.id}/{filename}'
            document.save()

            # 提取文档内容
            extraction_result = document_processor.extract_text(final_path, filename)

            if extraction_result['success']:
                document.content = extraction_result['content']
                # 保存原始文件名到metadata中，方便后续查找
                metadata = extraction_result['metadata'] or {}
                metadata['original_filename'] = file.name  # 保存前端传递的原始文件名
                document.metadata = metadata
                document.is_processed = True
                document.processing_status = 'completed'
                document.processed_at = timezone.now()
                document.save()

                logger.info(f"文档处理成功: {filename}")

                # 立即进行RAG处理和向量化
                try:
                    from ..ai_services import process_document_for_rag
                    rag_processing_result = process_document_for_rag(document.id, force_reprocess=True)

                    if rag_processing_result:
                        logger.info(f"文档RAG处理成功: {filename}")
                    else:
                        logger.warning(f"文档RAG处理失败: {filename}")

                except Exception as e:
                    logger.error(f"文档RAG处理异常: {filename}, 错误: {e}")
                    # RAG处理失败不影响文档上传成功

                # 兼容旧版本响应格式，同时提供前端需要的信息
                return JsonResponse({
                    'message': '文件上传成功',
                    'filename': filename,
                    'file_id': document.id,  # 使用新的document ID
                    'url': f'/media/documents/{document.id}/{filename}',
                    'data': {
                        'filename': filename,
                        'file_id': document.id,
                        # 为前端智慧总结页面提供关键信息
                        'summary_filename': document.title,  # 前端调用总结时应该使用这个
                        'ready_for_summary': rag_processing_result
                    },
                    # 为前端智慧总结页面提供的额外信息
                    'document_info': {
                        'id': document.id,
                        'title': document.title,  # 前端应该用这个作为fileName参数
                        'filename': filename,     # 实际的文件名
                        'rag_processed': rag_processing_result,
                        'ready_for_summary': True,
                        'summary_url': f'/api/summarize/?fileName={document.title}',  # 前端可以直接使用的URL
                        'file_type': document.file_type,
                        'file_size': document.file_size
                    }
                })
            else:
                document.processing_status = 'failed'
                document.error_message = extraction_result['error']
                document.save()

                return JsonResponse({
                    'error': f'文档处理失败: {extraction_result["error"]}'
                }, status=500)

        except Exception as e:
            logger.error(f"文件上传失败: {e}")
            return JsonResponse({'error': f'上传失败: {str(e)}'}, status=500)

    def get(self, request):
        """生成文档总结 - 兼容前端调用方式"""
        try:
            filename = request.GET.get('fileName')

            # 记录请求信息用于调试
            logger.info(f"收到总结请求，fileName参数: '{filename}'")
            logger.info(f"完整GET参数: {dict(request.GET)}")

            if not filename or filename.strip() == '':
                # 如果没有文件名，自动使用最新上传的文档
                logger.info("fileName参数为空，自动使用最新文档")
                latest_doc = Document.objects.filter(is_processed=True).order_by('-uploaded_at').first()

                if not latest_doc:
                    return JsonResponse({
                        'error': '没有可用的文档',
                        'message': '请先上传文档'
                    }, status=404)

                filename = latest_doc.title
                logger.info(f"自动选择最新文档: {filename}")

                # 直接使用这个文档，不需要再次查找
                document = latest_doc
            else:
                # 智能查找已处理的文档
                document = None

            # 1. 首先尝试精确匹配title
            document = Document.objects.filter(title=filename, is_processed=True).first()

            # 2. 如果没找到，尝试通过文件名匹配
            if not document:
                # 获取所有已处理的文档，检查其filename属性
                for doc in Document.objects.filter(is_processed=True):
                    if doc.filename == filename:
                        document = doc
                        break

            # 3. 特殊处理：如果前端传递的是原始文件名，尝试匹配最近上传的文档
            if not document:
                # 检查是否是最近上传的文档的原始文件名
                recent_docs = Document.objects.filter(is_processed=True).order_by('-uploaded_at')[:5]
                for doc in recent_docs:
                    # 检查文件路径中是否包含原始文件名
                    if doc.file and filename in doc.file.name:
                        document = doc
                        logger.info(f"通过文件路径匹配找到文档: {filename} -> {doc.title}")
                        break
                    # 检查metadata中是否有原始文件名信息
                    if doc.metadata and isinstance(doc.metadata, dict):
                        original_name = doc.metadata.get('original_filename', '')
                        if original_name == filename:
                            document = doc
                            logger.info(f"通过metadata匹配找到文档: {filename} -> {doc.title}")
                            break

            # 4. 如果还没找到，尝试模糊匹配（去掉扩展名）
            if not document:
                base_filename = filename.replace('.pdf', '').replace('.docx', '').replace('.txt', '')
                document = Document.objects.filter(
                    title__icontains=base_filename,
                    is_processed=True
                ).first()

            # 5. 最后尝试通过文件路径匹配
            if not document:
                for doc in Document.objects.filter(is_processed=True):
                    if filename in doc.filename or doc.filename in filename:
                        document = doc
                        break

            # 6. 如果仍然没找到，且fileName不为空，尝试使用最新文档
            if not document and filename.strip():
                logger.warning(f"无法找到文件 {filename}，尝试使用最新文档")
                latest_doc = Document.objects.filter(is_processed=True).order_by('-uploaded_at').first()
                if latest_doc:
                    document = latest_doc
                    logger.info(f"使用最新文档代替: {latest_doc.title}")
                    # 更新filename为实际的文档标题，以便后续处理
                    filename = latest_doc.title

            if not document:
                # 记录调试信息
                logger.warning(f"未找到文件: {filename}")
                available_docs = Document.objects.filter(is_processed=True).order_by('-uploaded_at')[:5]
                doc_list = []
                for doc in available_docs:
                    doc_list.append({
                        'title': doc.title,
                        'filename': doc.filename,
                        'id': doc.id
                    })
                logger.warning(f"可用文档: {doc_list}")

                return JsonResponse({
                    'error': f'文档不存在: {filename}',
                    'message': '请检查文件名是否正确',
                    'available_documents': doc_list,
                    'searched_filename': filename
                }, status=404)

            if not document.content:
                return JsonResponse({'error': '文档内容为空'}, status=404)

            # 如果已有总结，直接返回
            if document.summary:
                logger.info(f"返回已有总结: {filename}")
                response_data = {
                    'AIMessage': document.summary,
                    'filename': filename,
                    'model': 'cached',
                    'provider': 'cached'
                }
                return JsonResponse(response_data)

            # 确保文档被正确处理和向量化
            from ..ai_services import process_document_for_rag
            rag_processed = process_document_for_rag(document.id, force_reprocess=True)

            if not rag_processed:
                logger.warning(f"文档 {document.id} RAG处理失败，但继续生成总结")

            # 使用AI生成总结
            from ..ai_services.rag_engine import RAGEngine
            rag_engine = RAGEngine(document_id=document.id)
            summary_result = rag_engine.handle_summary(
                document_id=document.id,
                user=getattr(request, 'user', None),
                session_id=request.session.session_key
            )

            if 'error' in summary_result:
                summary = f"总结生成失败: {summary_result['error']}"
                logger.error(f"文档总结生成失败: {summary_result['error']}")
            else:
                summary = summary_result.get("text", "无法生成总结")
                logger.info(f"文档总结生成成功: {filename}")

            # 保存总结
            document.summary = summary
            document.save()

            logger.info(f"文档总结生成成功: {filename}")

            # 确保响应格式兼容前端期望
            response_data = {
                'AIMessage': summary,
                'filename': filename,
                'model': summary_result.get('model', ''),
                'provider': summary_result.get('provider', '')
            }

            return JsonResponse(response_data)

        except Exception as e:
            logger.error(f"文档总结失败: {e}")
            return JsonResponse({'error': f'总结失败: {str(e)}'}, status=500)


@api_view(['GET'])
def document_list(request):
    """获取文档列表 - 使用新的Document模型"""
    try:
        documents = Document.objects.filter(is_processed=True).order_by('-uploaded_at')
        doc_list = []

        for doc in documents:
            doc_list.append({
                'id': doc.id,
                'title': doc.title,
                'file_type': doc.file_type,
                'file_size': doc.file_size,
                'uploaded_at': doc.uploaded_at.isoformat(),
                'processed_at': doc.processed_at.isoformat() if doc.processed_at else None,
                'has_summary': bool(doc.summary),
                'content_length': len(doc.content) if doc.content else 0
            })

        return Response({'documents': doc_list})

    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def document_delete(request, doc_id):
    """删除文档 - 使用新的Document模型"""
    try:
        document = Document.objects.get(id=doc_id)

        # 删除文件
        if document.file and os.path.exists(document.file.path):
            os.remove(document.file.path)
            # 删除目录（如果为空）
            try:
                os.rmdir(os.path.dirname(document.file.path))
            except OSError:
                pass  # 目录不为空或不存在

        # 删除数据库记录
        document.delete()

        return Response({'message': '文档删除成功'})

    except Document.DoesNotExist:
        return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# 删除了重复的DocumentProcessView类
# 其功能已被SummarizeView完全覆盖，且SummarizeView更完整

@api_view(['GET'])
def document_content(request, doc_id):
    """获取文档内容"""
    try:
        document = Document.objects.get(id=doc_id)

        return Response({
            'id': document.id,
            'title': document.title,
            'content': document.content,
            'file_type': document.file_type,
            'file_size': document.file_size,
            'is_processed': document.is_processed,
            'processing_status': document.processing_status,
            'metadata': document.metadata,
            'uploaded_at': document.uploaded_at.isoformat(),
            'processed_at': document.processed_at.isoformat() if document.processed_at else None
        })

    except Document.DoesNotExist:
        return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"获取文档内容失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def document_summarize(request, doc_id):
    """生成文档总结"""
    try:
        document = Document.objects.get(id=doc_id)

        if not document.is_processed:
            return Response({
                'error': '文档尚未处理完成'
            }, status=status.HTTP_400_BAD_REQUEST)

        if not document.content:
            return Response({
                'error': '文档内容为空'
            }, status=status.HTTP_400_BAD_REQUEST)

        # 生成总结 - 使用ai_services的RAGEngine
        from ..ai_services.rag_engine import RAGEngine
        rag_engine = RAGEngine(document_id=document.id)
        summary_result = rag_engine.handle_summary(document_id=document.id)

        if 'error' not in summary_result:
            # 保存总结到数据库
            document.summary = summary_result.get('text', '')
            document.save()

            logger.info(f"文档总结生成成功: {document.title}")

            return Response({
                'document_id': document.id,
                'title': document.title,
                'summary': summary_result.get('text', ''),
                'model': summary_result.get('model', ''),
                'provider': summary_result.get('provider', '')
            })
        else:
            return Response({
                'error': f'总结生成失败: {summary_result.get("error", "未知错误")}'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    except Document.DoesNotExist:
        return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"文档总结失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def document_formats(request):
    """获取支持的文档格式"""
    try:
        formats = document_processor.get_supported_formats()

        return Response({
            'supported_formats': formats,
            'processing_available': document_processor.available,
            'pdf_available': document_processor.pdf_available,
            'docx_available': document_processor.docx_available,
            'allowed_extensions': list(ALLOWED_EXTENSIONS)
        })

    except Exception as e:
        logger.error(f"获取支持格式失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def document_status(request, doc_id):
    """获取文档处理状态"""
    try:
        document = Document.objects.get(id=doc_id)

        return Response({
            'id': document.id,
            'title': document.title,
            'processing_status': document.processing_status,
            'is_processed': document.is_processed,
            'error_message': document.error_message,
            'uploaded_at': document.uploaded_at.isoformat(),
            'processed_at': document.processed_at.isoformat() if document.processed_at else None,
            'file_type': document.file_type,
            'file_size': document.file_size,
            'content_length': len(document.content) if document.content else 0,
            'has_summary': bool(document.summary)
        })

    except Document.DoesNotExist:
        return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"获取文档状态失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def generate_document_summary(request):
    """生成文档摘要 - 使用ai_services"""
    try:
        data = request.data
        document_id = data.get('document_id')

        if not document_id:
            return Response({'error': '缺少文档ID'}, status=status.HTTP_400_BAD_REQUEST)

        # 获取文档
        try:
            document = Document.objects.get(id=document_id, is_processed=True)
        except Document.DoesNotExist:
            return Response({'error': '文档不存在或未处理完成'}, status=status.HTTP_404_NOT_FOUND)

        # 确保文档已进行RAG处理
        from ..ai_services import process_document_for_rag
        rag_processed = process_document_for_rag(document_id, force_reprocess=False)

        if not rag_processed:
            logger.warning(f"文档 {document_id} RAG处理失败，尝试强制重新处理")
            rag_processed = process_document_for_rag(document_id, force_reprocess=True)

        if not rag_processed:
            return Response({'error': '文档RAG处理失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 生成摘要
        from ..ai_services.rag_engine import RAGEngine
        rag_engine = RAGEngine(document_id=document_id)
        summary_result = rag_engine.handle_summary(
            document_id=document_id,
            user=getattr(request, 'user', None),
            session_id=request.session.session_key
        )

        if 'error' in summary_result:
            return Response({'error': summary_result['error']}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 保存摘要到文档
        document.summary = summary_result.get('text', '')
        document.save()

        logger.info(f"文档摘要生成成功: {document.title}")

        return Response({
            'message': '摘要生成成功',
            'document_id': document_id,
            'document_title': document.title,
            'summary': summary_result.get('text', ''),
            'processing_time': summary_result.get('processing_time', 0)
        })

    except Exception as e:
        logger.error(f"生成文档摘要失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def ai_service_status(request):
    """获取AI服务状态"""
    try:
        from ..utils import get_ai_service_status
        from ..ai_services import get_document_chunks_count

        # 获取基础服务状态
        service_status = get_ai_service_status()

        # 添加文档统计信息
        total_documents = Document.objects.filter(is_processed=True).count()
        unprocessed_documents = Document.objects.filter(is_processed=False).count()

        # 统计已进行RAG处理的文档数量
        rag_processed_count = 0
        for doc in Document.objects.filter(is_processed=True):
            if get_document_chunks_count(doc.id) > 0:
                rag_processed_count += 1

        service_status.update({
            'document_statistics': {
                'total_documents': total_documents,
                'unprocessed_documents': unprocessed_documents,
                'rag_processed_documents': rag_processed_count,
                'rag_pending_documents': total_documents - rag_processed_count
            },
            'available_features': {
                'document_upload': True,
                'document_summary': service_status.get('service_available', False),
                'project_management': True,
                'project_summary': service_status.get('service_available', False),
                'quiz_generation': service_status.get('service_available', False),
                'chat': service_status.get('service_available', False)
            }
        })

        return Response(service_status)

    except Exception as e:
        logger.error(f"获取AI服务状态失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_uploaded_files(request):
    """获取已上传的文档列表 - 为前端智慧总结页面提供"""
    try:
        # 获取最近上传的已处理文档
        documents = Document.objects.filter(
            is_processed=True
        ).order_by('-uploaded_at')[:20]  # 限制返回最近20个文档

        file_list = []
        for doc in documents:
            # 检查是否已进行RAG处理
            from ..ai_services import get_document_chunks_count
            chunks_count = get_document_chunks_count(doc.id)

            file_list.append({
                'id': doc.id,
                'name': doc.title,
                'filename': doc.filename,
                'file_type': doc.file_type,
                'file_size': doc.file_size,
                'uploaded_at': doc.uploaded_at.isoformat(),
                'has_summary': bool(doc.summary),
                'rag_processed': chunks_count > 0,
                'chunks_count': chunks_count
            })

        return Response({
            'files': file_list,
            'total_count': len(file_list)
        })

    except Exception as e:
        logger.error(f"获取文档列表失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
def generate_summary_by_filename(request):
    """根据文件名生成摘要 - 兼容前端调用方式"""
    try:
        # 从请求中获取文件名
        filename = request.GET.get('fileName') or request.data.get('fileName')

        if not filename:
            return Response({'error': '缺少文件名参数'}, status=status.HTTP_400_BAD_REQUEST)

        # 查找对应的文档
        try:
            # 尝试通过title查找
            document = Document.objects.filter(
                title=filename,
                is_processed=True
            ).first()

            # 如果没找到，尝试通过filename查找
            if not document:
                document = Document.objects.filter(
                    title__icontains=filename.replace('.pdf', '').replace('.docx', ''),
                    is_processed=True
                ).first()

            if not document:
                return Response({'error': f'未找到文件: {filename}'}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            logger.error(f"查找文档失败: {e}")
            return Response({'error': '查找文档失败'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # 确保文档已进行RAG处理
        from ..ai_services import process_document_for_rag
        rag_processed = process_document_for_rag(document.id, force_reprocess=False)

        if not rag_processed:
            logger.warning(f"文档 {document.id} RAG处理失败，尝试强制重新处理")
            rag_processed = process_document_for_rag(document.id, force_reprocess=True)

        # 生成摘要
        from ..ai_services.rag_engine import RAGEngine
        rag_engine = RAGEngine(document_id=document.id)
        summary_result = rag_engine.handle_summary(
            document_id=document.id,
            user=getattr(request, 'user', None),
            session_id=request.session.session_key
        )

        if 'error' in summary_result:
            ai_message = f"抱歉，生成摘要时出现错误：{summary_result['error']}\n\n请稍后重试或联系管理员。"
        else:
            ai_message = summary_result.get('text', '无法生成摘要')

            # 保存摘要到文档
            document.summary = ai_message
            document.save()

        logger.info(f"为文件 {filename} 生成摘要成功")

        # 返回前端期望的格式
        return Response({
            'AIMessage': ai_message,
            'filename': filename,
            'document_id': document.id,
            'processing_time': summary_result.get('processing_time', 0),
            'rag_processed': rag_processed
        })

    except Exception as e:
        logger.error(f"生成摘要失败: {e}")
        return Response({
            'AIMessage': f"生成摘要时发生错误：{str(e)}\n\n请检查文档是否正确上传并稍后重试。",
            'error': str(e)
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def debug_documents(request):
    """调试端点：查看数据库中的文档信息"""
    try:
        documents = Document.objects.filter(is_processed=True).order_by('-uploaded_at')[:10]
        doc_info = []

        for doc in documents:
            doc_info.append({
                'id': doc.id,
                'title': doc.title,
                'filename': doc.filename,
                'file_path': doc.file.name if doc.file else '',
                'has_summary': bool(doc.summary),
                'uploaded_at': doc.uploaded_at.isoformat()
            })

        return Response({
            'total_documents': Document.objects.filter(is_processed=True).count(),
            'recent_documents': doc_info
        })

    except Exception as e:
        logger.error(f"调试文档信息失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def test_summarize(request):
    """测试总结功能"""
    try:
        # 获取最新的文档
        latest_doc = Document.objects.filter(is_processed=True).order_by('-uploaded_at').first()

        if not latest_doc:
            return Response({'error': '没有可用的文档'})

        # 模拟前端调用
        filename = latest_doc.title

        # 确保文档已进行RAG处理
        from ..ai_services import process_document_for_rag
        rag_processed = process_document_for_rag(latest_doc.id, force_reprocess=False)

        if not rag_processed:
            rag_processed = process_document_for_rag(latest_doc.id, force_reprocess=True)

        # 生成摘要
        from ..ai_services.rag_engine import RAGEngine
        rag_engine = RAGEngine(document_id=latest_doc.id)
        summary_result = rag_engine.handle_summary(
            document_id=latest_doc.id,
            user=getattr(request, 'user', None),
            session_id=request.session.session_key
        )

        if 'error' in summary_result:
            ai_message = f"摘要生成失败: {summary_result['error']}"
        else:
            ai_message = summary_result.get('text', '无法生成摘要')
            # 保存摘要
            latest_doc.summary = ai_message
            latest_doc.save()

        return Response({
            'AIMessage': ai_message,
            'filename': filename,
            'document_id': latest_doc.id,
            'rag_processed': rag_processed,
            'test_url': f'/api/summarize/?fileName={filename}'
        })

    except Exception as e:
        logger.error(f"测试总结功能失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_latest_document(request):
    """获取最新上传的文档信息 - 为前端智慧总结页面提供"""
    try:
        # 获取最新的已处理文档
        latest_doc = Document.objects.filter(is_processed=True).order_by('-uploaded_at').first()

        if not latest_doc:
            return Response({'error': '没有可用的文档'})

        # 检查RAG处理状态
        from ..ai_services import get_document_chunks_count
        chunks_count = get_document_chunks_count(latest_doc.id)

        return Response({
            'document': {
                'id': latest_doc.id,
                'title': latest_doc.title,  # 前端应该用这个作为fileName参数
                'filename': latest_doc.filename,
                'file_type': latest_doc.file_type,
                'file_size': latest_doc.file_size,
                'uploaded_at': latest_doc.uploaded_at.isoformat(),
                'has_summary': bool(latest_doc.summary),
                'rag_processed': chunks_count > 0,
                'chunks_count': chunks_count,
                'ready_for_summary': chunks_count > 0,
                'summary_url': f'/api/summarize/?fileName={latest_doc.title}'
            },
            'message': f'最新文档: {latest_doc.title}，可以用于生成总结'
        })

    except Exception as e:
        logger.error(f"获取最新文档失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def get_summarize_files(request):
    """获取可用于总结的文件列表 - 专为前端智慧总结页面设计"""
    try:
        # 获取已处理的文档
        documents = Document.objects.filter(is_processed=True).order_by('-uploaded_at')[:10]

        file_list = []
        for doc in documents:
            # 检查RAG处理状态
            from ..ai_services import get_document_chunks_count
            chunks_count = get_document_chunks_count(doc.id)

            file_list.append({
                'name': doc.title,  # 前端应该用这个作为fileName参数
                'filename': doc.filename,  # 实际的文件名
                'id': doc.id,
                'file_type': doc.file_type,
                'file_size': doc.file_size,
                'uploaded_at': doc.uploaded_at.isoformat(),
                'has_summary': bool(doc.summary),
                'rag_processed': chunks_count > 0,
                'ready_for_summary': chunks_count > 0,
                'summary_url': f'/api/summarize/?fileName={doc.title}'
            })

        return Response({
            'files': file_list,
            'total_count': len(file_list),
            'message': '可用于总结的文件列表',
            'usage_note': '前端应该使用 name 字段作为 fileName 参数调用总结API'
        })

    except Exception as e:
        logger.error(f"获取总结文件列表失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def quick_test_summary(request):
    """快速测试总结功能 - 使用最新文档"""
    try:
        # 获取最新的已处理文档
        latest_doc = Document.objects.filter(is_processed=True).order_by('-uploaded_at').first()

        if not latest_doc:
            return Response({'error': '没有可用的文档'})

        # 直接调用总结功能
        filename = latest_doc.title
        logger.info(f"快速测试：使用文档 {filename}")

        # 检查是否已有总结
        if latest_doc.summary:
            return Response({
                'AIMessage': latest_doc.summary,
                'filename': filename,
                'model': 'cached',
                'provider': 'cached',
                'test_info': '使用已缓存的总结'
            })

        # 确保RAG处理
        from ..ai_services import process_document_for_rag
        rag_processed = process_document_for_rag(latest_doc.id, force_reprocess=False)

        if not rag_processed:
            rag_processed = process_document_for_rag(latest_doc.id, force_reprocess=True)

        # 生成总结
        from ..ai_services.rag_engine import RAGEngine
        rag_engine = RAGEngine(document_id=latest_doc.id)
        summary_result = rag_engine.handle_summary(
            document_id=latest_doc.id,
            user=getattr(request, 'user', None),
            session_id=request.session.session_key
        )

        if 'error' in summary_result:
            ai_message = f"总结生成失败: {summary_result['error']}"
        else:
            ai_message = summary_result.get('text', '无法生成总结')
            # 保存总结
            latest_doc.summary = ai_message
            latest_doc.save()

        return Response({
            'AIMessage': ai_message,
            'filename': filename,
            'model': summary_result.get('model', ''),
            'provider': summary_result.get('provider', ''),
            'test_info': f'成功生成总结，文档ID: {latest_doc.id}',
            'rag_processed': rag_processed
        })

    except Exception as e:
        logger.error(f"快速测试总结失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def auto_summarize_latest(request):
    """自动总结最新上传的文档 - 解决前端fileName为空的问题"""
    try:
        # 获取最新的已处理文档
        latest_doc = Document.objects.filter(is_processed=True).order_by('-uploaded_at').first()

        if not latest_doc:
            return JsonResponse({
                'error': '没有可用的文档',
                'message': '请先上传文档'
            }, status=404)

        # 检查是否已有总结
        if latest_doc.summary:
            logger.info(f"返回已有总结: {latest_doc.title}")
            return JsonResponse({
                'AIMessage': latest_doc.summary,
                'filename': latest_doc.title,
                'model': 'cached',
                'provider': 'cached',
                'document_id': latest_doc.id
            })

        # 确保文档已进行RAG处理
        from ..ai_services import process_document_for_rag
        rag_processed = process_document_for_rag(latest_doc.id, force_reprocess=False)

        if not rag_processed:
            logger.warning(f"文档 {latest_doc.id} RAG处理失败，尝试强制重新处理")
            rag_processed = process_document_for_rag(latest_doc.id, force_reprocess=True)

        if not rag_processed:
            return JsonResponse({
                'error': '文档RAG处理失败',
                'message': '请稍后重试'
            }, status=500)

        # 生成摘要
        from ..ai_services.rag_engine import RAGEngine
        rag_engine = RAGEngine(document_id=latest_doc.id)
        summary_result = rag_engine.handle_summary(
            document_id=latest_doc.id,
            user=getattr(request, 'user', None),
            session_id=request.session.session_key
        )

        if 'error' in summary_result:
            ai_message = f"总结生成失败: {summary_result['error']}"
            logger.error(f"文档总结生成失败: {summary_result['error']}")
        else:
            ai_message = summary_result.get("text", "无法生成总结")
            logger.info(f"文档总结生成成功: {latest_doc.title}")

            # 保存总结
            latest_doc.summary = ai_message
            latest_doc.save()

        # 返回前端期望的格式
        return JsonResponse({
            'AIMessage': ai_message,
            'filename': latest_doc.title,
            'model': summary_result.get('model', ''),
            'provider': summary_result.get('provider', ''),
            'document_id': latest_doc.id,
            'processing_time': summary_result.get('processing_time', 0)
        })

    except Exception as e:
        logger.error(f"自动总结最新文档失败: {e}")
        return JsonResponse({
            'error': f'总结失败: {str(e)}',
            'message': '请稍后重试'
        }, status=500)
