#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Django项目依赖安装脚本
解决Windows中文编码问题
"""

import subprocess
import sys
import os

# 设置编码
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['PYTHONUTF8'] = '1'

def install_package(package):
    """安装单个包"""
    try:
        print(f"正在安装 {package}...")
        result = subprocess.run([
            sys.executable, '-m', 'pip', 'install', package
        ], capture_output=True, text=True, encoding='utf-8')
        
        if result.returncode == 0:
            print(f"✅ {package} 安装成功")
            return True
        else:
            print(f"❌ {package} 安装失败: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ {package} 安装异常: {e}")
        return False

def main():
    """主安装函数"""
    print("🔧 开始安装Django项目依赖...")
    
    # 核心依赖列表
    packages = [
        'Django==4.2.23',
        'djangorestframework==3.14.0', 
        'django-cors-headers==4.0.0',
        'python-dotenv==1.0.0',
        'requests==2.31.0',
        'PyPDF2==3.0.1',
        'python-docx==1.1.0',
        'google-generativeai==0.3.2',
        'pandas==1.5.3',
        'numpy==1.24.3',
        'werkzeug==2.3.6',
    ]
    
    # 安装包
    success_count = 0
    for package in packages:
        if install_package(package):
            success_count += 1
    
    print(f"\n📊 安装结果: {success_count}/{len(packages)} 个包安装成功")
    
    # 测试Django
    try:
        import django
        print(f"✅ Django安装成功，版本: {django.get_version()}")
    except ImportError:
        print("❌ Django安装失败")
    
    # 测试其他关键包
    test_packages = ['rest_framework', 'corsheaders', 'dotenv']
    for pkg in test_packages:
        try:
            __import__(pkg)
            print(f"✅ {pkg} 可用")
        except ImportError:
            print(f"❌ {pkg} 不可用")

if __name__ == '__main__':
    main()
