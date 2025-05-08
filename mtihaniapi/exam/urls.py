from django.urls import path
from .views import *

urlpatterns = [
    path('create-classroom-exam', create_classroom_exam),
    path('retry-exam-generation', retry_exam_generation),
    path('edit-classroom-exam', edit_classroom_exam),
    path('edit-exam-questions', edit_exam_questions),
    path('get-user-exams', get_user_exams),
    path('get-exam-questions', get_exam_questions),
    path('get-single-exam', get_single_exam),
    path('start-exam-session', start_exam_session),
    path('get-exam-session', get_exam_session),
    path('update-exam-answer', update_exam_answer),
    path('end-exam-session', end_exam_session),
]
