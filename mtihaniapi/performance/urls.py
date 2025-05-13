from django.urls import path
from .views import *

urlpatterns = [
    path('edit-answer-score', edit_answer_score),
]
