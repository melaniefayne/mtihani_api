from django.db import models

from learner.models import Classroom, ClassroomStudent, Teacher

class Exam(models.Model):
    class_obj = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='exams')
    teacher =  models.ForeignKey(Teacher, on_delete=models.SET_NULL, null=True, related_name='exams')
    grade = models.IntegerField()
    code = models.CharField(max_length=50, unique=True)
    status = models.CharField(max_length=50)
    duration_min = models.IntegerField()
    start_date_time = models.DateTimeField()
    end_date_time = models.DateTimeField()
    is_published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ExamQuestion(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE, related_name='questions')
    grade = models.IntegerField()
    strand_id = models.IntegerField()
    skill_id = models.IntegerField()
    skill_name = models.CharField(max_length=255)
    strand_name = models.CharField(max_length=255)
    sub_strand_id = models.IntegerField()
    sub_strand_name = models.CharField(max_length=255)
    description = models.TextField()
    expected_answer = models.TextField()
    tr_description = models.TextField(blank=True, null=True)
    tr_expected_answer = models.TextField(blank=True, null=True)
    difficulty_level = models.CharField(max_length=50)

class ExamQuestionAnalysis(models.Model):
    exam = models.OneToOneField('Exam', on_delete=models.CASCADE, related_name='analysis')
    question_count = models.IntegerField()
    grade_distribution = models.JSONField(default=list)  # List of {id, name, score, expectation_level, count}
    bloom_skill_distribution = models.JSONField(default=list)
    sub_strand_distribution = models.JSONField(default=list)
    difficulty_distribution = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class StudentExamSession(models.Model):
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    start_date_time = models.DateTimeField()
    end_date_time = models.DateTimeField(null=True, blank=True)
    duration_min = models.IntegerField(null=True, blank=True)
    avg_score = models.FloatField(null=True, blank=True)
    expectation_level = models.CharField(max_length=100, blank=True, null=True)
    student = models.ForeignKey(ClassroomStudent, on_delete=models.CASCADE, related_name='student_exam_session')

class StudentExamSessionAnswer(models.Model):
    session = models.ForeignKey(StudentExamSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE)
    description = models.TextField()
    score = models.FloatField(null=True, blank=True)
    tr_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class StudentExamSessionPerformance(models.Model):
    session = models.OneToOneField(StudentExamSession, on_delete=models.CASCADE, related_name='student_exam_session_performance')
    avg_score = models.FloatField()
    avg_expectation_level = models.CharField(max_length=100, blank=True)
    bloom_skill_scores = models.JSONField(default=list)  # list of score dicts
    strand_scores = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def save(self, *args, **kwargs):
        from utils import get_expectation_level
        self.avg_expectation_level = get_expectation_level(self.avg_score)
        super().save(*args, **kwargs)

class ClassExamPerformance(models.Model):
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE)
    avg_score = models.FloatField()
    avg_expectation_level = models.CharField(max_length=100, blank=True)
    bloom_skill_scores = models.JSONField(default=list)
    strand_scores = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='class_exam_performance')

    def save(self, *args, **kwargs):
        from utils import get_expectation_level
        self.avg_expectation_level = get_expectation_level(self.avg_score)
        super().save(*args, **kwargs)
