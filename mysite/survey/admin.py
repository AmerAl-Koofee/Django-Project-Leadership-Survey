from django.contrib import admin
from .models import Survey, Question, UserAnswer, Answer


@admin.register(Survey)
class SurveyAdmin(admin.ModelAdmin):
    list_display = ('name', 'created_at', 'is_editable')
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ('label', 'survey', 'field_type', 'order', 'is_required')
    list_filter = ('survey', 'field_type')


@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ('survey', 'user', 'created_at')


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ('question', 'value', 'user_answer')
