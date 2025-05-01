# exam/serializers.py
from rest_framework import serializers

class ClassroomPerformanceSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    grade = serializers.IntegerField()
    subject = serializers.CharField()
    school_name = serializers.CharField()
    school_address = serializers.CharField()
    teacher_id = serializers.IntegerField(allow_null=True)
    lesson_times = serializers.ListField(child=serializers.CharField())
    avg_term_score = serializers.FloatField()
    avg_term_expectation_level = serializers.CharField()
    avg_mtihani_score = serializers.FloatField()
    avg_mtihani_expectation_level = serializers.CharField()
