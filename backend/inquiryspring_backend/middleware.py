"""
InquirySpring Backend 中间件
"""
import json
import logging
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger(__name__)


class APIResponseMiddleware(MiddlewareMixin):
    """API响应格式化中间件"""

    # 不需要包装的API端点 (前端期望特定格式)
    SKIP_WRAPPING_PATHS = [
        '/api/summarize/',
        '/api/chat/',
        '/api/test/',
        '/api/login/',
        '/api/register/',
    ]

    def process_response(self, request, response):
        """处理响应"""
        # 只处理API请求
        if not request.path.startswith('/api/'):
            return response

        # 检查是否需要跳过包装
        for skip_path in self.SKIP_WRAPPING_PATHS:
            if request.path.startswith(skip_path):
                return response

        # 只处理JSON响应
        if not response.get('Content-Type', '').startswith('application/json'):
            return response

        try:
            # 解析响应内容
            if hasattr(response, 'data'):
                # DRF响应
                data = response.data
            else:
                # Django JsonResponse
                data = json.loads(response.content.decode('utf-8'))

            # 如果已经是标准格式，直接返回
            if isinstance(data, dict) and 'status' in data:
                return response

            # 格式化响应
            formatted_data = {
                'status': 'success' if 200 <= response.status_code < 300 else 'error',
                'data': data,
                'timestamp': self._get_timestamp()
            }

            # 创建新的响应
            new_response = JsonResponse(formatted_data, status=response.status_code)
            return new_response

        except Exception as e:
            logger.error(f"响应格式化失败: {e}")
            return response
    
    def _get_timestamp(self):
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()


class RequestLoggingMiddleware(MiddlewareMixin):
    """请求日志中间件"""
    
    def process_request(self, request):
        """记录请求信息"""
        if request.path.startswith('/api/'):
            logger.info(f"API请求: {request.method} {request.path}")
            
            # 记录POST数据（敏感信息除外）
            if request.method == 'POST' and request.content_type == 'application/json':
                try:
                    data = json.loads(request.body.decode('utf-8'))
                    # 过滤敏感信息
                    filtered_data = self._filter_sensitive_data(data)
                    logger.debug(f"请求数据: {filtered_data}")
                except:
                    pass
        
        return None
    
    def process_response(self, request, response):
        """记录响应信息"""
        if request.path.startswith('/api/'):
            logger.info(f"API响应: {request.method} {request.path} - {response.status_code}")
        
        return response
    
    def _filter_sensitive_data(self, data):
        """过滤敏感数据"""
        if not isinstance(data, dict):
            return data
        
        sensitive_keys = ['password', 'token', 'api_key', 'secret']
        filtered = {}
        
        for key, value in data.items():
            if any(sensitive_key in key.lower() for sensitive_key in sensitive_keys):
                filtered[key] = '***'
            else:
                filtered[key] = value
        
        return filtered


class CORSMiddleware(MiddlewareMixin):
    """CORS中间件（补充django-cors-headers）"""
    
    def process_response(self, request, response):
        """添加CORS头"""
        # 添加额外的CORS头
        response['Access-Control-Allow-Credentials'] = 'true'
        response['Access-Control-Max-Age'] = '86400'
        
        return response


class DisableCSRFMiddleware(MiddlewareMixin):
    """开发阶段禁用CSRF检查的中间件"""

    def process_request(self, request):
        """禁用CSRF检查"""
        if request.path.startswith('/api/'):
            setattr(request, '_dont_enforce_csrf_checks', True)
        return None


class DebugMiddleware(MiddlewareMixin):
    """调试中间件 - 追踪403错误"""

    def process_request(self, request):
        """处理请求 - 记录详细信息"""
        if request.path.startswith('/api/projects/'):
            print(f"=== DEBUG中间件 - 请求开始 ===")
            print(f"Path: {request.path}")
            print(f"Method: {request.method}")
            print(f"User: {getattr(request, 'user', 'Not available yet')}")
            print(f"User authenticated: {getattr(getattr(request, 'user', None), 'is_authenticated', False)}")
            print(f"Headers: {dict(request.headers)}")
            print(f"Content-Type: {request.content_type}")
            print(f"CSRF disabled: {getattr(request, '_dont_enforce_csrf_checks', False)}")
            print(f"=== DEBUG中间件 - 请求信息结束 ===")
        return None

    def process_response(self, request, response):
        """处理响应 - 记录403错误"""
        if request.path.startswith('/api/projects/') and response.status_code == 403:
            print(f"=== DEBUG中间件 - 403错误 ===")
            print(f"Path: {request.path}")
            print(f"Status: {response.status_code}")
            print(f"Response content: {response.content}")
            print(f"Response headers: {dict(response.items())}")
            print(f"=== DEBUG中间件 - 403错误结束 ===")
        return response


class ErrorHandlingMiddleware(MiddlewareMixin):
    """错误处理中间件"""

    def process_exception(self, request, exception):
        """处理未捕获的异常"""
        if request.path.startswith('/api/'):
            logger.error(f"API异常: {request.path} - {str(exception)}", exc_info=True)

            # 返回标准错误响应
            error_response = {
                'status': 'error',
                'message': '服务器内部错误',
                'error': str(exception) if logger.level <= logging.DEBUG else None,
                'timestamp': self._get_timestamp()
            }

            return JsonResponse(error_response, status=500)

        return None

    def _get_timestamp(self):
        """获取当前时间戳"""
        from datetime import datetime
        return datetime.now().isoformat()
