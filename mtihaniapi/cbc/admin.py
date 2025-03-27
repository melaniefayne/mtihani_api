from django.contrib import admin
from .models import Strand, SubStrand, Skill, AssessmentRubric, BloomSkill

@admin.register(Strand)
class StrandAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "grade")
    search_fields = ("name",)
    list_filter = ("grade",)
    ordering = ("number",)


@admin.register(SubStrand)
class SubStrandAdmin(admin.ModelAdmin):
    list_display = ("number", "name", "strand", "learning_outcomes", "key_inquiries")
    search_fields = ("name",)
    list_filter = ("strand",)
    ordering = ("number",)
    
@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ("sub_strand", "skill")
    search_fields = ("skill",)
    list_filter = ("sub_strand",)
    ordering = ("sub_strand",)


@admin.register(AssessmentRubric)
class AssessmentRubricAdmin(admin.ModelAdmin):
    list_display = ("skill", "expectation", "description")
    search_fields = ("skill",)
    list_filter = ("expectation",)
    ordering = ("id",)


@admin.register(BloomSkill)
class BloomSkillAdmin(admin.ModelAdmin):
    list_display = ("name", "description", "examples")
    search_fields = ("name",)
