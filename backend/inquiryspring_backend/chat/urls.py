from django.urls import path
from . import views

# 简化的聊天URL配置 - 完全按前端需求
urlpatterns = [
    # 主聊天接口 - 前端使用 /api/chat/
    path('', views.ChatView.as_view(), name='chat'),

    # 文档上传 - 前端使用 /api/chat/upload/
    path('upload/', views.ChatDocumentUploadView.as_view(), name='chat_upload'),

    # 状态检查 - 前端使用 /api/chat/status/{id}/
    path('status/<int:session_id>/', views.chat_status, name='chat_status'),
]
