@echo off
chcp 65001
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1

echo 正在安装Django项目依赖...

echo 1. 安装核心Django依赖...
python -m pip install Django==4.2.23
python -m pip install djangorestframework==3.14.0
python -m pip install django-cors-headers==4.0.0

echo 2. 安装AI服务依赖...
python -m pip install google-generativeai==0.3.2

echo 3. 安装文件处理依赖...
python -m pip install PyPDF2==3.0.1
python -m pip install python-docx==1.1.0

echo 4. 安装数据处理依赖...
python -m pip install pandas==1.5.3
python -m pip install numpy==1.24.3

echo 5. 安装环境变量管理...
python -m pip install python-dotenv==1.0.0

echo 6. 安装工具库...
python -m pip install werkzeug==2.3.6

echo 7. 安装请求库...
python -m pip install requests==2.31.0

echo 依赖安装完成！
echo 测试Django安装...
python -c "import django; print('Django版本:', django.get_version())"

pause
