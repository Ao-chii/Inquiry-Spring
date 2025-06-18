from django.db import models
from django.contrib.auth.models import User


class Quiz(models.Model):
    """测验 - 兼容ai_services字段"""
    title = models.CharField('测验标题', max_length=200)
    description = models.TextField('测验描述', blank=True)

    # ai_services期望的字段
    document = models.ForeignKey(
        'documents.Document',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name='关联文档'
    )
    difficulty_level = models.CharField('难度级别', max_length=20, default='medium')
    total_questions = models.IntegerField('题目总数', default=0)

    # 兼容字段（保持向后兼容）
    question_count = models.IntegerField('题目数量', default=5)
    difficulty = models.CharField('难度', max_length=20, default='medium')
    question_types = models.JSONField('题目类型', default=list)

    # 状态
    is_active = models.BooleanField('是否活跃', default=True)

    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)

    # 关联
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = '测验'
        verbose_name_plural = '测验'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Question(models.Model):
    """题目 - 兼容ai_services字段"""
    QUESTION_TYPES = [
        ('MC', '单选题'),
        ('MCM', '多选题'),
        ('TF', '判断题'),
        ('FB', '填空题'),
        ('SA', '简答题'),
    ]

    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')

    # ai_services期望的字段
    content = models.TextField('题目内容', default='')  # ai_services使用content
    question_type = models.CharField('题目类型', max_length=10, choices=QUESTION_TYPES)
    options = models.JSONField('选项', default=list, blank=True)
    correct_answer = models.TextField('正确答案')
    explanation = models.TextField('解释', blank=True)
    difficulty = models.CharField('难度', max_length=20, default='medium')
    knowledge_points = models.JSONField('知识点', default=list, blank=True)
    order = models.IntegerField('排序', default=0)  # ai_services使用order

    # 兼容字段
    question_text = models.TextField('题目文本', blank=True)  # 向后兼容
    points = models.IntegerField('分值', default=1)

    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    def save(self, *args, **kwargs):
        # 确保content和question_text同步
        if self.content and not self.question_text:
            self.question_text = self.content
        elif self.question_text and not self.content:
            self.content = self.question_text
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = '题目'
        verbose_name_plural = '题目'
        ordering = ['quiz', 'id']

    def __str__(self):
        return f'{self.quiz.title} - {self.question_text[:50]}...'


class QuizAttempt(models.Model):
    """测验尝试"""
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='attempts')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    
    # 结果
    score = models.FloatField('得分', default=0.0)
    total_points = models.IntegerField('总分', default=0)
    
    # 时间
    started_at = models.DateTimeField('开始时间', auto_now_add=True)
    completed_at = models.DateTimeField('完成时间', null=True, blank=True)
    
    # 状态
    is_completed = models.BooleanField('是否完成', default=False)

    class Meta:
        verbose_name = '测验尝试'
        verbose_name_plural = '测验尝试'
        ordering = ['-started_at']

    def __str__(self):
        return f'{self.quiz.title} - 尝试 {self.id}'


class Answer(models.Model):
    """答案"""
    attempt = models.ForeignKey(QuizAttempt, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE)
    
    # 用户答案
    user_answer = models.TextField('用户答案')
    is_correct = models.BooleanField('是否正确', default=False)
    
    # 评分
    points_earned = models.FloatField('获得分数', default=0.0)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

    class Meta:
        verbose_name = '答案'
        verbose_name_plural = '答案'
        ordering = ['attempt', 'question']

    def __str__(self):
        return f'{self.attempt} - {self.question.question_text[:30]}...'
