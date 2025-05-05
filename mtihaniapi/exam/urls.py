from django.urls import path
from .views import *

urlpatterns = [
    path('create-exam', create_exam),
    path('retry-exam-generation', retry_exam_generation),
    path('edit-exam', edit_exam),
    path('edit-exam-questions', edit_exam_questions),
]
