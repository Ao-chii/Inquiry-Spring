from django.urls import path
from . import views

app_name = 'documents'

urlpatterns = [
    # 文档管理API - 使用新的Document模型（放在前面避免冲突）
    path('list/', views.document_list, name='document_list'),
    path('<int:doc_id>/delete/', views.document_delete, name='document_delete'),
    path('<int:doc_id>/content/', views.document_content, name='document_content'),
    path('<int:doc_id>/summarize/', views.document_summarize, name='document_summarize_new'),
    path('<int:doc_id>/status/', views.document_status, name='document_status'),
    path('formats/', views.document_formats, name='document_formats'),

    # 文档处理API - 统一使用SummarizeView
    path('process/', views.SummarizeView.as_view(), name='document_process'),
    path('upload/', views.SummarizeView.as_view(), name='file_upload'),
    path('fileUpload/', views.SummarizeView.as_view(), name='file_upload_alt'),

    # 文档总结 - 兼容前端
    path('summarize/', views.SummarizeView.as_view(), name='summarize'),

    # 文档总结 - 兼容前端 (根路径用于/api/summarize/，放在最后避免冲突)
    path('', views.SummarizeView.as_view(), name='summarize_root'),
]
