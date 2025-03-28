# learner/serializers.py
from rest_framework import serializers
from .models import Class, Teacher, LessonTime


class TeacherSerializer(serializers.ModelSerializer):
    class Meta:
        model = Teacher
        fields = '__all__'


class ClassSerializer(serializers.ModelSerializer):
    class Meta:
        model = Class
        fields = '__all__'


class LessonTimeSerializer(serializers.ModelSerializer):
    class Meta:
        model = LessonTime
        fields = '__all__'
