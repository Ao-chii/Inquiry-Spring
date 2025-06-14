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
from ..ai_service_wrapper import ai_service
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
                document.metadata = extraction_result['metadata']
                document.is_processed = True
                document.processing_status = 'completed'
                document.processed_at = timezone.now()
                document.save()

                logger.info(f"文档处理成功: {filename}")

                # 兼容旧版本响应格式
                return JsonResponse({
                    'message': '文件上传成功',
                    'filename': filename,
                    'file_id': document.id,  # 使用新的document ID
                    'url': f'/media/documents/{document.id}/{filename}',
                    'data': {
                        'filename': filename,
                        'file_id': document.id
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

            if not filename:
                return JsonResponse({'error': '缺少文件名参数'}, status=400)

            # 查找已处理的文档
            document = Document.objects.filter(title=filename, is_processed=True).first()

            if not document or not document.content:
                return JsonResponse({'error': '文档不存在或未处理完成'}, status=404)

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

            # 使用AI生成总结
            summary_result = ai_service.summarize(document.content)
            summary = summary_result.get("text", "无法生成总结")

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

        # 生成总结
        summary_result = ai_service.summarize(document.content)

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
