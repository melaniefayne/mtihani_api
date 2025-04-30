from django.urls import path
from .views import *

urlpatterns = [
    path('register-user', register_user),
    path('login-user', login_user),
    path('update-user', update_user),
    path('change-password', change_password),
]
