from django.urls import path
from . import views

app_name = 'quiz'

urlpatterns = [
    # 测验生成 - 兼容前端
    path('', views.TestGenerationView.as_view(), name='test_generation'),
    path('generate/', views.TestGenerationView.as_view(), name='test_generation_alt'),
    
    # API接口
    path('submit/', views.quiz_submit, name='quiz_submit'),
    path('history/', views.quiz_history, name='quiz_history'),
    path('analysis/<int:attempt_id>/', views.quiz_analysis, name='quiz_analysis'),
]
