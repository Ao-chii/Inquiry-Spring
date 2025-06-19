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
from ..ai_services.rag_engine import RAGEngine
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

            # 创建RAG引擎实例并使用AI服务生成回复
            rag_engine = RAGEngine()

            if context and used_document:
                # 智能判断问题是否需要基于文档回答
                should_use_document = self._should_use_document_context(user_message)

                if should_use_document:
                    # 有上下文且问题相关 - 使用文档ID进行基于文档的聊天
                    ai_result = rag_engine.handle_chat(
                        query=user_message,
                        document_id=used_document.id
                    )

                    # 检查是否实际使用了文档内容
                    is_generic_answer = ai_result.get("is_generic_answer", False)
                    sources = ai_result.get("sources", [])

                    ai_response = ai_result.get("answer", "抱歉，AI服务暂时不可用")

                    # 只有在实际使用了文档内容时才添加文档引用信息
                    if not is_generic_answer and sources:
                        ai_response = f"📄 基于文档《{used_document.title}》回答：\n\n{ai_response}"
                    else:
                        logger.info(f"问题与文档内容无关，提供通用回答: {user_message}")
                else:
                    # 问题与文档无关，直接进行普通聊天（不传递document_id）
                    logger.info(f"智能判断：问题与文档无关，使用通用回答: {user_message}")
                    ai_result = rag_engine.handle_chat(query=user_message)  # 不传递document_id
                    ai_response = ai_result.get("answer", "抱歉，AI服务暂时不可用")
            else:
                # 无上下文的情况 - 普通聊天
                ai_result = rag_engine.handle_chat(query=user_message)
                ai_response = ai_result.get("answer", "抱歉，AI服务暂时不可用")

            # 保存到数据库，初始状态为处理中
            chat_session = ChatSession.objects.create(
                user_message=user_message,
                ai_response="",  # 初始为空
                is_ready=False  # 添加is_ready字段，初始为False
            )

            logger.info(f"开始处理用户消息: {user_message}")

            # 异步处理AI回复
            import threading
            def process_ai_response():
                try:
                    # 这里是AI处理逻辑（之前的代码）
                    final_ai_response = ai_response

                    # 更新数据库
                    chat_session.ai_response = final_ai_response
                    chat_session.is_ready = True
                    chat_session.save()

                    logger.info(f"AI回复生成完成: {final_ai_response[:100]}...")
                except Exception as e:
                    logger.error(f"AI处理失败: {e}")
                    chat_session.ai_response = f"抱歉，处理您的消息时出现错误: {str(e)}"
                    chat_session.is_ready = True
                    chat_session.save()

            # 启动后台线程处理
            thread = threading.Thread(target=process_ai_response)
            thread.daemon = True
            thread.start()

            return JsonResponse({
                'status': 'success',
                'message': '消息已接收，正在处理中',
                'session_id': chat_session.id,
                'is_ready': False,
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

    def _should_use_document_context(self, query: str) -> bool:
        """智能判断问题是否需要基于文档回答"""
        import re

        # 简单的数学表达式检测
        math_patterns = [
            r'^\s*\d+\s*[\+\-\*/]\s*\d+\s*$',  # 简单数学运算如 1+5
            r'^\s*\d+\s*([\+\-\*/]\s*\d+\s*)+$',  # 多项数学运算
            r'^\s*\(\s*\d+.*\)\s*$',  # 带括号的数学表达式
        ]

        for pattern in math_patterns:
            if re.match(pattern, query.strip()):
                logger.info(f"检测到数学表达式，不使用文档上下文: {query}")
                return False

        # 简单的问候语检测
        greetings = ['hi', 'hello', '你好', '您好', 'hey', '嗨', '哈喽', 'hi~']
        query_lower = query.lower().strip()
        if query_lower in greetings or any(greeting in query_lower for greeting in greetings):
            logger.info(f"检测到问候语，不使用文档上下文: {query}")
            return False

        # 检查是否是通用回复
        generic_queries = [
            '谢谢', 'thank you', '再见', 'bye', 'goodbye',
            '好的', 'ok', 'okay', '明白', '知道了', '没问题'
        ]

        if query_lower in generic_queries:
            logger.info(f"检测到通用回复，不使用文档上下文: {query}")
            return False

        # 如果查询很短且通用，可能不相关
        if len(query.strip()) < 3:
            logger.info(f"查询过短，不使用文档上下文: {query}")
            return False

        # 检测时间相关问题
        time_patterns = [
            r'现在.*时间', r'几点了', r'what time', r'当前时间'
        ]
        for pattern in time_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"检测到时间相关问题，不使用文档上下文: {query}")
                return False

        # 检测常见的通用问题
        general_patterns = [
            r'^\s*\d+\s*[等于=]\s*\d+\s*$',  # 等式
            r'天气', r'weather', r'今天.*怎么样',
            r'你是谁', r'who are you', r'你叫什么',
            r'你好吗', r'how are you', r'最近怎么样',
            r'现在几点', r'今天星期几', r'今天日期',
            r'帮我.*计算', r'算一下', r'计算.*结果'
        ]

        for pattern in general_patterns:
            if re.search(pattern, query_lower):
                logger.info(f"检测到通用问题，不使用文档上下文: {query}")
                return False

        # 默认认为需要使用文档上下文
        return True


@api_view(['GET'])
def chat_status(request, session_id):
    """检查聊天消息状态"""
    try:
        chat_session = ChatSession.objects.get(id=session_id)

        return Response({
            'session_id': session_id,
            'is_ready': chat_session.is_ready,
            'ai_response': chat_session.ai_response if chat_session.is_ready else '',
            'user_message': chat_session.user_message,
            'timestamp': chat_session.timestamp.isoformat()
        })

    except ChatSession.DoesNotExist:
        return Response({'error': '会话不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"获取聊天状态失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def chat_history(request):
    """获取聊天历史"""
    try:
        messages = ChatSession.objects.filter(is_ready=True)[:20]  # 只返回已完成的消息
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

                # 立即进行RAG处理和向量化
                try:
                    from ..ai_services import process_document_for_rag
                    rag_processing_result = process_document_for_rag(document.id, force_reprocess=True)

                    if rag_processing_result:
                        logger.info(f"聊天文档RAG处理成功: {filename}")
                    else:
                        logger.warning(f"聊天文档RAG处理失败: {filename}")

                except Exception as e:
                    logger.error(f"聊天文档RAG处理异常: {filename}, 错误: {e}")
                    # RAG处理失败不影响文档上传成功

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
