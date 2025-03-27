from django.urls import path
from .views import upload_bloom_skills, upload_curriculum

urlpatterns = [
    path("upload_curriculum/", upload_curriculum, name="upload_curriculum"),
    path("upload_bloom_skills/", upload_bloom_skills, name="upload_bloom_skills"),
]
