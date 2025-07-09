# serializers.py
from rest_framework import serializers
from .models import TeacherDocument


class TeacherDocumentSerializer(serializers.ModelSerializer):
    file_url = serializers.SerializerMethodField()
    
    class Meta:
        model = TeacherDocument
        fields = [
            'id', 'title', 'description', 'file', 'file_url', 'extension',
            'uploaded_by', 'uploaded_at',
            'approved_for_rag', 'approved_at', 'approved_by'
        ]
        read_only_fields = ['uploaded_by', 'uploaded_at',
                            'approved_for_rag', 'approved_at', 'approved_by', 'extension']

    def get_file_url(self, obj):
        request = self.context.get('request')
        if obj.file and request:
            return request.build_absolute_uri(obj.file.url)
        return None