"""
文档处理服务 - 使用textract提取各种格式文档的内容
"""
import logging
import os
import tempfile
from typing import Dict, Any, Optional
from django.conf import settings

logger = logging.getLogger(__name__)

# 检查文档处理库是否可用
try:
    import PyPDF2
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    from docx import Document as DocxDocument
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

PROCESSING_AVAILABLE = PDF_AVAILABLE or DOCX_AVAILABLE
logger.info(f"Document processing capabilities: PDF={PDF_AVAILABLE}, DOCX={DOCX_AVAILABLE}")


class DocumentProcessor:
    """文档处理器 - 使用textract提取文档内容"""
    
    # 支持的文件格式
    SUPPORTED_FORMATS = {
        # 文本文件
        'txt': 'text',
        'csv': 'text',
        'json': 'text',
        'xml': 'text',
        'html': 'text',
        'htm': 'text',

        # Office文档
        'docx': 'office',

        # PDF文件
        'pdf': 'pdf',
    }
    
    def __init__(self):
        self.available = PROCESSING_AVAILABLE
        self.pdf_available = PDF_AVAILABLE
        self.docx_available = DOCX_AVAILABLE
    
    def get_file_type(self, filename: str) -> Optional[str]:
        """获取文件类型"""
        if not filename or '.' not in filename:
            return None
        
        extension = filename.rsplit('.', 1)[1].lower()
        return self.SUPPORTED_FORMATS.get(extension)
    
    def is_supported(self, filename: str) -> bool:
        """检查文件是否支持"""
        return self.get_file_type(filename) is not None
    
    def extract_text(self, file_path: str, filename: str = None) -> Dict[str, Any]:
        """
        从文档中提取文本内容
        
        Args:
            file_path: 文件路径
            filename: 文件名（用于确定文件类型）
        
        Returns:
            包含提取结果的字典
        """
        if not self.available:
            return {
                'success': False,
                'error': 'No document processing libraries available',
                'content': '',
                'metadata': {}
            }
        
        if not os.path.exists(file_path):
            return {
                'success': False,
                'error': 'File not found',
                'content': '',
                'metadata': {}
            }
        
        # 确定文件名
        if not filename:
            filename = os.path.basename(file_path)
        
        # 检查文件格式支持
        file_type = self.get_file_type(filename)
        if not file_type:
            return {
                'success': False,
                'error': f'Unsupported file format: {filename}',
                'content': '',
                'metadata': {'file_type': 'unknown'}
            }
        
        try:
            logger.info(f"Processing document: {filename} (type: {file_type})")
            
            # 获取文件大小
            file_size = os.path.getsize(file_path)
            
            # 根据文件类型选择提取方法
            if file_type == 'text':
                # 对于纯文本文件，直接读取
                content = self._extract_text_file(file_path)
                extraction_method = 'direct'
            elif file_type == 'pdf':
                content = self._extract_pdf(file_path)
                extraction_method = 'PyPDF2'
            elif file_type == 'office':
                content = self._extract_docx(file_path)
                extraction_method = 'python-docx'
            else:
                raise Exception(f"Unsupported file type: {file_type}")
            
            # 清理和处理内容
            content = self._clean_content(content)
            
            metadata = {
                'file_type': file_type,
                'file_size': file_size,
                'content_length': len(content),
                'extraction_method': extraction_method
            }
            
            logger.info(f"Successfully extracted {len(content)} characters from {filename}")
            
            return {
                'success': True,
                'content': content,
                'metadata': metadata,
                'error': None
            }
            
        except Exception as e:
            logger.error(f"Failed to extract content from {filename}: {e}")
            return {
                'success': False,
                'error': str(e),
                'content': '',
                'metadata': {'file_type': file_type}
            }
    
    def _extract_text_file(self, file_path: str) -> str:
        """提取纯文本文件内容"""
        encodings = ['utf-8', 'gbk', 'gb2312', 'latin-1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        
        # 如果所有编码都失败，使用二进制模式并忽略错误
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    
    def _extract_pdf(self, file_path: str) -> str:
        """使用PyPDF2提取PDF内容"""
        if not self.pdf_available:
            raise Exception("PyPDF2 not available")

        try:
            content = []
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page in pdf_reader.pages:
                    content.append(page.extract_text())
            return '\n'.join(content)
        except Exception as e:
            logger.error(f"PDF extraction failed: {e}")
            raise

    def _extract_docx(self, file_path: str) -> str:
        """使用python-docx提取Word文档内容"""
        if not self.docx_available:
            raise Exception("python-docx not available")

        try:
            doc = DocxDocument(file_path)
            content = []
            for paragraph in doc.paragraphs:
                content.append(paragraph.text)
            return '\n'.join(content)
        except Exception as e:
            logger.error(f"DOCX extraction failed: {e}")
            raise


    
    def _clean_content(self, content: str) -> str:
        """清理提取的内容"""
        if not content:
            return ""
        
        # 移除多余的空白字符
        lines = content.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # 去除行首行尾空白
            line = line.strip()
            # 跳过空行（但保留一些结构）
            if line or (cleaned_lines and cleaned_lines[-1]):
                cleaned_lines.append(line)
        
        # 重新组合，限制连续空行
        result = []
        prev_empty = False
        
        for line in cleaned_lines:
            if not line:
                if not prev_empty:
                    result.append(line)
                prev_empty = True
            else:
                result.append(line)
                prev_empty = False
        
        return '\n'.join(result).strip()
    
    def get_supported_formats(self) -> Dict[str, list]:
        """获取支持的文件格式列表"""
        formats_by_type = {}
        
        for ext, file_type in self.SUPPORTED_FORMATS.items():
            if file_type not in formats_by_type:
                formats_by_type[file_type] = []
            formats_by_type[file_type].append(ext)
        
        return formats_by_type
    
    def validate_file(self, file_path: str, filename: str = None, max_size_mb: int = 50) -> Dict[str, Any]:
        """
        验证文件是否可以处理
        
        Args:
            file_path: 文件路径
            filename: 文件名
            max_size_mb: 最大文件大小（MB）
        
        Returns:
            验证结果
        """
        if not filename:
            filename = os.path.basename(file_path)
        
        # 检查文件是否存在
        if not os.path.exists(file_path):
            return {
                'valid': False,
                'error': 'File not found',
                'file_type': None
            }
        
        # 检查文件格式
        file_type = self.get_file_type(filename)
        if not file_type:
            return {
                'valid': False,
                'error': f'Unsupported file format: {filename}',
                'file_type': None
            }
        
        # 检查文件大小
        file_size = os.path.getsize(file_path)
        max_size_bytes = max_size_mb * 1024 * 1024
        
        if file_size > max_size_bytes:
            return {
                'valid': False,
                'error': f'File too large: {file_size / 1024 / 1024:.1f}MB (max: {max_size_mb}MB)',
                'file_type': file_type
            }
        
        return {
            'valid': True,
            'error': None,
            'file_type': file_type,
            'file_size': file_size
        }


# 全局文档处理器实例
document_processor = DocumentProcessor()
