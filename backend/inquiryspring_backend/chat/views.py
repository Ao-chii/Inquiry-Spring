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
from ..documents.models import Document
from ..projects.models import Project, ProjectDocument

logger = logging.getLogger(__name__)


@method_decorator(csrf_exempt, name='dispatch')
class ChatView(View):
    """聊天视图 - 兼容前端的POST和GET请求"""
    
    def post(self, request):
        """处理用户消息 - 重构后完全信任RAGEngine的设计"""
        try:
            data = json.loads(request.body)
            user_message = data.get('message', '').strip()
            selected_document_id = data.get('document_id')
            conversation_id = data.get('conversation_id')
            username = data.get('username', '')

            if not user_message:
                return JsonResponse({'error': '消息不能为空'}, status=400)

            logger.info(f"收到用户消息: {user_message}")
            if selected_document_id:
                logger.info(f"用户选择的文档ID: {selected_document_id}")
            if conversation_id:
                logger.info(f"对话ID: {conversation_id}")

            # 获取或创建对话
            conversation = self._get_or_create_conversation(conversation_id, username, user_message)

            # 保存用户消息
            user_msg = Message.objects.create(
                conversation=conversation,
                content=user_message,
                is_user=True,
                document_id=selected_document_id
            )

            # 确定文档上下文策略
            document_to_use = self._determine_document_context(selected_document_id)

            # 直接使用RAGEngine处理 - 信任其内置的智能判断
            try:
                if document_to_use:
                    # 有文档上下文 - 让RAGEngine自己决定是否使用
                    ai_result = RAGEngine(document_id=document_to_use.id).handle_chat(
                        query=user_message,
                        document_id=document_to_use.id
                    )
                    used_document_info = {
                        'id': document_to_use.id,
                        'title': document_to_use.title
                    }
                else:
                    # 无文档上下文 - 纯聊天模式
                    ai_result = RAGEngine().handle_chat(query=user_message)
                    used_document_info = None

                ai_response = ai_result.get("answer", "抱歉，AI服务暂时不可用")
                sources = ai_result.get("sources", [])
                is_generic_answer = ai_result.get("is_generic_answer", False)

                # 保存AI回复
                ai_msg = Message.objects.create(
                    conversation=conversation,
                    content=ai_response,
                    is_user=False,
                    document_id=selected_document_id,
                    document_title=document_to_use.title if document_to_use else ''
                )

                # 更新对话
                conversation.update_message_count()

                logger.info(f"AI回复生成完成，使用文档: {document_to_use.title if document_to_use else '无'}")

            except Exception as e:
                logger.error(f"RAGEngine处理失败: {e}")
                error_msg = f"抱歉，处理您的消息时出现错误: {str(e)}"

                # 保存错误消息
                ai_msg = Message.objects.create(
                    conversation=conversation,
                    content=error_msg,
                    is_user=False,
                    document_id=selected_document_id,
                    document_title=document_to_use.title if document_to_use else ''
                )
                conversation.update_message_count()

                ai_response = error_msg
                sources = []
                is_generic_answer = True
                used_document_info = None

            # 保存到数据库（兼容旧版本）
            chat_session = ChatSession.objects.create(
                user_message=user_message,
                ai_response=ai_response,
                is_ready=True  # 同步处理，立即完成
            )

            return JsonResponse({
                'status': 'success',
                'message': '处理完成',
                'session_id': chat_session.id,
                'conversation_id': conversation.id,
                'is_ready': True,
                'ai_response': ai_response,
                'has_context': bool(document_to_use),
                'used_document': used_document_info['title'] if used_document_info else None,
                'sources': sources
            })
            
        except Exception as e:
            logger.error(f"聊天处理失败: {e}")
            return JsonResponse({
                'status': 'error',
                'error': f'处理失败: {str(e)}'
            }, status=500)

    def _get_or_create_conversation(self, conversation_id: str, username: str, user_message: str):
        """获取或创建对话"""
        conversation = None
        if conversation_id:
            try:
                from .models import Conversation
                conversation = Conversation.objects.get(id=conversation_id)
            except Conversation.DoesNotExist:
                logger.warning(f"对话不存在: {conversation_id}")

        # 如果没有对话，创建新对话
        if not conversation:
            from .models import Conversation
            # 使用用户第一次输入的前30个字符作为对话标题
            title = user_message[:30] + ('...' if len(user_message) > 30 else '')
            conversation = Conversation.objects.create(
                username=username,
                title=title,
                message_count=0
            )
            logger.info(f"创建新对话: {conversation.id}, 标题: {title}")

        return conversation

    def _determine_document_context(self, selected_document_id: int):
        """确定要使用的文档上下文 - 简化逻辑，信任用户选择"""
        if selected_document_id:
            try:
                document = Document.objects.get(
                    id=selected_document_id,
                    is_processed=True
                )
                logger.info(f"使用用户选择的文档: {document.title}")
                return document
            except Document.DoesNotExist:
                logger.warning(f"用户选择的文档不存在或未处理: {selected_document_id}")

        # 如果没有选择文档，返回None，让RAGEngine处理纯聊天
        return None

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


# 删除了聊天反馈功能


# 删除了ChatDocumentUploadView - 现在使用项目管理的文档上传功能


