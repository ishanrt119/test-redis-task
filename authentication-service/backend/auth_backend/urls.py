from django.contrib import admin
from django.urls import include, path
from django.http import JsonResponse

def health(request):
    return JsonResponse({"status": "healthy"})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/auth/', include('auth_app.urls')),
    path('health/', health),
]
