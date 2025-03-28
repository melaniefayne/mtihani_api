from django.urls import path
from .views import create_class, create_teacher, upload_students_csv

urlpatterns = [
    path('create_class', create_class),
    path('create_teacher', create_teacher),
    path('upload_students', upload_students_csv),
]
