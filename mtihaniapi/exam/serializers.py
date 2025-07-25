# exam/serializers.py
import json

from rest_framework import serializers
from .models import *


class ExamQuestionAnalysisSerializer(serializers.ModelSerializer):
    grade_distribution = serializers.SerializerMethodField()
    bloom_skill_distribution = serializers.SerializerMethodField()
    strand_distribution = serializers.SerializerMethodField()
    sub_strand_distribution = serializers.SerializerMethodField()
    untested_strands = serializers.SerializerMethodField()

    class Meta:
        model = ExamQuestionAnalysis
        fields = [
            'question_count',
            'grade_distribution',
            'bloom_skill_distribution',
            'strand_distribution',
            'sub_strand_distribution',
            'untested_strands',
        ]

    def get_grade_distribution(self, obj):
        return _safe_json_parse(obj.grade_distribution)

    def get_bloom_skill_distribution(self, obj):
        return _safe_json_parse(obj.bloom_skill_distribution)

    def get_strand_distribution(self, obj):
        return _safe_json_parse(obj.strand_distribution)

    def get_sub_strand_distribution(self, obj):
        return _safe_json_parse(obj.sub_strand_distribution)

    def get_untested_strands(self, obj):
        return _safe_json_parse(obj.untested_strands)


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


JSON_FILED_DEFAULTS = {
    "expectation_level_distribution": [],
    "score_distribution": [],
    "score_variance": {},
    "bloom_skill_scores": [],
    "general_insights": [],
    "grade_scores": [],
    "strand_analysis": [],
    "strand_student_mastery": [],
    "flagged_sub_strands": [],
    "strand_scores": [],
    "best_5_answer_ids": [],
    "worst_5_answer_ids": [],
}


def parse_json_field(obj, field):
    raw = getattr(obj, field, None)
    default = JSON_FILED_DEFAULTS.get(field, None)
    if not raw:
        return default
    try:
        return json.loads(raw)
    except Exception:
        return default


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

    def get_expectation_level_distribution(self, obj):
        return parse_json_field(obj, "expectation_level_distribution")

    def get_score_distribution(self, obj):
        return parse_json_field(obj, "score_distribution")

    def get_score_variance(self, obj):
        return parse_json_field(obj, "score_variance")

    def get_bloom_skill_scores(self, obj):
        return parse_json_field(obj, "bloom_skill_scores")

    def get_general_insights(self, obj):
        return parse_json_field(obj, "general_insights")

    def get_grade_scores(self, obj):
        return parse_json_field(obj, "grade_scores")

    def get_strand_analysis(self, obj):
        return parse_json_field(obj, "strand_analysis")

    def get_strand_student_mastery(self, obj):
        return parse_json_field(obj, "strand_student_mastery")

    def get_flagged_sub_strands(self, obj):
        return parse_json_field(obj, "flagged_sub_strands")


class StudentExamSessionPerformanceSerializer(serializers.ModelSerializer):
    exam_id = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()

    bloom_skill_scores = serializers.SerializerMethodField()
    grade_scores = serializers.SerializerMethodField()
    strand_scores = serializers.SerializerMethodField()
    best_5_answers = serializers.SerializerMethodField()
    worst_5_answers = serializers.SerializerMethodField()

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
            'best_5_answers',
            'worst_5_answers',
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

    def get_bloom_skill_scores(self, obj):
        return parse_json_field(obj, "bloom_skill_scores")

    def get_grade_scores(self, obj):
        return parse_json_field(obj, "grade_scores")

    def get_strand_scores(self, obj):
        return parse_json_field(obj, "strand_scores")

    def get_best_5_answers(self, obj):
        ids = parse_json_field(obj, "best_5_answer_ids")
        answers = StudentExamSessionAnswer.objects.filter(id__in=ids)
        # Maintain original order
        answers_dict = {a.id: a for a in answers}
        ordered_answers = [answers_dict[i] for i in ids if i in answers_dict]
        return FullStudentExamSessionAnswerSerializer(ordered_answers, many=True).data

    def get_worst_5_answers(self, obj):
        ids = parse_json_field(obj, "worst_5_answer_ids")
        answers = StudentExamSessionAnswer.objects.filter(id__in=ids)
        answers_dict = {a.id: a for a in answers}
        ordered_answers = [answers_dict[i] for i in ids if i in answers_dict]
        return FullStudentExamSessionAnswerSerializer(ordered_answers, many=True).data


