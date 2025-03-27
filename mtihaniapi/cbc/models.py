from django.db import models
from django.contrib.postgres.fields import JSONField

class Strand(models.Model):
    name = models.CharField(max_length=255)
    number = models.FloatField()
    grade = models.IntegerField()

    class Meta:
        unique_together = ("grade", "number")

    def __str__(self):
        return f"{self.name} (G{self.grade})"


class SubStrand(models.Model):
    strand = models.ForeignKey(Strand, on_delete=models.CASCADE, related_name="sub_strands")
    name = models.CharField(max_length=255)
    number = models.FloatField()
    lesson_count = models.IntegerField()
    descriptions = models.JSONField()
    learning_outcomes = models.JSONField()
    learning_experiences = models.JSONField()
    key_inquiries = models.JSONField()
    core_competencies = models.JSONField()
    values = models.JSONField()
    pertinent_issues = models.JSONField()
    other_learning_areas = models.JSONField()
    learning_materials = models.JSONField()
    non_formal_activities = models.JSONField()

    class Meta:
        unique_together = ("strand", "number")

    def __str__(self):
        return f"{self.strand}: {self.name}"


class Skill(models.Model):
    sub_strand = models.ForeignKey(SubStrand, on_delete=models.CASCADE, related_name="skills")
    skill = models.CharField(max_length=255)

    class Meta:
        unique_together = ("sub_strand", "skill")

    def __str__(self):
        return self.skill


class AssessmentRubric(models.Model):
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE, related_name="rubrics")
    expectation = models.CharField(max_length=50)
    description = models.TextField(max_length=255)

    class Meta:
        unique_together = ("skill", "expectation")

    def __str__(self):
        return f"{self.expectation} – {self.description}"


class BloomSkill(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    examples =  models.JSONField()

    def __str__(self):
        return self.name
