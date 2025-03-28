from django.urls import path
from .views import login_user, register_user

urlpatterns = [
    path('register/', register_user),
    path('login/', login_user),
]
