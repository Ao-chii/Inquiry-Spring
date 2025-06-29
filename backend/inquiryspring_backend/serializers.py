"""
InquirySpring Backend 序列化器
"""
from rest_framework import serializers
from inquiryspring_backend.chat.models import ChatSession, Message, Conversation
from inquiryspring_backend.documents.models import Document
from inquiryspring_backend.quiz.models import Quiz, Question, QuizAttempt
from inquiryspring_backend.projects.models import Project, ProjectStats


class ChatSessionSerializer(serializers.ModelSerializer):
    """聊天会话序列化器"""
    class Meta:
        model = ChatSession
        fields = ['id', 'session_id', 'user_message', 'ai_response', 'timestamp']


class MessageSerializer(serializers.ModelSerializer):
    """消息序列化器"""
    class Meta:
        model = Message
        fields = ['id', 'content', 'is_user', 'ai_model', 'processing_time', 'created_at']


class ConversationSerializer(serializers.ModelSerializer):
    """对话序列化器"""
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = ['id', 'title', 'created_at', 'updated_at', 'is_active', 'messages']


# 删除了UploadedFileSerializer - 现在统一使用DocumentSerializer


class DocumentSerializer(serializers.ModelSerializer):
    """文档序列化器"""
    file_size_formatted = serializers.SerializerMethodField()
    
    class Meta:
        model = Document
        fields = ['id', 'title', 'file_type', 'file_size', 'file_size_formatted', 
                 'is_processed', 'summary', 'uploaded_at']
    
    def get_file_size_formatted(self, obj):
        from .utils import format_file_size
        return format_file_size(obj.file_size)


class QuestionSerializer(serializers.ModelSerializer):
    """题目序列化器"""
    class Meta:
        model = Question
        fields = ['id', 'question_type', 'question_text', 'options', 
                 'correct_answer', 'explanation', 'difficulty', 'points']


class QuizSerializer(serializers.ModelSerializer):
    """测验序列化器"""
    questions = QuestionSerializer(many=True, read_only=True)
    
    class Meta:
        model = Quiz
        fields = ['id', 'title', 'description', 'question_count', 
                 'difficulty', 'created_at', 'questions']


class QuizAttemptSerializer(serializers.ModelSerializer):
    """测验尝试序列化器"""
    quiz_title = serializers.CharField(source='quiz.title', read_only=True)
    percentage = serializers.SerializerMethodField()
    
    class Meta:
        model = QuizAttempt
        fields = ['id', 'quiz_title', 'score', 'total_points', 'percentage', 
                 'started_at', 'completed_at', 'is_completed']
    
    def get_percentage(self, obj):
        if obj.total_points > 0:
            return round(obj.score / obj.total_points * 100, 1)
        return 0


class ProjectStatsSerializer(serializers.ModelSerializer):
    """项目统计序列化器"""
    class Meta:
        model = ProjectStats
        fields = ['total_documents', 'total_chats', 'total_quizzes', 
                 'completion_rate', 'last_activity']


class ProjectSerializer(serializers.ModelSerializer):
    """项目序列化器"""
    stats = ProjectStatsSerializer(read_only=True)
    document_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ['id', 'name', 'description', 'is_active', 
                 'created_at', 'updated_at', 'stats', 'document_count']
    
    def get_document_count(self, obj):
        return obj.documents.count()


# API响应序列化器
class APIResponseSerializer(serializers.Serializer):
    """标准API响应序列化器"""
    status = serializers.CharField()
    message = serializers.CharField(required=False)
    data = serializers.JSONField(required=False)


class ChatRequestSerializer(serializers.Serializer):
    """聊天请求序列化器"""
    message = serializers.CharField(max_length=2000)
    context = serializers.CharField(required=False, allow_blank=True)


class QuizRequestSerializer(serializers.Serializer):
    """测验请求序列化器"""
    num = serializers.IntegerField(min_value=1, max_value=20, default=5)
    difficulty = serializers.ChoiceField(
        choices=['easy', 'medium', 'hard'], 
        default='medium'
    )
    types = serializers.ListField(
        child=serializers.ChoiceField(choices=['MC', 'TF', 'FB', 'SA']),
        default=['MC', 'TF']
    )
    topic = serializers.CharField(required=False, allow_blank=True)


class FileUploadSerializer(serializers.Serializer):
    """文件上传序列化器"""
    file = serializers.FileField()
    
    def validate_file(self, value):
        """验证文件"""
        from .utils import validate_file_type
        
        if not validate_file_type(value.name):
            raise serializers.ValidationError("不支持的文件类型")
        
        # 检查文件大小 (16MB)
        if value.size > 16 * 1024 * 1024:
            raise serializers.ValidationError("文件大小不能超过16MB")
        
        return value
