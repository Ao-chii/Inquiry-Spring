"""
Django settings for InquirySpring Backend.
"""

import os
import warnings
from pathlib import Path
from dotenv import load_dotenv

# 过滤LangChain和Pydantic兼容性警告
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*langchain_core.pydantic_v1.*")
warnings.filterwarnings("ignore", message=".*Mixing V1 models and V2 models.*")
warnings.filterwarnings("ignore", message=".*Valid config keys have changed in V2.*")

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
load_dotenv(BASE_DIR / '.env')

# 设置Hugging Face相关环境变量
if os.getenv('USE_PROXY', 'false').lower() == 'true':
    proxy_url = os.getenv('PROXY_URL', 'http://127.0.0.1:7890')
    os.environ['HTTP_PROXY'] = proxy_url
    os.environ['HTTPS_PROXY'] = proxy_url

# 设置Hugging Face Hub配置
os.environ['HF_ENDPOINT'] = os.getenv('HF_ENDPOINT', 'https://huggingface.co')
os.environ['TRANSFORMERS_OFFLINE'] = os.getenv('TRANSFORMERS_OFFLINE', '0')
os.environ['HF_HUB_OFFLINE'] = os.getenv('HF_HUB_OFFLINE', '0')

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-inquiry-spring-secret-key-change-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv('DEBUG', 'True').lower() in ('true', '1', 'yes')

ALLOWED_HOSTS = ['*']

# Application definition
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'corsheaders',
    'rest_framework',
    
    # Local apps
    'inquiryspring_backend.chat',
    'inquiryspring_backend.documents',
    'inquiryspring_backend.quiz',
    'inquiryspring_backend.projects',
    'inquiryspring_backend.ai_services',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'inquiryspring_backend.middleware.DisableCSRFMiddleware',  # 禁用CSRF检查
    'inquiryspring_backend.middleware.DebugMiddleware',  # 调试中间件
    'inquiryspring_backend.middleware.RequestLoggingMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    # 'django.middleware.csrf.CsrfViewMiddleware',  # 已禁用
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'inquiryspring_backend.middleware.APIResponseMiddleware',
    'inquiryspring_backend.middleware.ErrorHandlingMiddleware',
]

ROOT_URLCONF = 'inquiryspring_backend.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'inquiryspring_backend.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'inquiryspring_backend' / 'db.sqlite3',
    }
}

# Password validation
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'zh-hans'
TIME_ZONE = 'Asia/Shanghai'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# CORS settings for Vue.js frontend - 完全匹配前端配置
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5000",
    "http://127.0.0.1:5000",
    "http://0.0.0.0:5000",  # 前端配置的host
]

CORS_ALLOW_ALL_ORIGINS = True  # 开发阶段允许所有来源
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = ['*']
CORS_ALLOW_METHODS = ['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS']
CORS_PREFLIGHT_MAX_AGE = 86400

# 开发阶段完全禁用CSRF保护
CSRF_COOKIE_SECURE = False
CSRF_USE_SESSIONS = False
CSRF_TRUSTED_ORIGINS = [
    'http://localhost:5000',
    'http://127.0.0.1:5000',
    'http://0.0.0.0:5000',
    'http://localhost:8000',
    'http://127.0.0.1:8000',
]
CSRF_FAILURE_VIEW = 'django.views.csrf.csrf_failure'

# REST Framework settings
REST_FRAMEWORK = {
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.AllowAny',
    ],
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20
}

# File upload settings
FILE_UPLOAD_MAX_MEMORY_SIZE = 16 * 1024 * 1024  # 16MB
DATA_UPLOAD_MAX_MEMORY_SIZE = 16 * 1024 * 1024  # 16MB

# Logging
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'root': {
        'handlers': ['console'],
        'level': 'INFO',
    },
    'loggers': {
        'django': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'inquiryspring-backend': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'inquiryspring_backend.ai_services': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
    },
}

# AI Services Configuration
AI_SERVICES = {
    'RAG_ENGINE': {
        'chunk_size': 1000,
        'chunk_overlap': 100,
        'top_k_retrieval': 3,
        'default_question_count': 5,
        'default_question_types': ['MC', 'TF'],
        'default_difficulty': 'medium',
    },
    'VECTOR_STORE_DIR': BASE_DIR / 'vector_store',
    'EMBEDDINGS_MODEL': 'sentence-transformers/all-mpnet-base-v2',
    'DEFAULT_MODEL': {
        'name': 'Gemini Flash 2.5',
        'provider': 'gemini',
        'model_id': 'gemini-2.5-flash-preview-05-20',
        'api_key': os.getenv('GOOGLE_API_KEY', ''),
        'max_tokens': 8000,
        'temperature': 0.7,
        'is_active': True,
        'is_default': True
    },
    'GOOGLE_API_KEY': os.getenv('GOOGLE_API_KEY', ''),
}
