#!/usr/bin/env python
"""
InquirySpring Backend 初始化脚本
"""
import django
from django.core.management import execute_from_command_line

def main():
    """初始化Django后端"""
    print("🔧 初始化InquirySpring Django后端...")

    # 设置Django设置模块
    import os
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'inquiryspring_backend.settings')
    
    try:
        django.setup()
        print("✅ Django配置加载成功")
        
        # 创建迁移文件
        print("📝 创建数据库迁移文件...")
        execute_from_command_line(['manage.py', 'makemigrations'])
        
        # 应用迁移
        print("🗄️  应用数据库迁移...")
        execute_from_command_line(['manage.py', 'migrate'])
        
        # 检查是否需要创建超级用户
        from django.contrib.auth.models import User
        if not User.objects.filter(is_superuser=True).exists():
            print("👤 创建管理员用户...")
            print("请按提示输入管理员信息：")
            execute_from_command_line(['manage.py', 'createsuperuser'])
        else:
            print("✅ 管理员用户已存在")
        
        # 检查AI服务
        try:
            from inquiryspring_backend.ai_services.llm_client import LLMClientFactory
            import os

            # 检查API密钥配置
            api_key = os.getenv('GOOGLE_API_KEY')
            if api_key:
                print("🤖 AI服务状态: 已配置")
                print("✅ Google API密钥已设置")

                # 尝试创建LLM客户端并测试连接
                try:
                    llm_client = LLMClientFactory.create_client()
                    test_response = llm_client.generate_text("测试连接", max_tokens=10)
                    if test_response and test_response.get('text'):
                        print("✅ AI服务连接正常")
                        print(f"✅ 测试响应: {test_response.get('text', '')[:50]}...")
                    else:
                        print("⚠️  AI服务连接可能有问题")
                except Exception as test_e:
                    print(f"⚠️  AI服务测试失败: {test_e}")
            else:
                print("❌ AI服务状态: 未配置")
                print("💡 提示: 在.env文件中设置GOOGLE_API_KEY以启用AI功能")
                print("⚠️  警告: 没有API密钥，AI功能将不可用")

        except Exception as e:
            print(f"⚠️  AI服务检查失败: {e}")
            print("💡 提示: 确保ai_services模块正确安装")
        
        print("=" * 50)
        print("✅ 后端初始化完成！")
        print("🚀 运行 'python run_backend.py' 启动服务器")
        print("📚 访问 http://localhost:8000/admin 进入管理后台")
        print("🔗 访问 http://localhost:8000/health 检查服务状态")
        
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc

if __name__ == '__main__':
    main()
