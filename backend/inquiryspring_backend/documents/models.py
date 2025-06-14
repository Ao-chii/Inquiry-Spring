from django.db import models
from django.contrib.auth.models import User
import os


def upload_to(instance, filename):
    """文件上传路径"""
    return f'documents/{instance.id}/{filename}'


class Document(models.Model):
    """文档模型"""
    title = models.CharField('文档标题', max_length=200)
    file = models.FileField('文件', upload_to=upload_to)
    file_type = models.CharField('文件类型', max_length=50)
    file_size = models.BigIntegerField('文件大小', default=0)
    
    # 处理状态
    is_processed = models.BooleanField('是否已处理', default=False)
    processing_status = models.CharField('处理状态', max_length=50, default='pending')
    error_message = models.TextField('错误信息', blank=True)
    
    # 内容
    content = models.TextField('文档内容', blank=True)
    summary = models.TextField('文档摘要', blank=True)
    
    # 元数据
    metadata = models.JSONField('元数据', default=dict, blank=True)
    
    # 时间戳
    uploaded_at = models.DateTimeField('上传时间', auto_now_add=True)
    processed_at = models.DateTimeField('处理时间', null=True, blank=True)
    
    # 用户关联
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = '文档'
        verbose_name_plural = '文档'
        ordering = ['-uploaded_at']

    def __str__(self):
        return self.title

    @property
    def filename(self):
        return os.path.basename(self.file.name) if self.file else ''


class DocumentChunk(models.Model):
    """文档分块"""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name='chunks')
    content = models.TextField('分块内容')
    chunk_index = models.IntegerField('分块索引')
    
    # 向量化相关
    embedding = models.JSONField('向量嵌入', null=True, blank=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '文档分块'
        verbose_name_plural = '文档分块'
        ordering = ['document', 'chunk_index']

    def __str__(self):
        return f'{self.document.title} - 分块 {self.chunk_index}'


class UploadedFile(models.Model):
    """上传文件（兼容旧版本）"""
    filename = models.CharField('文件名', max_length=255)
    file_path = models.CharField('文件路径', max_length=500)
    file_size = models.BigIntegerField('文件大小', default=0)
    upload_time = models.DateTimeField('上传时间', auto_now_add=True)
    
    class Meta:
        verbose_name = '上传文件'
        verbose_name_plural = '上传文件'
        ordering = ['-upload_time']

    def __str__(self):
        return self.filename
