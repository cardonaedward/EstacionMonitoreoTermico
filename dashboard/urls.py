from django.urls import path
from . import views

urlpatterns = [
    # --- RUTA PARA EL CIRCUITO ESP32 ---
    path('api/sensor-data/', views.recibir_datos_esp32, name='recibir_datos'),
    
    # --- RUTAS PARA EL FRONTEND DE ANGULAR ---
    path('api/ultimos-datos/', views.obtener_ultimos_datos, name='ultimos_datos'),
    path('api/historial/', views.obtener_historial, name='historial'),
    path('api/control/', views.control_dispositivo, name='control'),
]