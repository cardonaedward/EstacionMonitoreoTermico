from django.urls import path
from . import views

urlpatterns = [
    # --- RUTA PARA EL CIRCUITO ESP32 ---
    path('api/sensor-data/', views.recibir_datos_esp32, name='recibir_datos'),
    
    # --- RUTAS PARA EL FRONTEND DE ANGULAR ---
    path('api/ultimos-datos/', views.obtener_ultimos_datos, name='ultimos_datos'),
    path('api/historial/', views.obtener_historial, name='historial'),
    path('api/control/', views.control_dispositivo, name='control'),
    
    # --- RUTAS DE AUTENTICACIÓN Y SAAS ---
    path('api/login/', views.CustomLoginView.as_view(), name='custom_login'),
    path('api/registrar-usuario/', views.registrar_usuario, name='registrar_usuario'),
    path('api/vincular-dispositivo/', views.vincular_dispositivo, name='vincular_dispositivo'),

    # --- RUTAS RECUPERACIÓN DE CONTRASEÑA ---
    path('api/password-reset/solicitar/', views.solicitar_restablecimiento, name='pw_reset_solicitar'),
    path('api/password-reset/confirmar/', views.confirmar_restablecimiento, name='pw_reset_confirmar'),

    # --- RUTAS DE ADMINISTRACIÓN ---
    path('api/admin/usuarios/', views.AdminUsuariosView.as_view(), name='admin_usuarios'),
    path('api/admin/dispositivos/', views.AdminDispositivosView.as_view(), name='admin_dispositivos'),
    path('api/admin/usuarios-dispositivos/', views.AdminUsuariosDispositivosView.as_view(), name='admin_usuarios_dispositivos'),
]