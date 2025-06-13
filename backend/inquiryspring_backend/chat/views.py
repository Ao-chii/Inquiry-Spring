import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.utils.decorators import method_decorator
from django.views import View
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import json
from datetime import datetime

from .models import ChatSession, Message, Conversation
from ..ai_service_wrapper import ai_service
from ..documents.models import Document, UploadedFile

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class ChatView(View):
    """聊天视图 - 兼容前端的POST和GET请求"""
    
    def post(self, request):
        """处理用户消息"""
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()

            if not user_message:
                return JsonResponse({'error': '消息不能为空'}, status=400)

            logger.info(f"收到用户消息: {user_message}")

            # 自动使用最近上传的文档作为上下文
            context = ""
            used_document = None

            # 获取最近上传的已处理文档
            recent_documents = Document.objects.filter(
                is_processed=True
            ).order_by('-uploaded_at')[:1]

            if recent_documents.exists():
                # 始终使用最近的文档作为上下文
                latest_document = recent_documents.first()
                context = latest_document.content
                used_document = latest_document
                logger.info(f"使用最近文档作为上下文: {latest_document.title}")

            # 使用AI服务生成回复（带上下文）
            if context:
                # 构建带文档上下文的提示
                enhanced_message = f"""
基于以下文档内容回答用户问题：

文档标题：{used_document.title}
文档内容：
{context[:3000]}  # 限制上下文长度

用户问题：
{user_message}

请基于文档内容给出准确、详细的回答。如果问题与文档内容无关，请说明并尝试给出一般性回答。
"""
                ai_result = ai_service.chat(enhanced_message)

                # 在回复前添加文档引用信息
                ai_response = ai_result.get("text", "抱歉，AI服务暂时不可用")
                ai_response = f"📄 基于文档《{used_document.title}》回答：\n\n{ai_response}"
            else:
                ai_result = ai_service.chat(user_message)
                ai_response = ai_result.get("text", "抱歉，AI服务暂时不可用")

            # 保存到数据库
            chat_session = ChatSession.objects.create(
                user_message=user_message,
                ai_response=ai_response
            )

            logger.info(f"AI回复生成成功: {ai_response[:100]}...")

            return JsonResponse({
                'status': 'success',
                'message': '消息已发送',
                'session_id': chat_session.id,
                'has_context': bool(context),
                'used_document': used_document.title if used_document else None
            })
            
        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            return JsonResponse({
                'status': 'error',
                'error': f'处理失败: {str(e)}'
            }, status=500)
    
    def get(self, request):
        """获取最新的AI回复"""
        try:
            latest_message = ChatSession.objects.order_by('-timestamp').first()

            if latest_message:
                # 返回包含status字段的响应，以便中间件不再包装
                response_data = {
                    'status': 'success',
                    'user_message': latest_message.user_message,
                    'ai_response': latest_message.ai_response,
                    'AIMessage': latest_message.ai_response,  # 兼容前端
                    'timestamp': latest_message.timestamp.isoformat()
                }
                return JsonResponse(response_data)
            else:
                response_data = {
                    'status': 'success',
                    'user_message': '',
                    'ai_response': '您好！我是AI学习助手，有什么可以帮助您的吗？',
                    'AIMessage': '您好！我是AI学习助手，有什么可以帮助您的吗？',
                    'timestamp': datetime.now().isoformat()
                }
                return JsonResponse(response_data)

        except Exception as e:
            logger.error(f"获取聊天记录失败: {e}")
            return JsonResponse({
                'status': 'error',
                'error': f'获取失败: {str(e)}'
            }, status=500)


@api_view(['GET'])
def chat_history(request):
    """获取聊天历史"""
    try:
        messages = ChatSession.objects.all()[:20]  # 最近20条
        history = []
        
        for msg in messages:
            history.append({
                'id': msg.id,
                'user_message': msg.user_message,
                'ai_response': msg.ai_response,
                'timestamp': msg.timestamp.isoformat()
            })
        
        return Response({'history': history})
        
    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# 删除了聊天反馈功能


