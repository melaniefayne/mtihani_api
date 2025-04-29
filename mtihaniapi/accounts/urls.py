from django.urls import path
from .views import *

urlpatterns = [
    path('register', register_user),
    path('login-user', login_user),
    path('update_user', update_user),
    path('change_password', change_password),
]
