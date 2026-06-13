from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from dashboard import views
 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('dashboard.urls')), # <-- Unificamos todas las rutas del dashboard bajo /api/
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]