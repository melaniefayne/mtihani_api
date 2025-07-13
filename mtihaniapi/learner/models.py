from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from learner.utils import EXPECTATION_LEVELS, STUDENT_STATUSES, WEEKDAYS, generate_unique_code, get_avg_expectation_level


class Teacher(models.Model):
    name = models.CharField(max_length=255)
    phone_no = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    user = models.OneToOneField(User, on_delete=models.CASCADE)

    def __str__(self):
        return self.user.first_name or self.user.email


class Classroom(models.Model):
    name = models.CharField(max_length=255)
    subject = models.CharField(max_length=255)
    school_name = models.CharField(max_length=255)
    school_address = models.CharField(max_length=255)
    grade = models.IntegerField(
        validators=[
            MinValueValidator(7),
            MaxValueValidator(9)
        ]
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, related_name='classrooms')

    class Meta:
        unique_together = ('name', 'grade', 'teacher')

    def __str__(self):
        return f"{self.name} - G{self.grade}"


class LessonTime(models.Model):
    day = models.CharField(max_length=10, choices=WEEKDAYS)
    time = models.TimeField()
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name='lesson_times')

    class Meta:
        unique_together = ('classroom', 'day', 'time')

    def __str__(self):
        return f"{self.classroom.name} on {self.day} at {self.time.strftime('%I:%M %p')}"


class Student(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=6, unique=True,
                            default=generate_unique_code)
    user = models.ForeignKey(User, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name="students")
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name='students')
    status = models.CharField(
        max_length=15, choices=STUDENT_STATUSES, default="Inactive")
    avg_score = models.FloatField(default=0.0)
    avg_expectation_level = models.CharField(max_length=100, blank=True)

    class Meta:
        unique_together = ('classroom', 'code')

    def save(self, *args, **kwargs):
        from utils import get_avg_expectation_level
        self.avg_expectation_level = get_avg_expectation_level(self.avg_score)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.name} - {self.classroom.name}"


class TermScore(models.Model):
    grade = models.IntegerField(
        validators=[
            MinValueValidator(7),
            MaxValueValidator(9)
        ]
    )
    term = models.IntegerField(
        validators=[
            MinValueValidator(1),
            MaxValueValidator(3)
        ]
    )
    score = models.FloatField()
    expectation_level = models.CharField(
        max_length=100, choices=EXPECTATION_LEVELS, blank=True)
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='term_scores')

    class Meta:
        unique_together = ('student', 'grade', 'term')

    def save(self, *args, **kwargs):
        self.expectation_level = get_avg_expectation_level(self.score)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.student.name} - G{self.grade} T{self.term}: {self.score}"
