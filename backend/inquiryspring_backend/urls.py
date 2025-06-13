"""
URL configuration for InquirySpring Backend.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from inquiryspring_backend.documents import views as doc_views
from inquiryspring_backend.projects import auth as project_auth

def health_check(request):
    """健康检查接口"""
    return JsonResponse({
        'status': 'ok',
        'message': 'InquirySpring Backend is running',
        'version': '1.0.0'
    })

urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),
    
    # 用户认证API
    path('api/login/', project_auth.user_login, name='api_login'),
    path('api/register/', project_auth.user_register, name='api_register'),
    
    # API endpoints for Vue.js frontend
    path('api/chat/', include('inquiryspring_backend.chat.urls', namespace='api_chat')),
    path('api/documents/', include('inquiryspring_backend.documents.urls', namespace='api_documents')),
    path('api/quiz/', include('inquiryspring_backend.quiz.urls', namespace='api_quiz')),
    path('api/projects/', include('inquiryspring_backend.projects.urls', namespace='api_projects')),

    # 前端期望的特定API端点
    path('api/summarize/', include('inquiryspring_backend.documents.urls', namespace='api_summarize')),
    path('api/test/', include('inquiryspring_backend.quiz.urls', namespace='api_test')),

    # Legacy endpoints for frontend compatibility
    path('chat/', include('inquiryspring_backend.chat.urls', namespace='legacy_chat')),
    path('fileUpload/', include('inquiryspring_backend.documents.urls', namespace='legacy_upload')),
    path('summarize/', include('inquiryspring_backend.documents.urls', namespace='legacy_summarize')),
    path('test/', include('inquiryspring_backend.quiz.urls', namespace='legacy_quiz')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
