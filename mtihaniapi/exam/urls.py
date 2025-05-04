from django.urls import path
from .views import *

urlpatterns = [
    path('create-exam', create_exam),
]
