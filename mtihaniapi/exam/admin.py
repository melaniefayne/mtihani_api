from django.contrib import admin
from django.contrib.admin import SimpleListFilter
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
        "exam", "question_count", "untested_strands", "updated_at"
    )
    readonly_fields = (
        "exam", "question_count", "grade_distribution",
        "bloom_skill_distribution", "strand_distribution",
        "sub_strand_distribution", "untested_strands", "created_at", "updated_at"
    )


@admin.register(StudentExamSession)
class StudentExamSessionAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'exam', 'student', 'status',
        'start_date_time', 'end_date_time',
        'duration_min', 'is_late_submission'
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


class StudentPerformanceExamFilter(SimpleListFilter):
    title = "Exam"
    parameter_name = "exam"

    def lookups(self, request, model_admin):
        exams = Exam.objects.all()
        return [(exam.id, f"{exam.code} (ID {exam.id})") for exam in exams]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(session__exam__id=self.value())
        return queryset


@admin.register(StudentExamSessionPerformance)
class StudentExamSessionPerformanceAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "avg_score",
        "avg_expectation_level",
        "class_avg_difference",
        "completion_rate",
    )

    list_filter = ("avg_expectation_level", StudentPerformanceExamFilter)
    search_fields = ("session__student__name", "session__exam__code")

    readonly_fields = (
        "bloom_skill_scores",
        "grade_scores",
        "strand_scores",
        "sub_strand_scores",
        "best_5_question_ids",
        "worst_5_question_ids",
        "created_at",
        "updated_at"
    )

    fieldsets = (
        (None, {
            "fields": (
                "session",
                "avg_score",
                "avg_expectation_level",
                "questions_answered",
                "questions_unanswered",
                "completion_rate",
            )
        }),
        ("Score Distributions", {
            "fields": (
                "bloom_skill_scores",
                "grade_scores",
                "strand_scores",
                "sub_strand_scores",
            ),
            "classes": ("collapse",)
        }),
        ("Question Insights", {
            "fields": (
                "best_5_question_ids",
                "worst_5_question_ids",
            ),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            ),
            "classes": ("collapse",)
        }),
    )


@admin.register(ClassExamPerformance)
class ClassExamPerformanceAdmin(admin.ModelAdmin):
    list_display = ("id", "exam", "avg_score",
                    "avg_expectation_level", "updated_at")
    readonly_fields = (
        "exam",
        "avg_score",
        "avg_expectation_level",
        "expectation_level_distribution",
        "bloom_skill_scores",
        "grade_scores",
        "strand_scores",
        "sub_strand_scores",
        "weak_bloom_skills",
        "strong_bloom_skills",
        "weak_sub_strands",
        "strong_sub_strands",
        "score_distribution",
        "created_at",
        "updated_at",
    )
    search_fields = ("exam__code",)


@admin.register(ExamQuestionPerformance)
class ExamQuestionPerformanceAdmin(admin.ModelAdmin):
    list_display = ("id", "question", "avg_score", "avg_expectation_level", "updated_at")
    list_filter = ("question__exam",)
    search_fields = ("question__description", "question__exam__code")

    readonly_fields = (
        "question",
        "avg_score",
        "score_distribution",
        "answers_by_level",
        "created_at",
        "updated_at"
    )

    fieldsets = (
        (None, {
            "fields": ("question", "avg_score")
        }),
        ("Distributions", {
            "fields": ("score_distribution",),
            "classes": ("collapse",)
        }),
        ("Answers by Expectation Level", {
            "fields": ("answers_by_level",),
            "classes": ("collapse",)
        }),
        ("Timestamps", {
            "fields": ("created_at", "updated_at"),
            "classes": ("collapse",)
        }),
    )