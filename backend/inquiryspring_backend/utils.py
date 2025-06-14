"""
InquirySpring Backend 工具函数
"""
import os
import hashlib
import mimetypes
from typing import Dict, Any, Optional
from django.conf import settings
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile


def get_file_hash(file_content: bytes) -> str:
    """计算文件内容的MD5哈希值"""
    return hashlib.md5(file_content).hexdigest()


def get_file_type(filename: str) -> str:
    """根据文件名获取文件类型"""
    mime_type, _ = mimetypes.guess_type(filename)
    if mime_type:
        return mime_type.split('/')[0]  # 返回主类型，如 'text', 'image', 'application'
    return 'unknown'


def save_uploaded_file(file, upload_dir: str = 'uploads') -> Dict[str, Any]:
    """保存上传的文件并返回文件信息"""
    try:
        # 生成安全的文件名
        filename = file.name
        file_content = file.read()
        file_hash = get_file_hash(file_content)
        
        # 构建文件路径
        file_path = os.path.join(upload_dir, filename)
        
        # 保存文件
        saved_path = default_storage.save(file_path, ContentFile(file_content))
        
        return {
            'success': True,
            'filename': filename,
            'file_path': saved_path,
            'file_size': len(file_content),
            'file_hash': file_hash,
            'file_type': get_file_type(filename),
            'url': default_storage.url(saved_path)
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }


def read_file_content(file_path: str, encoding: str = 'utf-8') -> Optional[str]:
    """读取文件内容"""
    try:
        if default_storage.exists(file_path):
            with default_storage.open(file_path, 'r', encoding=encoding) as f:
                return f.read()
    except UnicodeDecodeError:
        # 尝试其他编码
        try:
            with default_storage.open(file_path, 'r', encoding='gbk') as f:
                return f.read()
        except:
            pass
    except Exception as e:
        print(f"读取文件失败: {e}")
    return None


def format_file_size(size_bytes: int) -> str:
    """格式化文件大小显示"""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f}{size_names[i]}"


def validate_file_type(filename: str, allowed_types: list = None) -> bool:
    """验证文件类型是否允许"""
    if allowed_types is None:
        allowed_types = ['txt', 'pdf', 'doc', 'docx', 'png', 'jpg', 'jpeg', 'gif']
    
    if '.' not in filename:
        return False
    
    file_ext = filename.rsplit('.', 1)[1].lower()
    return file_ext in allowed_types


def clean_text(text: str) -> str:
    """清理文本内容"""
    if not text:
        return ""
    
    # 移除多余的空白字符
    text = ' '.join(text.split())
    
    # 移除特殊字符（保留基本标点）
    import re
    text = re.sub(r'[^\w\s\u4e00-\u9fff.,!?;:()[]{}""''—-]', '', text)
    
    return text.strip()


def truncate_text(text: str, max_length: int = 100) -> str:
    """截断文本到指定长度"""
    if len(text) <= max_length:
        return text
    return text[:max_length] + '...'


def get_ai_service_status() -> Dict[str, Any]:
    """获取AI服务状态"""
    try:
        import os
        from .ai_services.llm_client import LLMClientFactory

        # 检查API密钥配置
        api_key_configured = bool(os.environ.get('GOOGLE_API_KEY'))

        # 检查离线模式
        offline_mode = os.environ.get("GEMINI_OFFLINE_MODE", "").lower() in ("true", "1", "yes")

        # 尝试创建LLM客户端来验证服务状态
        try:
            client = LLMClientFactory.create_client()
            service_available = True
        except Exception:
            service_available = False

        return {
            'status': 'ready' if api_key_configured and service_available and not offline_mode else 'limited',
            'api_key_configured': api_key_configured,
            'offline_mode': offline_mode,
            'service_available': service_available,
            'services_available': ['chat', 'quiz', 'summary']
        }
    except Exception as e:
        return {
            'status': 'error',
            'error': str(e),
            'api_key_configured': False,
            'offline_mode': True
        }


def format_response(data: Any, message: str = None, status: str = 'success') -> Dict[str, Any]:
    """格式化API响应"""
    response = {
        'status': status,
        'data': data
    }
    
    if message:
        response['message'] = message
    
    return response


def handle_api_error(error: Exception, context: str = '') -> Dict[str, Any]:
    """处理API错误"""
    error_message = str(error)
    if context:
        error_message = f"{context}: {error_message}"
    
    return {
        'status': 'error',
        'error': error_message,
        'data': None
    }
