from django.urls import path
from . import views

# 完全匹配前端项目管理路由的URL配置
urlpatterns = [
    # 简单测试路由 - 绕过所有DRF限制
    path('simple-test/', views.simple_test_view, name='simple_test'),

    # 测试路由 - 确保基本路由工作
    path('test/', views.test_route, name='test_route'),

    # 项目文档上传 - 前端: /api/projects/{id}/documents/
    # 使用str类型避免整数范围限制
    path('<str:project_id>/documents/', views.project_upload_document, name='project_upload_document'),

    # 项目详情 - 前端可能需要
    path('<str:project_id>/', views.project_detail, name='project_detail'),

    # 项目列表和创建 - 前端使用 /api/projects/ (放在最后避免冲突)
    path('', views.project_list, name='project_list'),
]
