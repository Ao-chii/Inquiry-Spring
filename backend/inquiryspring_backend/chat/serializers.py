from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Conversation, Message
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


class MessageSerializer(serializers.ModelSerializer):
    """消息序列化器"""
    
    class Meta:
        model = Message
        fields = [
            'id', 'content', 'is_user', 'metadata',
            'feedback_score', 'feedback_comment', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ConversationListSerializer(serializers.ModelSerializer):
    """对话列表序列化器"""
    user = UserSerializer(read_only=True)
    document = DocumentSerializer(read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message = serializers.SerializerMethodField()
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'mode', 'user', 'document',
            'message_count', 'last_message', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_message_count(self, obj):
        """获取消息数量"""
        return obj.messages.count()
    
    def get_last_message(self, obj):
        """获取最后一条消息"""
        last_message = obj.messages.last()
        if last_message:
            return {
                'content': last_message.content[:100] + '...' if len(last_message.content) > 100 else last_message.content,
                'is_user': last_message.is_user,
                'created_at': last_message.created_at
            }
        return None


class ConversationDetailSerializer(serializers.ModelSerializer):
    """对话详情序列化器"""
    user = UserSerializer(read_only=True)
    document = DocumentSerializer(read_only=True)
    messages = MessageSerializer(many=True, read_only=True)
    
    class Meta:
        model = Conversation
        fields = [
            'id', 'title', 'mode', 'user', 'document',
            'context', 'messages', 'is_active',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ConversationCreateSerializer(serializers.ModelSerializer):
    """创建对话序列化器"""
    
    class Meta:
        model = Conversation
        fields = ['title', 'mode', 'document', 'context']
    
    def create(self, validated_data):
        # 从请求上下文中获取用户
        user = self.context['request'].user if self.context['request'].user.is_authenticated else None
        validated_data['user'] = user
        return super().create(validated_data)


class MessageCreateSerializer(serializers.ModelSerializer):
    """创建消息序列化器"""
    
    class Meta:
        model = Message
        fields = ['conversation', 'content', 'is_user', 'metadata']
    
    def validate_conversation(self, value):
        """验证对话是否存在且激活"""
        if not value.is_active:
            raise serializers.ValidationError("对话已被禁用")
        return value


class MessageFeedbackSerializer(serializers.ModelSerializer):
    """消息反馈序列化器"""
    
    class Meta:
        model = Message
        fields = ['feedback_score', 'feedback_comment']
    
    def validate_feedback_score(self, value):
        """验证反馈评分"""
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError("反馈评分必须在1-5之间")
        return value


class ConversationSearchSerializer(serializers.Serializer):
    """对话搜索序列化器"""
    query = serializers.CharField(max_length=200, required=False, help_text="搜索关键词")
    mode = serializers.ChoiceField(choices=Conversation.MODE_CHOICES, required=False, help_text="对话模式")
    document_id = serializers.IntegerField(required=False, help_text="文档ID")
    user_id = serializers.IntegerField(required=False, help_text="用户ID")
    start_date = serializers.DateTimeField(required=False, help_text="开始时间")
    end_date = serializers.DateTimeField(required=False, help_text="结束时间")
    is_active = serializers.BooleanField(required=False, help_text="是否激活")
    
    def validate(self, data):
        """验证搜索参数"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("开始时间不能晚于结束时间")
        
        return data
