from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Quiz, Question, QuizAttempt
from apps.documents.models import Document


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class DocumentSerializer(serializers.ModelSerializer):
    """文档序列化器（简化版）"""
    
    class Meta:
        model = Document
        fields = ['id', 'title', 'file_type']


class QuestionSerializer(serializers.ModelSerializer):
    """问题序列化器"""

    class Meta:
        model = Question
        fields = [
            'id', 'content', 'question_type', 'options', 'correct_answer',
            'explanation', 'source_passage', 'knowledge_points',
            'difficulty', 'order', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class QuestionCreateSerializer(serializers.ModelSerializer):
    """创建问题序列化器"""

    class Meta:
        model = Question
        fields = [
            'quiz', 'content', 'question_type', 'options', 'correct_answer',
            'explanation', 'source_passage', 'knowledge_points',
            'difficulty', 'order'
        ]


class QuizListSerializer(serializers.ModelSerializer):
    """测验列表序列化器"""
    user = UserSerializer(read_only=True)
    document = DocumentSerializer(read_only=True)
    question_count = serializers.SerializerMethodField()
    attempt_count = serializers.SerializerMethodField()
    average_score = serializers.SerializerMethodField()
    
    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'user', 'document',
            'question_count', 'attempt_count', 'average_score',
            'difficulty_level', 'time_limit', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_question_count(self, obj):
        """获取问题数量"""
        return obj.questions.count()
    
    def get_attempt_count(self, obj):
        """获取尝试次数"""
        return obj.attempts.count()
    
    def get_average_score(self, obj):
        """获取平均分数"""
        attempts = obj.attempts.filter(is_completed=True)
        if attempts.exists():
            total_score = sum(attempt.score for attempt in attempts)
            return round(total_score / attempts.count(), 2)
        return 0


class QuizDetailSerializer(serializers.ModelSerializer):
    """测验详情序列化器"""
    user = UserSerializer(read_only=True)
    document = DocumentSerializer(read_only=True)
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quiz
        fields = [
            'id', 'title', 'description', 'user', 'document',
            'questions', 'difficulty_level', 'time_limit',
            'passing_score', 'is_active', 'metadata',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class QuizCreateSerializer(serializers.ModelSerializer):
    """创建测验序列化器"""
    
    class Meta:
        model = Quiz
        fields = [
            'title', 'description', 'document', 'difficulty_level',
            'time_limit', 'passing_score', 'metadata'
        ]
    
    def create(self, validated_data):
        # 从请求上下文中获取用户
        user = self.context['request'].user if self.context['request'].user.is_authenticated else None
        validated_data['user'] = user
        return super().create(validated_data)


class QuizAttemptSerializer(serializers.ModelSerializer):
    """测验尝试序列化器"""
    user = UserSerializer(read_only=True)
    quiz = QuizListSerializer(read_only=True)
    
    class Meta:
        model = QuizAttempt
        fields = [
            'id', 'user', 'quiz', 'score', 'total_questions',
            'correct_answers', 'is_completed', 'time_taken',
            'answers_data', 'started_at', 'completed_at'
        ]
        read_only_fields = ['id', 'started_at', 'completed_at']


class QuizAttemptCreateSerializer(serializers.ModelSerializer):
    """创建测验尝试序列化器"""
    
    class Meta:
        model = QuizAttempt
        fields = ['quiz']
    
    def create(self, validated_data):
        # 从请求上下文中获取用户
        user = self.context['request'].user if self.context['request'].user.is_authenticated else None
        validated_data['user'] = user
        
        # 设置初始值
        quiz = validated_data['quiz']
        validated_data['total_questions'] = quiz.questions.count()
        
        return super().create(validated_data)


class QuizAttemptSubmitSerializer(serializers.Serializer):
    """提交测验答案序列化器"""
    answers = serializers.DictField(
        child=serializers.ListField(child=serializers.IntegerField()),
        help_text="问题ID到答案ID列表的映射"
    )
    
    def validate_answers(self, value):
        """验证答案格式"""
        if not value:
            raise serializers.ValidationError("答案不能为空")
        
        # 验证答案格式
        for question_id, answer_ids in value.items():
            try:
                int(question_id)
            except ValueError:
                raise serializers.ValidationError(f"无效的问题ID: {question_id}")
            
            if not isinstance(answer_ids, list):
                raise serializers.ValidationError(f"问题 {question_id} 的答案必须是列表")
            
            for answer_id in answer_ids:
                if not isinstance(answer_id, int):
                    raise serializers.ValidationError(f"无效的答案ID: {answer_id}")
        
        return value


class QuizSearchSerializer(serializers.Serializer):
    """测验搜索序列化器"""
    query = serializers.CharField(max_length=200, required=False, help_text="搜索关键词")
    difficulty_level = serializers.ChoiceField(
        choices=Quiz.DIFFICULTY_CHOICES, 
        required=False, 
        help_text="难度级别"
    )
    document_id = serializers.IntegerField(required=False, help_text="文档ID")
    user_id = serializers.IntegerField(required=False, help_text="用户ID")
    start_date = serializers.DateTimeField(required=False, help_text="开始时间")
    end_date = serializers.DateTimeField(required=False, help_text="结束时间")
    is_active = serializers.BooleanField(required=False, help_text="是否激活")
    min_questions = serializers.IntegerField(required=False, help_text="最少问题数")
    max_questions = serializers.IntegerField(required=False, help_text="最多问题数")
    
    def validate(self, data):
        """验证搜索参数"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("开始时间不能晚于结束时间")
        
        min_questions = data.get('min_questions')
        max_questions = data.get('max_questions')
        
        if min_questions and max_questions and min_questions > max_questions:
            raise serializers.ValidationError("最少问题数不能大于最多问题数")
        
        return data


class QuizStatisticsSerializer(serializers.Serializer):
    """测验统计序列化器"""
    total_quizzes = serializers.IntegerField()
    active_quizzes = serializers.IntegerField()
    total_questions = serializers.IntegerField()
    total_attempts = serializers.IntegerField()
    completed_attempts = serializers.IntegerField()
    average_score = serializers.FloatField()
    difficulty_stats = serializers.DictField()
    recent_quizzes = QuizListSerializer(many=True)
