from django.contrib import admin
from .models import Quiz, Question, QuizAttempt, Answer


@admin.register(Quiz)
class QuizAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'question_count', 'difficulty', 'is_active', 'created_at']
    list_filter = ['difficulty', 'is_active', 'created_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['id', 'quiz', 'question_type', 'question_preview', 'difficulty', 'points']
    list_filter = ['question_type', 'difficulty', 'quiz']
    search_fields = ['question_text']
    readonly_fields = ['created_at']
    
    def question_preview(self, obj):
        return obj.question_text[:50] + '...' if len(obj.question_text) > 50 else obj.question_text
    question_preview.short_description = '题目预览'


@admin.register(QuizAttempt)
class QuizAttemptAdmin(admin.ModelAdmin):
    list_display = ['id', 'quiz', 'user', 'score', 'total_points', 'percentage', 'is_completed', 'started_at']
    list_filter = ['is_completed', 'started_at', 'quiz']
    search_fields = ['quiz__title', 'user__username']
    readonly_fields = ['started_at', 'completed_at']
    
    def percentage(self, obj):
        if obj.total_points > 0:
            return f"{obj.score / obj.total_points * 100:.1f}%"
        return "0%"
    percentage.short_description = '得分率'


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['id', 'attempt', 'question_preview', 'user_answer_preview', 'is_correct', 'points_earned']
    list_filter = ['is_correct', 'attempt__quiz', 'created_at']
    search_fields = ['user_answer', 'question__question_text']
    readonly_fields = ['created_at']
    
    def question_preview(self, obj):
        return obj.question.question_text[:30] + '...' if len(obj.question.question_text) > 30 else obj.question.question_text
    question_preview.short_description = '题目'
    
    def user_answer_preview(self, obj):
        return obj.user_answer[:30] + '...' if len(obj.user_answer) > 30 else obj.user_answer
    user_answer_preview.short_description = '用户答案'
