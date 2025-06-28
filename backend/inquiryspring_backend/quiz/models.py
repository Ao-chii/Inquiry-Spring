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

    # 元数据字段 - ai_services需要
    metadata = models.JSONField('元数据', default=dict, blank=True)

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

        # 处理correct_answer字段 - 确保列表格式正确存储
        if hasattr(self, '_correct_answer_list'):
            # 如果设置了列表格式的答案，转换为适当的存储格式
            self._save_correct_answer_from_list()

        super().save(*args, **kwargs)

    def _save_correct_answer_from_list(self):
        """将列表格式的正确答案转换为存储格式"""
        if hasattr(self, '_correct_answer_list'):
            answer_list = self._correct_answer_list
            if isinstance(answer_list, list) and len(answer_list) > 1:
                # 多选题，存储为JSON字符串
                import json
                self.correct_answer = json.dumps(answer_list, ensure_ascii=False)
            elif isinstance(answer_list, list) and len(answer_list) == 1:
                # 单选题，存储为字符串
                self.correct_answer = str(answer_list[0])
            else:
                # 其他情况，直接转换为字符串
                self.correct_answer = str(answer_list) if answer_list else ''
            delattr(self, '_correct_answer_list')

    def get_correct_answer_list(self):
        """获取正确答案列表，自动处理JSON格式"""
        try:
            import json
            # 尝试解析JSON格式的答案（多选题）
            if isinstance(self.correct_answer, str) and self.correct_answer.startswith('['):
                return json.loads(self.correct_answer)
            else:
                # 单选题或其他类型，返回单个答案的列表
                return [self.correct_answer] if self.correct_answer else []
        except (json.JSONDecodeError, AttributeError):
            # 如果解析失败，返回原始答案
            return [self.correct_answer] if self.correct_answer else []

    def set_correct_answer_list(self, answer_list):
        """设置正确答案列表，延迟到save时处理"""
        self._correct_answer_list = answer_list

    @classmethod
    def create_with_correct_answer(cls, quiz, correct_answer, **kwargs):
        """创建Question实例，正确处理correct_answer字段"""
        # 处理correct_answer字段
        if isinstance(correct_answer, list):
            if len(correct_answer) > 1:
                # 多选题，存储为JSON字符串
                import json
                kwargs['correct_answer'] = json.dumps(correct_answer, ensure_ascii=False)
            elif len(correct_answer) == 1:
                # 单选题，存储为字符串
                kwargs['correct_answer'] = str(correct_answer[0])
            else:
                # 空列表
                kwargs['correct_answer'] = ''
        else:
            # 非列表类型，直接存储
            kwargs['correct_answer'] = str(correct_answer) if correct_answer is not None else ''

        return cls(quiz=quiz, **kwargs)

    def get_correct_answer_list(self):
        """获取正确答案列表，处理多选题的JSON格式"""
        try:
            import json
            # 尝试解析JSON格式的答案（多选题）
            if self.correct_answer.startswith('[') and self.correct_answer.endswith(']'):
                return json.loads(self.correct_answer)
            else:
                # 单选题或其他类型，返回单个答案
                return [self.correct_answer]
        except (json.JSONDecodeError, AttributeError):
            # 如果解析失败，返回原始答案
            return [self.correct_answer] if self.correct_answer else []

    def set_correct_answer_list(self, answer_list):
        """设置正确答案列表，自动处理多选题的JSON格式"""
        if isinstance(answer_list, list) and len(answer_list) > 1:
            # 多选题，存储为JSON
            import json
            self.correct_answer = json.dumps(answer_list, ensure_ascii=False)
        elif isinstance(answer_list, list) and len(answer_list) == 1:
            # 单选题，存储为字符串
            self.correct_answer = str(answer_list[0])
        else:
            # 其他情况，直接存储
            self.correct_answer = str(answer_list) if answer_list else ''

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
