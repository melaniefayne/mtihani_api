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
    path('api/get_token', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/refresh_token', TokenRefreshView.as_view(), name='token_refresh'),
    path('admin/', admin.site.urls),
    path('api/cbc/', include('cbc.urls')),
]
