# exam/serializers.py
import json

from rest_framework import serializers
from .models import *


class ExamQuestionAnalysisSerializer(serializers.ModelSerializer):
    grade_distribution = serializers.SerializerMethodField()
    bloom_skill_distribution = serializers.SerializerMethodField()
    strand_distribution = serializers.SerializerMethodField()
    sub_strand_distribution = serializers.SerializerMethodField()

    class Meta:
        model = ExamQuestionAnalysis
        fields = [
            'question_count',
            'grade_distribution',
            'bloom_skill_distribution',
            'strand_distribution',
            'sub_strand_distribution',
        ]

    def get_grade_distribution(self, obj):
        return _safe_json_parse(obj.grade_distribution)

    def get_bloom_skill_distribution(self, obj):
        return _safe_json_parse(obj.bloom_skill_distribution)

    def get_strand_distribution(self, obj):
        return _safe_json_parse(obj.strand_distribution)

    def get_sub_strand_distribution(self, obj):
        return _safe_json_parse(obj.sub_strand_distribution)


def _safe_json_parse(raw):
    try:
        return json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return []


class ExamSerializer(serializers.ModelSerializer):
    classroom_id = serializers.IntegerField(source='classroom.id')
    classroom_name = serializers.CharField(source='classroom.name')
    analysis = ExamQuestionAnalysisSerializer()
    student_id = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id', 'start_date_time', 'end_date_time', 'status', 'is_published',
            'code', 'duration_min', 'generation_error',
            'classroom_id', 'classroom_name', 'analysis', 'created_at',
            'student_id'  # << shows only when relevant
        ]

    def get_student_id(self, exam):
        student_map = self.context.get("student_exam_sessions", {})
        return student_map.get(exam.id)


class ExamQuestionSerializer(serializers.ModelSerializer):
    bloom_skill_options = serializers.SerializerMethodField()
    question_options = serializers.SerializerMethodField()
    answer_options = serializers.SerializerMethodField()

    class Meta:
        model = ExamQuestion
        fields = [
            'id', 'number', 'grade', 'strand', 'sub_strand', 'bloom_skill',
            'description', 'expected_answer',
            'bloom_skill_options', 'question_options', 'answer_options'
        ]

    def get_bloom_skill_options(self, obj):
        return _safe_parse_json(obj.bloom_skill_options)

    def get_question_options(self, obj):
        return _safe_parse_json(obj.question_options)

    def get_answer_options(self, obj):
        return _safe_parse_json(obj.answer_options)


def _safe_parse_json(raw):
    try:
        return json.loads(raw) if raw else []
    except json.JSONDecodeError:
        return []


class StudentExamSessionSerializer(serializers.ModelSerializer):
    exam_id = serializers.IntegerField(source='exam.id')
    student_id = serializers.ReadOnlyField(source='student.id')
    student_name = serializers.ReadOnlyField(source='student.name')

    class Meta:
        model = StudentExamSession
        fields = ['id', 'is_late_submission', 'start_date_time', 'status',
                  'end_date_time', 'duration_min', 'exam_id', 'student_id', 
                  'student_name']


class StudentExamSessionAnswerSerializer(serializers.ModelSerializer):
    question_id = serializers.IntegerField(source='question.id')
    question_number = serializers.ReadOnlyField(source='question.number')
    question_description = serializers.ReadOnlyField(
        source='question.description')
    strand = serializers.ReadOnlyField(source='question.strand')
    grade = serializers.IntegerField(source='question.grade')

    class Meta:
        model = StudentExamSessionAnswer
        fields = ['id', 'question_id', 'question_number',
                  'question_description', 'description', 'strand', 'grade']


class FullStudentExamSessionAnswerSerializer(StudentExamSessionAnswerSerializer):
    sub_strand = serializers.ReadOnlyField(source='question.sub_strand')
    bloom_skill = serializers.ReadOnlyField(source='question.bloom_skill')
    expected_answer = serializers.ReadOnlyField(
        source='question.expected_answer')

    class Meta(StudentExamSessionAnswerSerializer.Meta):
        fields = StudentExamSessionAnswerSerializer.Meta.fields + [
            'sub_strand', 'bloom_skill', 'expected_answer', 'score',
            'expectation_level', 'ai_score', 'tr_score',
        ]

from rest_framework import serializers

class ClassExamPerformanceSerializer(serializers.ModelSerializer):
    # Parse fields stored as JSON/text into Python objects
    expectation_level_distribution = serializers.SerializerMethodField()
    score_distribution = serializers.SerializerMethodField()
    score_variance = serializers.SerializerMethodField()
    bloom_skill_scores = serializers.SerializerMethodField()
    general_insights = serializers.SerializerMethodField()
    grade_scores = serializers.SerializerMethodField()
    strand_analysis = serializers.SerializerMethodField()
    strand_student_mastery = serializers.SerializerMethodField()
    flagged_sub_strands = serializers.SerializerMethodField()

    class Meta:
        model = ClassExamPerformance
        fields = [
            "id",
            "exam",
            "avg_score",
            "avg_expectation_level",
            "student_count",
            "expectation_level_distribution",
            "score_distribution",
            "score_variance",
            "bloom_skill_scores",
            "general_insights",
            "grade_scores",
            "strand_analysis",
            "strand_student_mastery",
            "flagged_sub_strands",
            "created_at",
            "updated_at",
        ]

    def get_expectation_level_distribution(self, obj):
        try:
            return json.loads(obj.expectation_level_distribution or "[]")
        except Exception:
            return []

    def get_score_distribution(self, obj):
        try:
            return json.loads(obj.score_distribution or "[]")
        except Exception:
            return []

    def get_score_variance(self, obj):
        try:
            return json.loads(obj.score_variance or "{}")
        except Exception:
            return {}

    def get_bloom_skill_scores(self, obj):
        try:
            return json.loads(obj.bloom_skill_scores or "[]")
        except Exception:
            return []

    def get_general_insights(self, obj):
        try:
            return json.loads(obj.general_insights or "[]")
        except Exception:
            return []

    def get_grade_scores(self, obj):
        try:
            return json.loads(obj.grade_scores or "[]")
        except Exception:
            return []

    def get_strand_analysis(self, obj):
        try:
            return json.loads(obj.strand_analysis or "[]")
        except Exception:
            return []

    def get_strand_student_mastery(self, obj):
        try:
            return json.loads(obj.strand_student_mastery or "[]")
        except Exception:
            return []

    def get_flagged_sub_strands(self, obj):
        try:
            return json.loads(obj.flagged_sub_strands or "[]")
        except Exception:
            return []