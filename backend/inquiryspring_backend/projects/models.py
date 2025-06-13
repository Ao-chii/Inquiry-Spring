from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    """学习项目"""
    name = models.CharField('项目名称', max_length=200)
    description = models.TextField('项目描述', blank=True)
    
    # 状态
    is_active = models.BooleanField('是否活跃', default=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    # 用户关联
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = '学习项目'
        verbose_name_plural = '学习项目'
        ordering = ['-updated_at']

    def __str__(self):
        return self.name


class ProjectDocument(models.Model):
    """项目文档关联"""
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='documents')
    document = models.ForeignKey('documents.Document', on_delete=models.CASCADE)
    
    # 关联信息
    added_at = models.DateTimeField('添加时间', auto_now_add=True)
    is_primary = models.BooleanField('是否主要文档', default=False)

    class Meta:
        verbose_name = '项目文档'
        verbose_name_plural = '项目文档'
        unique_together = ['project', 'document']

    def __str__(self):
        return f'{self.project.name} - {self.document.title}'


class ProjectStats(models.Model):
    """项目统计"""
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='stats')
    
    # 统计数据
    total_documents = models.IntegerField('文档总数', default=0)
    total_chats = models.IntegerField('聊天总数', default=0)
    total_quizzes = models.IntegerField('测验总数', default=0)
    
    # 学习进度
    completion_rate = models.FloatField('完成率', default=0.0)
    last_activity = models.DateTimeField('最后活动时间', auto_now=True)

    class Meta:
        verbose_name = '项目统计'
        verbose_name_plural = '项目统计'

    def __str__(self):
        return f'{self.project.name} - 统计'
