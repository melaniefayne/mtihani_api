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
        "id", "code", "classroom", "teacher", "status", "is_published", "generation_config", "generation_error"
    )
    list_filter = ("status", "is_published", "classroom__name",
                   "teacher__user__username")
    search_fields = ("code", "classroom__name", "teacher__user__username")
    readonly_fields = ("created_at", "updated_at", "duration_min")
    inlines = [ExamQuestionInline]


@admin.register(ExamQuestion)
class ExamQuestionAdmin(admin.ModelAdmin):
    list_display = (
        "id", "exam", "number", "grade", "strand", "sub_strand", "bloom_skill"
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


@admin.register(StudentExamSession)
class StudentExamSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'exam', 'student', 'status',
        'start_date_time', 'end_date_time',
        'duration_min', 'avg_score', 'expectation_level',
        'is_late_submission'
    ]
    list_filter = ['status', 'is_late_submission', 'exam__classroom']
    search_fields = ['student__name', 'exam__code',
                     'exam__teacher__user__username']
    readonly_fields = ['start_date_time', 'end_date_time', 'duration_min']
    ordering = ['-start_date_time']


@admin.register(StudentExamSessionAnswer)
class StudentExamSessionAnswerAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'question', 'short_description', 'score', 'expectation_level', 'ai_score', 'tr_score',
        'created_at', 'updated_at'
    ]
    list_filter = ['score', 'tr_score']
    search_fields = ['session__student__name', 'question__description']
    ordering = ['question__number']

    def short_description(self, obj):
        return (obj.description[:50] + "...") if obj.description and len(obj.description) > 50 else obj.description
    short_description.short_description = "Answer Preview"
