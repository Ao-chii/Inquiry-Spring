from django.contrib import admin
from .models import Conversation, Message, ChatSession


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'user', 'created_at', 'updated_at', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['title', 'user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'is_user', 'content_preview', 'ai_model', 'created_at']
    list_filter = ['is_user', 'ai_model', 'created_at']
    search_fields = ['content']
    readonly_fields = ['created_at']
    # 删除了反馈相关字段
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '消息预览'


@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    list_display = ['id', 'session_id', 'user_message_preview', 'ai_response_preview', 'timestamp']
    list_filter = ['timestamp']
    search_fields = ['user_message', 'ai_response']
    readonly_fields = ['timestamp']
    
    def user_message_preview(self, obj):
        return obj.user_message[:30] + '...' if len(obj.user_message) > 30 else obj.user_message
    user_message_preview.short_description = '用户消息'
    
    def ai_response_preview(self, obj):
        return obj.ai_response[:30] + '...' if len(obj.ai_response) > 30 else obj.ai_response
    ai_response_preview.short_description = 'AI回复'
