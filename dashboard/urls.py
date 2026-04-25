from django.urls import path
from . import views

urlpatterns = [
    # Esta será la dirección a la que el ESP32 enviará el POST
    path('api/sensor-data/', views.recibir_datos_esp32, name='recibir_datos'),
]