from django.contrib import admin
from .models import (
    Teacher, Classroom, LessonTime,
    ClassroomStudent, TermScore
)


@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_no', 'user', 'created_at')
    search_fields = ('name', 'user__email', 'user__first_name')


class LessonTimeInline(admin.TabularInline):
    model = LessonTime
    extra = 1


@admin.register(Classroom)
class ClassroomAdmin(admin.ModelAdmin):
    list_display = ('name', 'grade', 'subject', 'school_name', 'teacher', 'updated_at')
    list_filter = ('grade', 'teacher', 'subject')
    search_fields = ('name', 'school_name', 'teacher__name')
    inlines = [LessonTimeInline]


class TermScoreInline(admin.TabularInline):
    model = TermScore
    extra = 1
    readonly_fields = ('expectation_level',)


@admin.register(ClassroomStudent)
class ClassroomStudentAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'user_linked', 'classrooms_list', 'avg_score')
    search_fields = ('name', 'code', 'user__email')
    list_filter = ('classroom', 'avg_expectation_level')
    inlines = [TermScoreInline]

    def user_linked(self, obj):
        return obj.user.email if obj.user else '—'
    user_linked.short_description = 'User'

    def classrooms_list(self, obj):
        return ", ".join([c.name for c in obj.classroom.all()])
    classrooms_list.short_description = 'Classrooms'


@admin.register(TermScore)
class TermScoreAdmin(admin.ModelAdmin):
    list_display = ('classroom_student', 'grade', 'term', 'score', 'expectation_level')
    list_filter = ('grade', 'term', 'expectation_level')
    search_fields = ('classroom_student__name',)
    readonly_fields = ('expectation_level',)