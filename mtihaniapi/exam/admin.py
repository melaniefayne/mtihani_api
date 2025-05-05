from django.contrib import admin
from exam.models import *


class ExamQuestionInline(admin.TabularInline):
    model = ExamQuestion
    extra = 0
    fields = (
        "number", "grade", "strand", "sub_strand", "bloom_skill",
        "description", "expected_answer"
    )
    readonly_fields = ("number",)


@admin.register(Exam)
class ExamAdmin(admin.ModelAdmin):
    list_display = (
        "code", "classroom", "teacher", "status", "is_published", "generation_config", "generation_error"
    )
    list_filter = ("status", "is_published", "classroom__name", "teacher__user__username")
    search_fields = ("code", "classroom__name", "teacher__user__username")
    readonly_fields = ("created_at", "updated_at", "duration_min")
    inlines = [ExamQuestionInline]


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "exam", "number", "grade", "strand", "sub_strand", "bloom_skill"
    )
    list_filter = ("grade", "strand", "sub_strand", "bloom_skill")
    search_fields = ("description", "expected_answer", "strand", "sub_strand")
    readonly_fields = ("exam",)


@admin.register(ExamQuestionAnalysis)
class ExamQuestionAnalysisAdmin(admin.ModelAdmin):
    list_display = (
        "exam", "question_count", "created_at", "updated_at"
    )
    readonly_fields = (
        "exam", "question_count", "grade_distribution",
        "bloom_skill_distribution", "strand_distribution",
        "sub_strand_distribution", "created_at", "updated_at"
    )