from django.urls import path
from .views import *

urlpatterns = [
    path("upload_curriculum/", upload_curriculum, name="upload_curriculum"),
    path("upload_bloom_skills/", upload_bloom_skills, name="upload_bloom_skills"),
    path('full_curriculum', full_curriculum),
    path('my_grade', cbc_my_grade),
]
