"""
Django管理命令：调试403错误
用法: python manage.py debug_403
"""

from django.core.management.base import BaseCommand
from django.test import Client
from django.urls import reverse, resolve
from django.conf import settings
import json

class Command(BaseCommand):
    help = '调试项目文档上传的403错误'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('🔍 开始403错误调试'))
        
        # 创建测试客户端
        client = Client()
        
        # 1. 测试URL解析
        self.test_url_resolution()
        
        # 2. 测试基本路由
        self.test_basic_routes(client)
        
        # 3. 测试项目路由
        self.test_project_routes(client)
        
        # 4. 测试中间件
        self.test_middleware_settings()
        
        self.stdout.write(self.style.SUCCESS('🔍 调试完成'))

    def test_url_resolution(self):
        """测试URL解析"""
        self.stdout.write('\n📋 测试URL解析:')
        
        test_urls = [
            '/api/projects/test/',
            '/api/projects/1/documents/',
            '/api/projects/1749890204035/documents/',
        ]
        
        for url in test_urls:
            try:
                resolver_match = resolve(url)
                self.stdout.write(f"✅ {url} → {resolver_match.view_name}")
                self.stdout.write(f"   视图函数: {resolver_match.func}")
                self.stdout.write(f"   参数: {resolver_match.kwargs}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ {url} → 解析失败: {e}"))

    def test_basic_routes(self, client):
        """测试基本路由"""
        self.stdout.write('\n📋 测试基本路由:')
        
        # 健康检查
        response = client.get('/health/')
        self.stdout.write(f"GET /health/ → {response.status_code}")
        
        # API根路径
        response = client.get('/api/')
        self.stdout.write(f"GET /api/ → {response.status_code}")

    def test_project_routes(self, client):
        """测试项目路由"""
        self.stdout.write('\n📋 测试项目路由:')
        
        test_cases = [
            ('GET', '/api/projects/'),
            ('GET', '/api/projects/test/'),
            ('GET', '/api/projects/1/'),
            ('GET', '/api/projects/1/documents/'),
            ('POST', '/api/projects/1/documents/'),
            ('OPTIONS', '/api/projects/1/documents/'),
        ]
        
        for method, url in test_cases:
            try:
                if method == 'GET':
                    response = client.get(url)
                elif method == 'POST':
                    response = client.post(url, {})
                elif method == 'OPTIONS':
                    response = client.options(url)
                
                status_icon = "✅" if response.status_code != 403 else "❌"
                self.stdout.write(f"{status_icon} {method} {url} → {response.status_code}")
                
                if response.status_code == 403:
                    self.stdout.write(f"   响应内容: {response.content.decode()}")
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"❌ {method} {url} → 异常: {e}"))

    def test_middleware_settings(self):
        """测试中间件设置"""
        self.stdout.write('\n📋 中间件配置:')
        
        for i, middleware in enumerate(settings.MIDDLEWARE):
            self.stdout.write(f"{i+1}. {middleware}")
        
        self.stdout.write('\n📋 REST Framework配置:')
        rest_config = getattr(settings, 'REST_FRAMEWORK', {})
        for key, value in rest_config.items():
            self.stdout.write(f"{key}: {value}")
        
        self.stdout.write('\n📋 CORS配置:')
        cors_settings = [
            'CORS_ALLOW_ALL_ORIGINS',
            'CORS_ALLOWED_ORIGINS', 
            'CORS_ALLOW_CREDENTIALS',
            'CORS_ALLOW_HEADERS',
            'CORS_ALLOW_METHODS',
        ]
        
        for setting in cors_settings:
            value = getattr(settings, setting, 'Not Set')
            self.stdout.write(f"{setting}: {value}")
