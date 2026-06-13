from django.urls import path
from . import views

urlpatterns = [
    # --- RUTA PARA EL CIRCUITO ESP32 ---
    path('sensor-data/', views.recibir_datos_esp32, name='recibir_datos'), # <-- Se quita "api/"
    
    # --- RUTAS PARA EL FRONTEND DE ANGULAR ---
    path('ultimos-datos/', views.obtener_ultimos_datos, name='ultimos_datos'),
    path('historial/', views.obtener_historial, name='historial'),
    path('control/', views.control_dispositivo, name='control'),
    
    # --- RUTAS DE AUTENTICACIÓN Y SAAS ---
    path('login/', views.CustomLoginView.as_view(), name='custom_login'),
    path('registrar-usuario/', views.registrar_usuario, name='registrar_usuario'),
    path('vincular-dispositivo/', views.vincular_dispositivo, name='vincular_dispositivo'),

    # --- RUTAS RECUPERACIÓN DE CONTRASEÑA ---
    path('password-reset/solicitar/', views.solicitar_restablecimiento, name='pw_reset_solicitar'),
    path('password-reset/confirmar/', views.confirmar_restablecimiento, name='pw_reset_confirmar'),

    # --- RUTAS DE ADMINISTRACIÓN ---
    path('admin/usuarios/', views.AdminUsuariosView.as_view(), name='admin_usuarios'),
    path('admin/dispositivos/', views.AdminDispositivosView.as_view(), name='admin_dispositivos'),
    path('admin/usuarios-dispositivos/', views.AdminUsuariosDispositivosView.as_view(), name='admin_usuarios_dispositivos'),
]