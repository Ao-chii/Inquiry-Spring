from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Document, DocumentChunk


class UserSerializer(serializers.ModelSerializer):
    """用户序列化器"""
    
    class Meta:
        model = User
        fields = ['id', 'username', 'first_name', 'last_name']


class DocumentChunkSerializer(serializers.ModelSerializer):
    """文档片段序列化器"""
    
    class Meta:
        model = DocumentChunk
        fields = [
            'id', 'content', 'chunk_index', 'metadata',
            'embedding_vector', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class DocumentListSerializer(serializers.ModelSerializer):
    """文档列表序列化器"""
    chunk_count = serializers.SerializerMethodField()
    conversation_count = serializers.SerializerMethodField()

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'file_type', 'file_size',
            'chunk_count', 'conversation_count', 'is_processed',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def get_chunk_count(self, obj):
        """获取文档片段数量"""
        return obj.chunks.count()
    
    def get_conversation_count(self, obj):
        """获取关联对话数量"""
        return obj.conversations.count()


class DocumentDetailSerializer(serializers.ModelSerializer):
    """文档详情序列化器"""
    chunks = DocumentChunkSerializer(many=True, read_only=True)

    class Meta:
        model = Document
        fields = [
            'id', 'title', 'content', 'file_type', 'file_size',
            'file_path', 'chunks', 'metadata',
            'is_processed', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class DocumentCreateSerializer(serializers.ModelSerializer):
    """创建文档序列化器"""
    
    class Meta:
        model = Document
        fields = ['title', 'content', 'file_type', 'metadata']
    
    def create(self, validated_data):
        # 计算文件大小
        content = validated_data.get('content', '')
        validated_data['file_size'] = len(content.encode('utf-8'))

        return super().create(validated_data)


class DocumentUpdateSerializer(serializers.ModelSerializer):
    """更新文档序列化器"""
    
    class Meta:
        model = Document
        fields = ['title', 'content', 'metadata', 'is_processed']
    
    def update(self, instance, validated_data):
        # 如果内容更新，重新计算文件大小
        if 'content' in validated_data:
            content = validated_data['content']
            validated_data['file_size'] = len(content.encode('utf-8'))
        
        return super().update(instance, validated_data)


class DocumentSearchSerializer(serializers.Serializer):
    """文档搜索序列化器"""
    query = serializers.CharField(max_length=200, required=False, help_text="搜索关键词")
    file_type = serializers.CharField(max_length=10, required=False, help_text="文件类型")
    user_id = serializers.IntegerField(required=False, help_text="用户ID")
    start_date = serializers.DateTimeField(required=False, help_text="开始时间")
    end_date = serializers.DateTimeField(required=False, help_text="结束时间")
    is_processed = serializers.BooleanField(required=False, help_text="是否已处理")
    min_size = serializers.IntegerField(required=False, help_text="最小文件大小")
    max_size = serializers.IntegerField(required=False, help_text="最大文件大小")
    
    def validate(self, data):
        """验证搜索参数"""
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if start_date and end_date and start_date > end_date:
            raise serializers.ValidationError("开始时间不能晚于结束时间")
        
        min_size = data.get('min_size')
        max_size = data.get('max_size')
        
        if min_size and max_size and min_size > max_size:
            raise serializers.ValidationError("最小文件大小不能大于最大文件大小")
        
        return data


class DocumentChunkCreateSerializer(serializers.ModelSerializer):
    """创建文档片段序列化器"""
    
    class Meta:
        model = DocumentChunk
        fields = ['document', 'content', 'chunk_index', 'metadata']
    
    def validate_document(self, value):
        """验证文档是否存在"""
        if not value.is_processed:
            raise serializers.ValidationError("文档尚未处理完成")
        return value


class DocumentStatisticsSerializer(serializers.Serializer):
    """文档统计序列化器"""
    total_documents = serializers.IntegerField()
    processed_documents = serializers.IntegerField()
    total_chunks = serializers.IntegerField()
    total_size = serializers.IntegerField()
    file_type_stats = serializers.DictField()
    recent_documents = DocumentListSerializer(many=True)
