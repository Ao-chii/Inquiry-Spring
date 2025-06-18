from django.urls import path
from . import views

# 简化的文档URL配置 - 完全按前端需求
urlpatterns = [
    # 前端使用的主要端点
    # /api/fileUpload/ - 文件上传和总结
    path('', views.SummarizeView.as_view(), name='file_upload'),

    # 智慧总结页面需要的API
    path('uploaded-files/', views.get_uploaded_files, name='uploaded_files'),

    # /api/summarize/ - 文档总结
    # 这个路径会被主URL配置处理
]
