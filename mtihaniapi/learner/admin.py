from django.contrib import admin
from learner.models import *

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_no', 'user', 'created_at')
    search_fields = ('name', 'user__email', 'user__first_name')


class LessonTimeInline(admin.TabularInline):
    model = LessonTime
    extra = 1


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'grade', 'subject', 'school_name', 'teacher', 'updated_at')
    list_filter = ('grade', 'teacher', 'subject')
    search_fields = ('name', 'school_name', 'teacher__name')
    inlines = [LessonTimeInline]


class TermScoreInline(admin.TabularInline):
    model = TermScore
    extra = 1
    readonly_fields = ('expectation_level',)


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'code', 'user_linked', 'classroom_name', 'avg_score')
    search_fields = ('name', 'code', 'user__email')
    list_filter = ('classroom', 'avg_expectation_level')
    inlines = [TermScoreInline]

    def user_linked(self, obj):
        return obj.user.email if obj.user else '—'
    user_linked.short_description = 'User'

    def classroom_name(self, obj):
        return obj.classroom.name if obj.classroom else '—'
    classroom_name.short_description = 'Classroom'


@admin.register(TermScore)
class TermScoreAdmin(admin.ModelAdmin):
    list_display = ('student', 'grade', 'term', 'score', 'expectation_level')
    list_filter = ('grade', 'term', 'expectation_level')
    search_fields = ('student__name',)
    readonly_fields = ('expectation_level',)