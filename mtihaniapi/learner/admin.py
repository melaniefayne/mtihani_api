from django.contrib import admin
from .models import Teacher, Class, Student, TermScore, LessonTime

@admin.register(Teacher)
class TeacherAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone_no", "created_at", "updated_at")
    search_fields = ("user__email", "user__first_name", "phone_no")
    ordering = ("-created_at",)


@admin.register(Class)
class ClassAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "grade", "school_name", "code", "teacher")
    search_fields = ("name", "school_name", "teacher__user__email")
    list_filter = ("grade", "school_name")
    ordering = ("grade", "name")


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "code", "classroom", "user")
    search_fields = ("name", "code", "classroom__name", "user__email")
    list_filter = ("classroom__grade",)
    ordering = ("name",)


@admin.register(TermScore)
class TermScoreAdmin(admin.ModelAdmin):
    list_display = ("student", "grade", "term", "score")
    search_fields = ("student__name", "student__code")
    list_filter = ("grade", "term")
    ordering = ("student", "grade", "term")


@admin.register(LessonTime)
class LessonTimeAdmin(admin.ModelAdmin):
    list_display = ("class_ref", "day", "time")
    list_filter = ("day",)
    search_fields = ("class_ref__name",)
    ordering = ("class_ref", "day", "time")
