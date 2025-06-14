from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

@csrf_exempt
def user_login(request):
    """处理用户登录请求"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return JsonResponse({
                    'success': False,
                    'message': '用户名和密码不能为空'
                })
            
            user = authenticate(username=username, password=password)
            
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': '登录成功'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': '用户名或密码错误'
                })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'message': '不支持的请求方法'
    })

@csrf_exempt
def user_register(request):
    """处理用户注册请求"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')
            
            if not username or not password:
                return JsonResponse({
                    'success': False,
                    'message': '用户名和密码不能为空'
                })
            
            # 检查用户名是否已存在
            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'message': '用户名已存在'
                })
            
            # 创建新用户
            user = User.objects.create_user(
                username=username,
                password=password
            )
            
            return JsonResponse({
                'success': True,
                'message': '注册成功'
            })
                
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            })
    
    return JsonResponse({
        'success': False,
        'message': '不支持的请求方法'
    }) 