# serializers.py
from rest_framework import serializers
from .models import TeacherDocument, SubStrandReference


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


class SubStrandReferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = SubStrandReference
        fields = [
            'id', 'strand', 'sub_strand', 'reference_text', 'created_from',
             'created_at', 'last_updated'
        ]
        read_only_fields = ('created_at', 'last_updated')
