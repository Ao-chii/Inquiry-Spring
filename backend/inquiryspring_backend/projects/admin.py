from django.contrib import admin
from .models import Project, ProjectDocument, ProjectStats


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'user', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description', 'user__username']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ProjectDocument)
class ProjectDocumentAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'document', 'is_primary', 'added_at']
    list_filter = ['is_primary', 'added_at', 'project']
    search_fields = ['project__name', 'document__title']
    readonly_fields = ['added_at']


@admin.register(ProjectStats)
class ProjectStatsAdmin(admin.ModelAdmin):
    list_display = ['id', 'project', 'total_documents', 'total_chats', 'total_quizzes', 'completion_rate', 'last_activity']
    list_filter = ['last_activity', 'project']
    search_fields = ['project__name']
    readonly_fields = ['last_activity']