@method_decorator(csrf_exempt, name='dispatch')
class ChatDocumentUploadView(View):
    """聊天中的文档上传视图 - 兼容前端文件上传"""

    def post(self, request):
        """上传文档用于聊天上下文"""
        try:
            if 'file' not in request.FILES:
                return JsonResponse({'error': '没有选择文件'}, status=400)

            file = request.FILES['file']

            if file.name == '':
                return JsonResponse({'error': '没有选择文件'}, status=400)

            # 导入文档处理相关模块
            from ..documents.views import allowed_file
            from ..documents.document_processor import document_processor
            from django.conf import settings
            from django.utils import timezone
            import os
            import re

            def secure_filename(filename):
                """安全的文件名处理"""
                # 移除路径分隔符和危险字符
                filename = re.sub(r'[^\w\s\-\.]', '', filename).strip()
                # 替换空格为下划线
                filename = re.sub(r'[\-\s]+', '_', filename)
                return filename

            if not allowed_file(file.name):
                return JsonResponse({'error': '不支持的文件类型'}, status=400)

            # 检查文档处理器是否可用
            if not document_processor.available:
                return JsonResponse({
                    'error': '文档处理功能不可用'
                }, status=500)

            # 保存文件到临时位置
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
                # 删除临时文件
                if os.path.exists(file_path):
                    os.remove(file_path)
                return JsonResponse({'error': validation['error']}, status=400)

            # 创建Document记录
            document = Document.objects.create(
                title=filename,  # 使用原始文件名
                file_type=validation['file_type'],
                file_size=validation['file_size'],
                processing_status='processing'
            )

            # 更新文件路径（包含document ID）
            final_dir = os.path.join(settings.MEDIA_ROOT, 'documents', str(document.id))
            os.makedirs(final_dir, exist_ok=True)
            final_path = os.path.join(final_dir, filename)

            # 移动文件到最终位置
            os.rename(file_path, final_path)

            # 更新document记录
            document.file.name = f'documents/{document.id}/{filename}'
            document.save()

            # 提取文档内容
            extraction_result = document_processor.extract_text(final_path, filename)

            if extraction_result['success']:
                # 更新文档记录
                document.content = extraction_result['content']
                document.metadata = extraction_result['metadata']
                document.is_processed = True
                document.processing_status = 'completed'
                document.processed_at = timezone.now()
                document.save()

                logger.info(f"聊天文档处理成功: {filename}")

                return JsonResponse({
                    'message': '文档上传成功，现在可以基于此文档进行问答',
                    'document_id': document.id,
                    'filename': filename,
                    'content_length': len(extraction_result['content']),
                    'file_type': validation['file_type'],
                    'status': 'success'
                })
            else:
                # 处理失败
                document.processing_status = 'failed'
                document.error_message = extraction_result['error']
                document.save()

                return JsonResponse({
                    'error': f'文档处理失败: {extraction_result["error"]}',
                    'document_id': document.id
                }, status=500)

        except Exception as e:
            logger.error(f"聊天文档上传失败: {e}")
            return JsonResponse({'error': f'上传失败: {str(e)}'}, status=500)


@api_view(['GET'])
def chat_documents(request):
    """获取聊天中可用的文档列表"""
    try:
        documents = Document.objects.filter(
            title__startswith='聊天文档-',
            is_processed=True
        ).order_by('-uploaded_at')[:10]

        doc_list = []
        for doc in documents:
            doc_list.append({
                'id': doc.id,
                'title': doc.title,
                'filename': doc.title.replace('聊天文档-', ''),
                'file_type': doc.file_type,
                'content_length': len(doc.content) if doc.content else 0,
                'uploaded_at': doc.uploaded_at.isoformat()
            })

        return Response({'documents': doc_list})

    except Exception as e:
        logger.error(f"获取聊天文档列表失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
