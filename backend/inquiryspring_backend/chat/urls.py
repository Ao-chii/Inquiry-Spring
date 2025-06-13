from django.urls import path
from . import views

app_name = 'chat'

urlpatterns = [
    # 主聊天接口 - 兼容前端
    path('', views.ChatView.as_view(), name='chat'),

    # 文档上传接口
    path('upload/', views.ChatDocumentUploadView.as_view(), name='chat_upload'),
    path('documents/', views.chat_documents, name='chat_documents'),

    # API接口
    path('history/', views.chat_history, name='chat_history'),
    # 删除了反馈功能路由
]
