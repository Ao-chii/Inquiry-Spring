from django.urls import path
from . import views

# 简化的测验URL配置 - 完全按前端需求
urlpatterns = [
    # 前端使用 /api/test/ - 测验生成
    path('', views.TestGenerationView.as_view(), name='test_generation'),
]
