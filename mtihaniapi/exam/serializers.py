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


class StudentExamSessionSerializer(serializers.ModelSerializer):
    exam_id = serializers.IntegerField(source='exam.id')
    student_id = serializers.ReadOnlyField(source='student.id')
    student_name = serializers.ReadOnlyField(source='student.name')
    avg_score = serializers.SerializerMethodField()
    expectation_level = serializers.SerializerMethodField()

    class Meta:
        model = StudentExamSession
        fields = ['id', 'is_late_submission', 'start_date_time', 'status',
                  'end_date_time', 'duration_min', 'exam_id', 'student_id',
                  'student_name', "avg_score", "expectation_level"]

    def get_avg_score(self, obj):
        if obj.exam.status == "Complete" and hasattr(obj, 'student_exam_session_performance'):
            return obj.student_exam_session_performance.avg_score
        return None

    def get_expectation_level(self, obj):
        if obj.exam.status == "Complete" and hasattr(obj, 'student_exam_session_performance'):
            return obj.student_exam_session_performance.avg_expectation_level
        return None


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


class ClassExamPerformanceSerializer(serializers.ModelSerializer):
    # Declare all fields as SerializerMethodField for JSON parsing
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

    _json_field_defaults = {
        "expectation_level_distribution": [],
        "score_distribution": [],
        "score_variance": {},
        "bloom_skill_scores": [],
        "general_insights": [],
        "grade_scores": [],
        "strand_analysis": [],
        "strand_student_mastery": [],
        "flagged_sub_strands": [],
    }

    def _parse_json_field(self, obj, field):
        raw = getattr(obj, field, None)
        default = self._json_field_defaults.get(field, None)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default

    def get_expectation_level_distribution(self, obj):
        return self._parse_json_field(obj, "expectation_level_distribution")

    def get_score_distribution(self, obj):
        return self._parse_json_field(obj, "score_distribution")

    def get_score_variance(self, obj):
        return self._parse_json_field(obj, "score_variance")

    def get_bloom_skill_scores(self, obj):
        return self._parse_json_field(obj, "bloom_skill_scores")

    def get_general_insights(self, obj):
        return self._parse_json_field(obj, "general_insights")

    def get_grade_scores(self, obj):
        return self._parse_json_field(obj, "grade_scores")

    def get_strand_analysis(self, obj):
        return self._parse_json_field(obj, "strand_analysis")

    def get_strand_student_mastery(self, obj):
        return self._parse_json_field(obj, "strand_student_mastery")

    def get_flagged_sub_strands(self, obj):
        return self._parse_json_field(obj, "flagged_sub_strands")


class StudentExamSessionPerformanceSerializer(serializers.ModelSerializer):
    exam_id = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()

    bloom_skill_scores = serializers.SerializerMethodField()
    grade_scores = serializers.SerializerMethodField()
    strand_scores = serializers.SerializerMethodField()
    best_5_question_ids = serializers.SerializerMethodField()
    worst_5_question_ids = serializers.SerializerMethodField()

    class Meta:
        model = StudentExamSessionPerformance
        fields = [
            'id',
            'session',
            'exam_id',
            'student_id',
            'student_name',
            'avg_score',
            'avg_expectation_level',
            'class_avg_difference',
            'bloom_skill_scores',
            'grade_scores',
            'strand_scores',
            'questions_answered',
            'questions_unanswered',
            'completion_rate',
            'best_5_question_ids',
            'worst_5_question_ids',
            'created_at',
            'updated_at',
        ]

    # Related fields
    def get_exam_id(self, obj):
        return obj.session.exam.id if obj.session and obj.session.exam else None

    def get_student_id(self, obj):
        return obj.session.student.id if obj.session and obj.session.student else None

    def get_student_name(self, obj):
        return obj.session.student.name if obj.session and obj.session.student else None

    # JSON fields
    def _parse_json_field(self, s):
        import json
        if not s:
            return []
        try:
            return json.loads(s)
        except Exception:
            return []

    def get_bloom_skill_scores(self, obj):
        return self._parse_json_field(obj.bloom_skill_scores)

    def get_grade_scores(self, obj):
        return self._parse_json_field(obj.grade_scores)

    def get_strand_scores(self, obj):
        return self._parse_json_field(obj.strand_scores)

    def get_best_5_question_ids(self, obj):
        return self._parse_json_field(obj.best_5_question_ids)

    def get_worst_5_question_ids(self, obj):
        return self._parse_json_field(obj.worst_5_question_ids)


class StudentExamSessionPerformanceMiniSerializer(serializers.ModelSerializer):
    exam_id = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentExamSessionPerformance
        fields = [
            "id", "exam_id", "student_id", "student_name", "avg_score", "avg_expectation_level"
        ]

    def get_exam_id(self, obj):
        return obj.session.exam.id if obj.session and obj.session.exam else None

    def get_student_id(self, obj):
        return obj.session.student.id if obj.session and obj.session.student else None

    def get_student_name(self, obj):
        return obj.session.student.name if obj.session and obj.session.student else None


class ExamPerformanceClusterSerializer(serializers.ModelSerializer):
    student_sessions = serializers.SerializerMethodField()
    score_variance = serializers.SerializerMethodField()
    bloom_skill_scores = serializers.SerializerMethodField()
    strand_scores = serializers.SerializerMethodField()
    top_best_question_ids = serializers.SerializerMethodField()
    top_worst_question_ids = serializers.SerializerMethodField()

    class Meta:
        model = ExamPerformanceCluster
        fields = [
            "id",
            "exam",
            "cluster_label",
            "cluster_size",
            "student_sessions",
            "avg_score",
            "avg_expectation_level",
            "score_variance",
            "bloom_skill_scores",
            "strand_scores",
            "top_best_question_ids",
            "top_worst_question_ids",
            "insight",
            "created_at",
        ]

    # Nested performances
    def get_student_sessions(self, obj):
        import json
        ids = json.loads(obj.student_session_ids or "[]")
        performances = StudentExamSessionPerformance.objects.filter(id__in=ids)
        return StudentExamSessionPerformanceMiniSerializer(performances, many=True).data

    # All JSON fields (reuse from earlier style)
    def _parse_json_field(self, obj, field, default):
        import json
        raw = getattr(obj, field, None)
        if not raw:
            return default
        try:
            return json.loads(raw)
        except Exception:
            return default

    def get_score_variance(self, obj):
        return self._parse_json_field(obj, "score_variance", {})

    def get_bloom_skill_scores(self, obj):
        return self._parse_json_field(obj, "bloom_skill_scores", [])

    def get_strand_scores(self, obj):
        return self._parse_json_field(obj, "strand_scores", [])

    def get_top_best_question_ids(self, obj):
        return self._parse_json_field(obj, "top_best_question_ids", [])

    def get_top_worst_question_ids(self, obj):
        return self._parse_json_field(obj, "top_worst_question_ids", [])
