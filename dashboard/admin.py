from django.contrib import admin
from .models import (
    EstacionMeteorologica, 
    DispositivoIoT, 
    TipoVariable, 
    Sensor, 
    LecturaSensor, 
    Alerta
)

# Registros simples para la configuración
admin.site.register(EstacionMeteorologica)
admin.site.register(DispositivoIoT)
admin.site.register(TipoVariable)
admin.site.register(Sensor)

# Registros avanzados (con tablas ordenadas) para los datos
@admin.register(LecturaSensor)
class LecturaSensorAdmin(admin.ModelAdmin):
    list_display = ('sensor', 'valor', 'sensacion_termica', 'alerta_activa', 'registrado_en')
    list_filter = ('alerta_activa', 'registrado_en')
    search_fields = ('sensor__modelo',)

@admin.register(Alerta)
class AlertaAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'valor_detectado', 'estado', 'canal', 'generada_en')
    list_filter = ('estado', 'canal')