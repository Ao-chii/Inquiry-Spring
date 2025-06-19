from django.db import models
from django.contrib.auth.models import User


class Conversation(models.Model):
    """对话会话"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    title = models.CharField('对话标题', max_length=200, blank=True)
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    is_active = models.BooleanField('是否活跃', default=True)

    class Meta:
        verbose_name = '对话会话'
        verbose_name_plural = '对话会话'
        ordering = ['-updated_at']

    def __str__(self):
        return self.title or f'对话 {self.id}'


class Message(models.Model):
    """聊天消息"""
    conversation = models.ForeignKey(
        Conversation, 
        on_delete=models.CASCADE, 
        related_name='messages',
        null=True, 
        blank=True
    )
    content = models.TextField('消息内容')
    is_user = models.BooleanField('是否用户消息', default=True)
    
    # AI相关字段
    ai_model = models.CharField('AI模型', max_length=100, blank=True)
    processing_time = models.FloatField('处理时间(秒)', default=0.0)
    tokens_used = models.IntegerField('使用令牌数', default=0)
    
    # 删除了反馈功能
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '聊天消息'
        verbose_name_plural = '聊天消息'
        ordering = ['created_at']

    def __str__(self):
        role = '用户' if self.is_user else 'AI'
        return f'{role}: {self.content[:50]}...'


class ChatSession(models.Model):
    """聊天会话（兼容旧版本）"""
    session_id = models.CharField('会话ID', max_length=100, unique=True, null=True, blank=True)
    user_message = models.TextField('用户消息')
    ai_response = models.TextField('AI回复')
    is_ready = models.BooleanField('是否已完成', default=False)  # 新增字段
    timestamp = models.DateTimeField('时间戳', auto_now_add=True)
    
    class Meta:
        verbose_name = '聊天会话'
        verbose_name_plural = '聊天会话'
        ordering = ['-timestamp']

    def __str__(self):
        return f'会话 {self.session_id or self.id}: {self.user_message[:30]}...'
