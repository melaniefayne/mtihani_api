from django.urls import path
from .views import *

urlpatterns = [
    path('create_class', create_class),
    path('create_teacher', create_teacher),
    path('upload_students', upload_students_csv),
    path('update_class', update_class),
    path('update_teacher', update_teacher),
    path('update_term_scores', upsert_term_scores),
]
