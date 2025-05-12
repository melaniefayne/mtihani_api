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
    student_session_id = serializers.SerializerMethodField()

    class Meta:
        model = Exam
        fields = [
            'id', 'start_date_time', 'end_date_time', 'status', 'is_published',
            'code', 'duration_min', 'generation_error',
            'classroom_id', 'classroom_name', 'analysis', 'created_at',
            'student_session_id'  # << only shows for students
        ]

    def get_student_session_id(self, exam):
        student_exam_sessions = self.context.get("student_exam_sessions", {})
        return student_exam_sessions.get(exam.id)


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
                  'end_date_time', 'duration_min', 'avg_score', 'expectation_level',
                  'exam_id', 'student_id', 'student_name']


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
                  'question_description', 'description', 'score', 'tr_score',
                  'strand', 'grade']