class StudentExamSessionPerformanceMiniSerializer(serializers.ModelSerializer):
    status = serializers.SerializerMethodField()
    exam_id = serializers.SerializerMethodField()
    student_id = serializers.SerializerMethodField()
    student_name = serializers.SerializerMethodField()

    class Meta:
        model = StudentExamSessionPerformance
        fields = [
            "id", "status", "exam_id", "student_id", "student_name", "avg_score", "avg_expectation_level"
        ]

    def get_status(self, obj):
        return obj.session.exam.status if obj.session and obj.session.exam else None

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
    # top_best_questions = serializers.SerializerMethodField()
    # top_worst_questions = serializers.SerializerMethodField()
    follow_up_exam_id = serializers.SerializerMethodField()

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
            # "top_best_questions",
            # "top_worst_questions",
            "created_at",
            "updated_at",
            "follow_up_exam_id",
        ]

    # Nested performances
    def get_student_sessions(self, obj):
        performances = obj.performances.all()
        return StudentExamSessionPerformanceMiniSerializer(performances, many=True).data

    def get_score_variance(self, obj):
        return parse_json_field(obj, "score_variance")

    def get_bloom_skill_scores(self, obj):
        return parse_json_field(obj, "bloom_skill_scores")

    def get_strand_scores(self, obj):
        return parse_json_field(obj, "strand_scores")

    # def get_top_best_questions(self, obj):
    #     import json
    #     ids = json.loads(obj.top_best_question_ids or "[]")
    #     questions = ExamQuestion.objects.filter(id__in=ids)
    #     # Return in the original order
    #     id_map = {q.id: q for q in questions}
    #     ordered_questions = [id_map[qid] for qid in ids if qid in id_map]
    #     return ExamQuestionSerializer(ordered_questions, many=True).data

    # def get_top_worst_questions(self, obj):
    #     import json
    #     ids = json.loads(obj.top_worst_question_ids or "[]")
    #     questions = ExamQuestion.objects.filter(id__in=ids)
    #     # Return in the original order
    #     id_map = {q.id: q for q in questions}
    #     ordered_questions = [id_map[qid] for qid in ids if qid in id_map]
    #     return ExamQuestionSerializer(ordered_questions, many=True).data

    def get_follow_up_exam_id(self, obj):
        follow_up_exam = obj.follow_up_exams.filter(type="FollowUp").first()
        return follow_up_exam.id if follow_up_exam else None


class ExamQuestionPerformanceSerializer(serializers.ModelSerializer):
    score_distribution = serializers.SerializerMethodField()
    answers_by_level = serializers.SerializerMethodField()

    class Meta:
        model = ExamQuestionPerformance
        fields = [
            "question_id",
            "avg_score",
            "avg_expectation_level",
            "score_distribution",
            "answers_by_level",
            "created_at",
            "updated_at",
        ]

    def get_score_distribution(self, obj):
        return _safe_json_parse(obj.score_distribution)

    def get_answers_by_level(self, obj):
        return _safe_json_parse(obj.answers_by_level)


class ClassAggregatePerformanceSerializer(serializers.ModelSerializer):
    bloom_skill_scores = serializers.SerializerMethodField()
    grade_scores = serializers.SerializerMethodField()
    strand_analysis = serializers.SerializerMethodField()

    class Meta:
        model = ClassAggregatePerformance
        fields = [
            "id", "exam_count", "avg_score", "avg_expectation_level",
            "bloom_skill_scores", "strand_analysis", "grade_scores",
            "created_at", "updated_at",
        ]

    def get_bloom_skill_scores(self, obj):
        return parse_json_field(obj, "bloom_skill_scores")

    def get_grade_scores(self, obj):
        return parse_json_field(obj, "grade_scores")

    def get_strand_analysis(self, obj):
        return parse_json_field(obj, "strand_analysis")


class StudentAggregatePerformanceSerializer(serializers.ModelSerializer):
    bloom_skill_scores = serializers.SerializerMethodField()
    grade_scores = serializers.SerializerMethodField()
    strand_scores = serializers.SerializerMethodField()
    student_id = serializers.ReadOnlyField(source='student.id')
    student_name = serializers.ReadOnlyField(source='student.name')

    class Meta:
        model = StudentAggregatePerformance
        fields = [
            "id",
            "exam_count",
            "student_id",
            "student_name",
            "avg_score",
            "avg_expectation_level",
            "bloom_skill_scores",
            "grade_scores",
            "strand_scores",
            "created_at",
            "updated_at",
        ]

    def get_bloom_skill_scores(self, obj):
        return parse_json_field(obj, "bloom_skill_scores")

    def get_grade_scores(self, obj):
        return parse_json_field(obj, "grade_scores")

    def get_strand_scores(self, obj):
        return parse_json_field(obj, "strand_scores")
