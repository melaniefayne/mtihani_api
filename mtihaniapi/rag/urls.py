# urls.py

from django.urls import path
from .views import *

urlpatterns = [
    path('upload-teacher-document', upload_teacher_document),
    path('get-teacher-documents', list_teacher_documents),
    path('delete-teacher-document', delete_teacher_document),
    path('approve-teacher-document', approve_teacher_document),
]