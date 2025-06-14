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
    path('<int:project_id>/upload-document/', views.project_upload_document, name='project_upload_document'),

    # 项目AI功能
    path('<int:project_id>/generate-summary/', views.generate_project_summary, name='generate_project_summary'),
    path('<int:project_id>/generate-quiz/', views.generate_project_quiz, name='generate_project_quiz'),
]
