from django.contrib import admin
from django.http import JsonResponse
from django.urls import path, include
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)


def home(request):
    return JsonResponse({"message": "API running :)"})


urlpatterns = [
    path('', home),
    path('admin/', admin.site.urls),
    path('api/get_token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/refresh_token', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/accounts/', include('accounts.urls')),
    path('api/accounts/', include('accounts.urls')),
    path('api/learner/', include('learner.urls')),
    path('api/exam/', include('exam.urls')),
    path('api/rag/', include('rag.urls')),
]
