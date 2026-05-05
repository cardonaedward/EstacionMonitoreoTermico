from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from dashboard import views
 
urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('dashboard.urls')), # <-- Conecta tu API al sistema principal
    path('api/vincular/', views.vincular_dispositivo, name='vincular_dispositivo'),
    path('api/registro/', views.registrar_usuario, name='registrar_usuario'),
    path('api/login/', views.CustomLoginView.as_view(), name='token_obtain_pair'), # Ruta personalizada para login con is_admin
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]