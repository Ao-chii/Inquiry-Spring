"""
URL configuration for InquirySpring Backend - 完全以前端为准
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from inquiryspring_backend.projects import auth as project_auth

def health_check(request):
    """健康检查接口"""
    return JsonResponse({
        'status': 'ok',
        'message': 'InquirySpring Backend is running',
        'version': '1.0.0'
    })

@csrf_exempt
def debug_403(request):
    """调试403错误的测试端点"""
    print(f"=== DEBUG 403 测试端点被调用 ===")
    print(f"Method: {request.method}")
    print(f"Path: {request.path}")
    print(f"User: {request.user}")
    print(f"User authenticated: {request.user.is_authenticated}")
    print(f"Headers: {dict(request.headers)}")
    print(f"=== DEBUG 403 结束 ===")

    return JsonResponse({
        'message': '403调试测试成功',
        'method': request.method,
        'path': request.path,
        'user': str(request.user),
        'authenticated': request.user.is_authenticated,
        'success': True
    })

# 完全匹配前端路由的URL配置
urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health'),

    # === 前端API端点 - 完全匹配前端路径 ===
    # 用户认证
    path('api/login/', project_auth.user_login, name='login'),
    path('api/register/', project_auth.user_register, name='register'),

    # 聊天功能 - 前端: /api/chat/
    path('api/chat/', include('inquiryspring_backend.chat.urls')),

    # 文档上传 - 前端: /api/fileUpload/
    path('api/fileUpload/', include('inquiryspring_backend.documents.urls')),

    # 文档总结 - 前端: /api/summarize/
    path('api/summarize/', include('inquiryspring_backend.documents.urls')),

    # 测验功能 - 前端: /api/test/
    path('api/test/', include('inquiryspring_backend.quiz.urls')),

    # 项目管理 - 前端: /api/projects/ (必须放在最后，避免冲突)
    path('api/projects/', include('inquiryspring_backend.projects.urls')),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
