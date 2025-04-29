from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator
from utils import generate_unique_code


class Teacher(models.Model):
    name = models.CharField(max_length=255)
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    phone_no = models.CharField(max_length=15)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.user.first_name or self.user.email


class Class(models.Model):
    name = models.CharField(max_length=255)
    school_name = models.CharField(max_length=255)
    school_address = models.CharField(max_length=255)
    grade = models.IntegerField(
        validators=[
            MinValueValidator(7),
            MaxValueValidator(9)
        ]
    )
    code = models.CharField(max_length=6, unique=True, default=generate_unique_code)
    teacher = models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='classes')

    class Meta:
        unique_together = ('name', 'grade', 'teacher')

    def __str__(self):
        return f"{self.name} - G{self.grade}"


class LessonTime(models.Model):
    WEEKDAYS = [
        ("Monday", "Monday"),
        ("Tuesday", "Tuesday"),
        ("Wednesday", "Wednesday"),
        ("Thursday", "Thursday"),
        ("Friday", "Friday"),
    ]

    class_ref = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='lesson_times')
    day = models.CharField(max_length=10, choices=WEEKDAYS)
    time = models.TimeField()

    def __str__(self):
        return f"{self.class_ref.name} on {self.day} at {self.time.strftime('%I:%M %p')}"
    

class Student(models.Model):
    name = models.CharField(max_length=255)
    code = models.CharField(max_length=6, unique=True, default=generate_unique_code)
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    classroom = models.ForeignKey(Class, on_delete=models.CASCADE, related_name='students')

    class Meta:
        unique_together = ('name', 'classroom')

    def __str__(self):
        return self.name


class TermScore(models.Model):
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name='term_scores')
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

    class Meta:
        unique_together = ('student', 'grade', 'term')

    def __str__(self):
        return f"{self.student.name} - G{self.grade} T{self.term}: {self.score}"