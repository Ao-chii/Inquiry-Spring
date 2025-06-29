from django.contrib import admin
from .models import Document, DocumentChunk


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'file_type', 'file_size', 'is_processed', 'uploaded_at']
    list_filter = ['is_processed', 'file_type', 'uploaded_at']
    search_fields = ['title', 'content']
    readonly_fields = ['uploaded_at', 'processed_at']
    
    fieldsets = (
        ('基本信息', {
            'fields': ('title', 'file', 'file_type', 'file_size', 'user')
        }),
        ('处理状态', {
            'fields': ('is_processed', 'processing_status', 'error_message')
        }),
        ('内容', {
            'fields': ('content', 'summary'),
            'classes': ('collapse',)
        }),
        ('时间信息', {
            'fields': ('uploaded_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(DocumentChunk)
class DocumentChunkAdmin(admin.ModelAdmin):
    list_display = ['id', 'document', 'chunk_index', 'content_preview', 'created_at']
    list_filter = ['document', 'created_at']
    search_fields = ['content']
    readonly_fields = ['created_at']
    
    def content_preview(self, obj):
        return obj.content[:50] + '...' if len(obj.content) > 50 else obj.content
    content_preview.short_description = '内容预览'


# 删除了UploadedFileAdmin - 现在统一使用Document模型
