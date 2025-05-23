from django.urls import path
from .views import *

urlpatterns = [
    path('create-class', create_classroom),
    path('get-user-classrooms', get_user_classrooms),
    path('get-classroom-term-scores', get_classroom_term_scores),
    path('get-classroom-students', get_students),
    path('edit-classroom', edit_classroom),
    path('edit-classroom-student', edit_student),
    path('join-classroom', join_classroom),
    path('get-single-student', get_single_student),
]
