from django.db import models
from django.conf import settings


class AIModel(models.Model):
    """AI模型配置"""
    
    PROVIDER_CHOICES = [
        ('gemini', 'Google Gemini'),
        ('local', '本地模型'),
    ]
    
    name = models.CharField('模型名称', max_length=100)
    provider = models.CharField('供应商', max_length=20, choices=PROVIDER_CHOICES)
    model_id = models.CharField('模型ID', max_length=100)
    api_key = models.CharField('API密钥', max_length=200, blank=True)
    api_base = models.URLField('API基础URL', blank=True)
    
    # 模型参数
    max_tokens = models.PositiveIntegerField('最大令牌数', default=10000)
    temperature = models.FloatField('温度参数', default=0.7)
    
    # 状态
    is_active = models.BooleanField('是否激活', default=True)
    is_default = models.BooleanField('是否默认', default=False)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = 'AI模型'
        verbose_name_plural = 'AI模型'
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.name} ({self.get_provider_display()})"
    
    def save(self, *args, **kwargs):
        # 确保只有一个默认模型
        if self.is_default:
            # 首先将所有模型的is_default字段设置为False
            AIModel.objects.filter(is_default=True).update(is_default=False)
            # 然后在保存当前实例时，由于self.is_default=True，它将被保存为默认值
        super().save(*args, **kwargs)


class PromptTemplate(models.Model):
    """提示词模板"""
    
    TEMPLATE_TYPES = [
        ('quiz', '测验生成'),
        ('chat', '智能对话'), 
        ('summary', '文档总结')
    ]
    
    name = models.CharField('模板名称', max_length=100)
    template_type = models.CharField('模板类型', max_length=20, choices=TEMPLATE_TYPES)
    content = models.TextField('模板内容')
    variables = models.JSONField('变量列表', default=list, blank=True)
    
    # 版本控制
    version = models.CharField('版本', max_length=20, default='1.0')
    is_active = models.BooleanField('是否激活', default=True)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    class Meta:
        verbose_name = '提示词模板'
        verbose_name_plural = '提示词模板'
        ordering = ['template_type', 'name']
    
    def __str__(self):
        return f"{self.get_template_type_display()} - {self.name}"


class AITaskLog(models.Model):
    """AI任务日志"""
    
    TASK_TYPES = [
        # 主要任务
        ('chat', '智能对话'),
        ('quiz', '测验生成'),
        ('summary', '文档总结'),
        
        # 内部子任务，用于更精细的日志记录
        ('query_rewrite', '查询重写'),
        ('conversation_summary', '对话历史摘要'),
        
        # 结构化输出修复任务
        ('chat_fix', '聊天输出修复'),
        ('quiz_fix', '测验输出修复'),
        ('summary_fix', '摘要输出修复'),
    ]
    
    STATUS_CHOICES = [
        ('pending', '等待中'),
        ('processing', '处理中'),
        ('completed', '已完成'),
        ('failed', '失败'),
    ]
    
    # 关联与追溯字段
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='关联用户'
    )
    session_id = models.CharField('会话ID', max_length=100, blank=True, db_index=True, help_text="用于追踪匿名用户的会话")
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='关联文档'
    )

    task_type = models.CharField('任务类型', max_length=20, choices=TASK_TYPES)
    model = models.ForeignKey(AIModel, on_delete=models.SET_NULL, null=True, verbose_name='使用模型')
    
    # 输入输出
    input_data = models.JSONField('输入数据', default=dict)
    output_data = models.JSONField('输出数据', default=dict, blank=True)
    
    # 状态和性能
    status = models.CharField('状态', max_length=20, choices=STATUS_CHOICES, default='pending')
    error_message = models.TextField('错误信息', blank=True)
    
    # 性能指标
    tokens_used = models.PositiveIntegerField('使用令牌数', default=0)
    processing_time = models.FloatField('处理时间(秒)', default=0.0)
    cost = models.DecimalField('成本', max_digits=10, decimal_places=4, default=0.0)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    
    class Meta:
        verbose_name = 'AI任务日志'
        verbose_name_plural = 'AI任务日志'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.get_task_type_display()} - {self.get_status_display()}"
