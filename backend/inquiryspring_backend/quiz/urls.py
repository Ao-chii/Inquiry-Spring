from django.urls import path
from . import views

# 测验功能URL配置 - 基于ai_services路线
urlpatterns = [
    # 主要测验生成API - 支持文档上传和标准生成
    path('', views.TestGenerationView.as_view(), name='test_generation'),

    # 测验提交
    path('submit/', views.quiz_submit, name='quiz_submit'),

    # 答案评判
    path('evaluate/', views.evaluate_answers, name='evaluate_answers'),

    # 测验历史
    path('history/', views.quiz_history, name='quiz_history'),

    # 测验分析
    path('analysis/<int:attempt_id>/', views.quiz_analysis, name='quiz_analysis'),

    # 可用文档列表
    path('documents/', views.available_documents, name='available_documents'),
]
