from django.db import models
from utils import EXAM_STATUSES, EXPECTATION_LEVELS, generate_unique_code, get_answer_expectation_level, get_avg_expectation_level
from learner.models import Classroom, Student, Teacher
from django.utils import timezone


class Exam(models.Model):

    start_date_time = models.DateTimeField()
    end_date_time = models.DateTimeField()
    status = models.CharField(
        max_length=25, choices=EXAM_STATUSES, default="Generating")
    code = models.CharField(max_length=50, unique=True,
                            default=generate_unique_code)
    duration_min = models.IntegerField(blank=True)
    is_published = models.BooleanField(default=False)
    is_grading = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    generation_config = models.TextField(blank=True, null=True)
    generation_error = models.TextField(null=True, blank=True)
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name='exams')
    teacher = models.ForeignKey(
        Teacher, on_delete=models.SET_NULL, null=True, related_name='exams')

    def save(self, *args, **kwargs):
        if self.start_date_time and self.end_date_time:
            delta = self.end_date_time - self.start_date_time
            self.duration_min = int(delta.total_seconds() // 60)
        super().save(*args, **kwargs)

    def refresh_status(self):
        now = timezone.now()

        if now < self.start_date_time:
            self.status = "Upcoming"
        elif self.start_date_time <= now <= self.end_date_time:
            self.status = "Ongoing"
        elif now > self.end_date_time:
            self.status = "Grading"
        self.save(update_fields=["status"])

    def update_to_grading(self):
        self.status = "Grading"
        self.is_grading = True
        self.save(update_fields=["status", "is_grading"])


class ExamQuestion(models.Model):
    number = models.IntegerField()
    grade = models.IntegerField()
    strand = models.CharField(max_length=100)
    sub_strand = models.CharField(max_length=100)
    bloom_skill = models.CharField(max_length=100)
    description = models.TextField()
    expected_answer = models.TextField()
    bloom_skill_options = models.TextField(blank=True)
    question_options = models.TextField(blank=True)
    answer_options = models.TextField(blank=True)
    tr_description = models.TextField(blank=True, null=True)
    tr_expected_answer = models.TextField(blank=True, null=True)
    exam = models.ForeignKey(
        Exam, on_delete=models.CASCADE, related_name='questions')


class ExamQuestionAnalysis(models.Model):
    question_count = models.IntegerField()
    grade_distribution = models.TextField(blank=True)
    bloom_skill_distribution = models.TextField(blank=True)
    strand_distribution = models.TextField(blank=True)
    sub_strand_distribution = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    exam = models.OneToOneField(
        Exam, on_delete=models.CASCADE, related_name='analysis')


class StudentExamSession(models.Model):
    status = models.CharField(
        max_length=15, choices=EXAM_STATUSES, default="Upcoming")
    is_late_submission = models.BooleanField(default=False)
    start_date_time = models.DateTimeField(null=True)
    end_date_time = models.DateTimeField(null=True, blank=True)
    duration_min = models.IntegerField(null=True, blank=True)
    avg_score = models.FloatField(null=True, blank=True)
    expectation_level = models.CharField(max_length=100, blank=True, null=True)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    student = models.ForeignKey(
        Student, on_delete=models.CASCADE, related_name='student_exam_session')

    class Meta:
        unique_together = ('student', 'exam')

    def save(self, *args, **kwargs):
        if self.start_date_time and self.end_date_time:
            delta = self.end_date_time - self.start_date_time
            self.duration_min = int(delta.total_seconds() // 60)

        if self.end_date_time and self.exam.end_date_time:
            self.is_late_submission = self.end_date_time > self.exam.end_date_time

        super().save(*args, **kwargs)


class StudentExamSessionAnswer(models.Model):
    session = models.ForeignKey(
        StudentExamSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE)
    description = models.TextField()
    score = models.FloatField(null=True, blank=True)
    expectation_level = models.CharField(
        max_length=100, choices=EXPECTATION_LEVELS, blank=True, null=True)
    ai_score = models.FloatField(null=True, blank=True)
    tr_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.expectation_level = get_answer_expectation_level(
            self.score)
        super().save(*args, **kwargs)


class StudentExamSessionPerformance(models.Model):
    session = models.OneToOneField(
        StudentExamSession, on_delete=models.CASCADE, related_name='student_exam_session_performance')
    avg_score = models.FloatField()
    avg_expectation_level = models.CharField(max_length=100, blank=True)
    bloom_skill_scores = models.TextField(blank=True)
    strand_scores = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.avg_expectation_level = get_avg_expectation_level(self.avg_score)
        super().save(*args, **kwargs)


class ClassExamPerformance(models.Model):
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE)
    avg_score = models.FloatField()
    avg_expectation_level = models.CharField(max_length=100, blank=True)
    bloom_skill_scores = models.TextField(blank=True)
    strand_scores = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    classroom = models.ForeignKey(
        Classroom, on_delete=models.CASCADE, related_name='class_exam_performance')

    def save(self, *args, **kwargs):
        self.avg_expectation_level = get_avg_expectation_level(self.avg_score)
        super().save(*args, **kwargs)
