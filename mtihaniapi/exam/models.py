from django.db import models

# Create your models here.

class Classroom(models.Model):
    name = models.CharField(max_length=100)
    school_name = models.CharField(max_length=255, blank=True, null=True)
    school_address = models.TextField(blank=True, null=True)
    subject = models.CharField(max_length=100, blank=True, null=True)
    grade = models.IntegerField()
    code = models.CharField(max_length=50, unique=True)
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE, related_name='classes')


class Exam(models.Model):
    class_obj = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='exams')
    teacher = models.ForeignKey('Teacher', on_delete=models.CASCADE)
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
    student = models.ForeignKey('Student', on_delete=models.CASCADE)
    exam = models.ForeignKey(Exam, on_delete=models.CASCADE)
    start_date_time = models.DateTimeField()
    end_date_time = models.DateTimeField(null=True, blank=True)
    duration_min = models.IntegerField(null=True, blank=True)
    avg_score = models.FloatField(null=True, blank=True)
    expectation_level = models.CharField(max_length=100, blank=True, null=True)

class StudentExamSessionAnswer(models.Model):
    session = models.ForeignKey(StudentExamSession, on_delete=models.CASCADE, related_name='answers')
    question = models.ForeignKey(ExamQuestion, on_delete=models.CASCADE)
    description = models.TextField()
    score = models.FloatField(null=True, blank=True)
    tr_score = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class StudentExamSessionPerformance(models.Model):
    session = models.OneToOneField(StudentExamSession, on_delete=models.CASCADE)
    avg_score = models.FloatField()
    bloom_skill_scores = models.JSONField(default=list)  # list of score dicts
    strand_scores = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

class ClassExamPerformance(models.Model):
    classroom = models.ForeignKey(Classroom, on_delete=models.CASCADE, related_name='class_performance')
    exam = models.OneToOneField(Exam, on_delete=models.CASCADE)
    avg_score = models.FloatField()
    bloom_skill_scores = models.JSONField(default=list)
    strand_scores = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
