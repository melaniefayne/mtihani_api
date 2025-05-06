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

    class Meta:
        model = Exam
        fields = [
            'id', 'start_date_time', 'end_date_time', 'status', 'is_published',
            'code', 'duration_min', 'generation_error',
            'classroom_id', 'classroom_name', 'analysis', 'created_at'
        ]


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
