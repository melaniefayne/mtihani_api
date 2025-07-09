# serializers.py
from rest_framework import serializers
from .models import TeacherDocument


class TeacherDocumentSerializer(serializers.ModelSerializer):
    class Meta:
        model = TeacherDocument
        fields = [
            'id', 'title', 'description', 'file', 'uploaded_by', 'uploaded_at', 'extension',
            'approved_for_rag', 'approved_at', 'approved_by'
        ]
        read_only_fields = ['uploaded_by', 'uploaded_at',
                            'approved_for_rag', 'approved_at', 'approved_by', 'extension']
