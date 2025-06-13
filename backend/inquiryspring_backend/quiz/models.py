from django.db import models
from django.contrib.auth.models import User


class Quiz(models.Model):
    """测验"""
    title = models.CharField('测验标题', max_length=200)
    description = models.TextField('测验描述', blank=True)
    
    # 生成参数
    question_count = models.IntegerField('题目数量', default=5)
    difficulty = models.CharField('难度', max_length=20, default='medium')
    question_types = models.JSONField('题目类型', default=list)
    
    # 状态
    is_active = models.BooleanField('是否活跃', default=True)
    
    # 时间戳
    created_at = models.DateTimeField('创建时间', auto_now_add=True)
    updated_at = models.DateTimeField('更新时间', auto_now=True)
    
    # 用户关联
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = '测验'
        verbose_name_plural = '测验'
        ordering = ['-created_at']

    def __str__(self):
        return self.title


class Question(models.Model):
    """题目"""
    QUESTION_TYPES = [
        ('MC', '单选题'),
        ('MCM', '多选题'),
        ('TF', '判断题'),
        ('FB', '填空题'),
        ('SA', '简答题'),
    ]
    
    quiz = models.ForeignKey(Quiz, on_delete=models.CASCADE, related_name='questions')
    question_type = models.CharField('题目类型', max_length=10, choices=QUESTION_TYPES)
    question_text = models.TextField('题目内容')
    
    # 选项（用于选择题）
    options = models.JSONField('选项', default=list, blank=True)
    
    # 答案
    correct_answer = models.TextField('正确答案')
    explanation = models.TextField('解释', blank=True)
    
    # 元数据
    difficulty = models.CharField('难度', max_length=20, default='medium')
    points = models.IntegerField('分值', default=1)
    
    created_at = models.DateTimeField('创建时间', auto_now_add=True)

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
