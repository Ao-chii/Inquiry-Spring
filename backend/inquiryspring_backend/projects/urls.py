from django.urls import path
from . import views

app_name = 'projects'

urlpatterns = [
    # 项目列表
    path('', views.project_list, name='project_list'),
    
    # 项目详情
    path('<int:project_id>/', views.project_detail, name='project_detail'),
    
    # 项目文档管理
    path('<int:project_id>/documents/', views.project_add_document, name='project_add_document'),
]