@api_view(['GET'])
def chat_documents(request):
    """获取聊天中可用的文档列表 - 从项目管理数据库获取"""
    try:
        # 获取用户名参数
        username = request.GET.get('username', '')

        if username:
            # 如果提供了用户名，获取该用户的项目文档
            from django.contrib.auth.models import User
            try:
                user = User.objects.get(username=username)
                # 获取用户项目中的所有文档
                project_documents = ProjectDocument.objects.filter(
                    project__user=user,
                    project__is_active=True,
                    document__is_processed=True
                ).select_related('document').order_by('-document__uploaded_at')[:20]

                documents = [pd.document for pd in project_documents]
            except User.DoesNotExist:
                documents = []
        else:
            # 如果没有用户名，获取所有已处理的文档
            documents = Document.objects.filter(
                is_processed=True
            ).order_by('-uploaded_at')[:20]

        doc_list = []
        for doc in documents:
            doc_list.append({
                'id': doc.id,
                'title': doc.title,
                'filename': doc.filename if hasattr(doc, 'filename') and doc.filename else doc.title,
                'file_type': doc.file_type,
                'file_size': doc.file_size,
                'content_length': len(doc.content) if doc.content else 0,
                'uploaded_at': doc.uploaded_at.isoformat(),
                'processed_at': doc.processed_at.isoformat() if doc.processed_at else None
            })

        return Response({
            'documents': doc_list,
            'count': len(doc_list)
        })

    except Exception as e:
        logger.error(f"获取聊天文档列表失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def delete_document(request, document_id):
    """删除文档 - 兼容chat界面的文档删除功能"""
    try:
        document = Document.objects.get(id=document_id)
        document_title = document.title

        # 删除项目文档关联
        ProjectDocument.objects.filter(document=document).delete()

        # 删除文档本身
        document.delete()

        logger.info(f"文档删除成功: {document_title}")

        return Response({
            'message': f'文档 "{document_title}" 删除成功',
            'deleted_document_id': document_id
        })

    except Document.DoesNotExist:
        return Response({'error': '文档不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"删除文档失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'POST'])
def conversation_list(request):
    """对话列表API"""
    if request.method == 'GET':
        try:
            username = request.GET.get('username', '')
            conversations = Conversation.objects.filter(
                username=username,
                is_active=True
            ).order_by('-updated_at')[:20]

            conv_list = []
            for conv in conversations:
                conv_list.append({
                    'id': conv.id,
                    'title': conv.title,
                    'message_count': conv.message_count,
                    'created_at': conv.created_at.isoformat(),
                    'updated_at': conv.updated_at.isoformat()
                })

            return Response({'conversations': conv_list})

        except Exception as e:
            logger.error(f"获取对话列表失败: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    elif request.method == 'POST':
        try:
            data = request.data
            username = data.get('username', '')
            title = data.get('title', '新对话')

            conversation = Conversation.objects.create(
                username=username,
                title=title,
                message_count=0
            )

            return Response({
                'conversation': {
                    'id': conversation.id,
                    'title': conversation.title,
                    'message_count': conversation.message_count,
                    'created_at': conversation.created_at.isoformat(),
                    'updated_at': conversation.updated_at.isoformat()
                }
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"创建对话失败: {e}")
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET', 'DELETE'])
def conversation_detail(request, conversation_id):
    """对话详情API"""
    try:
        conversation = Conversation.objects.get(id=conversation_id)

        if request.method == 'GET':
            messages = conversation.messages.all().order_by('created_at')
            message_list = []
            for msg in messages:
                message_list.append({
                    'id': msg.id,
                    'content': msg.content,
                    'is_user': msg.is_user,
                    'document_id': msg.document_id,
                    'document_title': msg.document_title,
                    'created_at': msg.created_at.isoformat()
                })

            return Response({
                'conversation': {
                    'id': conversation.id,
                    'title': conversation.title,
                    'message_count': conversation.message_count,
                    'created_at': conversation.created_at.isoformat(),
                    'updated_at': conversation.updated_at.isoformat()
                },
                'messages': message_list
            })

        elif request.method == 'DELETE':
            conversation.delete()
            return Response({'message': '对话删除成功'})

    except Conversation.DoesNotExist:
        return Response({'error': '对话不存在'}, status=status.HTTP_404_NOT_FOUND)
    except Exception as e:
        logger.error(f"对话详情操作失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['DELETE'])
def clear_conversations(request):
    """清空对话历史"""
    try:
        data = request.data
        username = data.get('username', '')

        deleted_count = Conversation.objects.filter(username=username).count()
        Conversation.objects.filter(username=username).delete()

        return Response({
            'message': '对话历史清空成功',
            'deleted_count': deleted_count
        })

    except Exception as e:
        logger.error(f"清空对话历史失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
def chat_history(request):
    """获取聊天历史"""
    try:
        username = request.GET.get('username', '')
        limit = int(request.GET.get('limit', 50))

        # 获取最近的聊天会话
        sessions = ChatSession.objects.filter(
            is_ready=True
        ).order_by('-id')[:limit]  # 使用id排序，因为created_at字段可能为空

        history_list = []
        for session in sessions:
            history_list.append({
                'id': session.id,
                'user_message': session.user_message,
                'ai_response': session.ai_response,
                'created_at': session.created_at.isoformat() if hasattr(session, 'created_at') and session.created_at else None,
                'is_ready': session.is_ready
            })

        return Response({
            'history': history_list,
            'count': len(history_list)
        })

    except Exception as e:
        logger.error(f"获取聊天历史失败: {e}")
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
