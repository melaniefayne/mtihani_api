from django.urls import path
from .views import create_class, create_teacher, upload_students_csv

urlpatterns = [
    path('create-class/', create_class),
    path('create-teacher/', create_teacher),
    path('upload-students/', upload_students_csv),
]
