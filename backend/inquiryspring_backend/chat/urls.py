from django.urls import path
from . import views

# 完整的聊天URL配置 - 匹配前端需求
urlpatterns = [
    # 主聊天接口 - 前端使用 /api/chat/
    path('', views.ChatView.as_view(), name='chat'),

    # 文档上传 - 前端使用 /api/chat/upload/
    path('upload/', views.ChatDocumentUploadView.as_view(), name='chat_upload'),

    # 状态检查 - 前端使用 /api/chat/status/{id}/
    path('status/<int:session_id>/', views.chat_status, name='chat_status'),

    # 文档列表 - 前端使用 /api/chat/documents/
    path('documents/', views.chat_documents, name='chat_documents'),

    # 文档删除 - 前端使用 /api/chat/documents/{id}/delete/
    path('documents/<int:document_id>/delete/', views.delete_document, name='delete_document'),

    # 对话管理 - 前端使用 /api/chat/conversations/
    path('conversations/', views.conversation_list, name='conversation_list'),
    path('conversations/<int:conversation_id>/', views.conversation_detail, name='conversation_detail'),
    path('conversations/clear/', views.clear_conversations, name='clear_conversations'),

    # 聊天历史 - 前端使用 /api/chat/history/
    path('history/', views.chat_history, name='chat_history'),
]
