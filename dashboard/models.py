from django.db import models
from django.contrib.auth.models import User # Usaremos el sistema de usuarios nativo de Django
from django.utils import timezone
from datetime import timedelta

# ─────────────────────────────────────────────────────────────
# GRUPO 0 — Seguridad y Cuentas
# ─────────────────────────────────────────────────────────────

class PasswordResetCode(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    code = models.CharField(max_length=4)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_expired(self):
        return timezone.now() > self.created_at + timedelta(minutes=10)

# ─────────────────────────────────────────────────────────────
# GRUPO 1 — Infraestructura física
# ─────────────────────────────────────────────────────────────

class EstacionMeteorologica(models.Model):
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('inactiva', 'Inactiva'),
        ('mantenimiento', 'Mantenimiento'),
    ]
    nombre = models.CharField(max_length=150)
    ubicacion = models.CharField(max_length=250)
    latitud = models.DecimalField(max_digits=9, decimal_places=6)
    longitud = models.DecimalField(max_digits=9, decimal_places=6)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.nombre

class DispositivoIoT(models.Model):
    TIPO_CHOICES = [
        ('esp32', 'ESP32'),
        ('esp8266', 'ESP8266'),
        ('raspberry', 'Raspberry Pi'),
        ('otro', 'Otro'),
    ]
    ESTADO_CHOICES = [
        ('online', 'Online'),
        ('offline', 'Offline'),
        ('error', 'Error'),
    ]
    estacion = models.ForeignKey(EstacionMeteorologica, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, default="Estacion Termica")
    usuario_propietario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    codigo_validacion = models.CharField(max_length=10, null=True, blank=True)
    mac_address = models.CharField(max_length=20, unique=True)
    firmware_version = models.CharField(max_length=20, blank=True, null=True)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='esp32')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='offline')
    ultimo_ping = models.DateTimeField(blank=True, null=True)
    creado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.mac_address})"

class ConfiguracionSistema(models.Model):
    estacion = models.ForeignKey(EstacionMeteorologica, on_delete=models.CASCADE)
    clave = models.CharField(max_length=80)
    valor = models.TextField()
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    actualizado_en = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('estacion', 'clave')

    def __str__(self):
        return f"{self.estacion.nombre} - {self.clave}"

# ─────────────────────────────────────────────────────────────
# GRUPO 2 — Sensado y variables
# ─────────────────────────────────────────────────────────────

class TipoVariable(models.Model):
    nombre = models.CharField(max_length=60, unique=True)
    unidad = models.CharField(max_length=20)
    rango_min = models.DecimalField(max_digits=7, decimal_places=2)
    rango_max = models.DecimalField(max_digits=7, decimal_places=2)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"{self.nombre} ({self.unidad})"

class Sensor(models.Model):
    ESTADO_CHOICES = [
        ('activo', 'Activo'),
        ('inactivo', 'Inactivo'),
        ('falla', 'Falla'),
    ]
    dispositivo = models.ForeignKey(DispositivoIoT, on_delete=models.CASCADE)
    tipo_variable = models.ForeignKey(TipoVariable, on_delete=models.RESTRICT)
    modelo = models.CharField(max_length=80)
    precision_dec = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activo')
    calibrado_en = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return f"{self.modelo} - {self.tipo_variable.nombre}"

class LogConectividad(models.Model):
    EVENTO_CHOICES = [
        ('conexion', 'Conexión'),
        ('desconexion', 'Desconexión'),
        ('timeout', 'Timeout'),
        ('error', 'Error'),
    ]
    dispositivo = models.ForeignKey(DispositivoIoT, on_delete=models.CASCADE)
    evento = models.CharField(max_length=20, choices=EVENTO_CHOICES)
    ip_address = models.CharField(max_length=45, blank=True, null=True)
    ocurrido_en = models.DateTimeField(auto_now_add=True)

# ─────────────────────────────────────────────────────────────
# GRUPO 3 — Lecturas y riesgo térmico
# ─────────────────────────────────────────────────────────────

class LecturaSensor(models.Model):
    sensor = models.ForeignKey(Sensor, on_delete=models.CASCADE)
    valor = models.DecimalField(max_digits=7, decimal_places=3)
    sensacion_termica = models.DecimalField(max_digits=5, decimal_places=2, blank=True, null=True)
    alerta_activa = models.BooleanField(default=False)
    registrado_en = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.sensor.tipo_variable.nombre}: {self.valor} a las {self.registrado_en}"

class EstadoRiesgoTermico(models.Model):
    RIESGO_CHOICES = [
        ('bajo', 'Bajo'),
        ('moderado', 'Moderado'),
        ('alto', 'Alto'),
        ('critico', 'Crítico'),
    ]
    lectura = models.OneToOneField(LecturaSensor, on_delete=models.CASCADE)
    nivel_riesgo = models.CharField(max_length=20, choices=RIESGO_CHOICES)
    indice_calor = models.DecimalField(max_digits=5, decimal_places=2)
    descripcion = models.CharField(max_length=200, blank=True, null=True)
    evaluado_en = models.DateTimeField(auto_now_add=True)

# ─────────────────────────────────────────────────────────────
# GRUPO 4 — Alertas y notificaciones
# ─────────────────────────────────────────────────────────────

class UmbralAlerta(models.Model):
    SEVERIDAD_CHOICES = [
        ('info', 'Info'),
        ('advertencia', 'Advertencia'),
        ('critico', 'Crítico'),
    ]
    tipo_variable = models.ForeignKey(TipoVariable, on_delete=models.CASCADE)
    valor_min = models.DecimalField(max_digits=7, decimal_places=2)
    valor_max = models.DecimalField(max_digits=7, decimal_places=2)
    severidad = models.CharField(max_length=20, choices=SEVERIDAD_CHOICES)
    activo = models.BooleanField(default=True)
    actualizado_en = models.DateTimeField(auto_now=True)

class Alerta(models.Model):
    CANAL_CHOICES = [
        ('telegram', 'Telegram'),
        ('email', 'Email'),
        ('push', 'Push'),
        ('sms', 'SMS'),
    ]
    ESTADO_CHOICES = [
        ('activa', 'Activa'),
        ('resuelta', 'Resuelta'),
        ('ignorada', 'Ignorada'),
    ]
    lectura = models.ForeignKey(LecturaSensor, on_delete=models.CASCADE)
    umbral = models.ForeignKey(UmbralAlerta, on_delete=models.RESTRICT)
    tipo = models.CharField(max_length=80)
    valor_detectado = models.DecimalField(max_digits=7, decimal_places=2)
    canal = models.CharField(max_length=20, choices=CANAL_CHOICES, default='telegram')
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='activa')
    generada_en = models.DateTimeField(auto_now_add=True)

class Notificacion(models.Model):
    ESTADO_CHOICES = [
        ('pendiente', 'Pendiente'),
        ('enviada', 'Enviada'),
        ('fallida', 'Fallida'),
    ]
    alerta = models.ForeignKey(Alerta, on_delete=models.CASCADE)
    destinatario = models.CharField(max_length=150)
    canal = models.CharField(max_length=20) # Reutiliza CANAL_CHOICES si deseas
    mensaje = models.TextField()
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='pendiente')
    enviada_en = models.DateTimeField(blank=True, null=True)

# ─────────────────────────────────────────────────────────────
# GRUPO 5 — Actuadores y comandos remotos
# ─────────────────────────────────────────────────────────────

class Actuador(models.Model):
    TIPO_CHOICES = [
        ('relay', 'Relay'),
        ('ventilador', 'Ventilador'),
        ('nebulizador', 'Nebulizador'),
        ('led', 'LED'),
        ('otro', 'Otro'),
    ]
    dispositivo = models.ForeignKey(DispositivoIoT, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=80)
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='relay')
    activo = models.BooleanField(default=False)
    creado_en = models.DateTimeField(auto_now_add=True)

class EstadoActuador(models.Model):
    ESTADO_CHOICES = [
        ('encendido', 'Encendido'),
        ('apagado', 'Apagado'),
        ('error', 'Error'),
    ]
    actuador = models.ForeignKey(Actuador, on_delete=models.CASCADE)
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES)
    origen = models.CharField(max_length=60, blank=True, null=True)
    registrado_en = models.DateTimeField(auto_now_add=True)

class ComandoRemoto(models.Model):
    ORIGEN_CHOICES = [
        ('dashboard', 'Dashboard'),
        ('automatico', 'Automático'),
        ('api', 'API'),
    ]
    dispositivo = models.ForeignKey(DispositivoIoT, on_delete=models.CASCADE)
    comando = models.CharField(max_length=100)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, default='dashboard')
    ejecutado = models.BooleanField(default=False)
    solicitado_en = models.DateTimeField(auto_now_add=True)

class RespuestaComando(models.Model):
    comando = models.OneToOneField(ComandoRemoto, on_delete=models.CASCADE)
    exito = models.BooleanField()
    respuesta = models.TextField(blank=True, null=True)
    respondido_en = models.DateTimeField(auto_now_add=True)

# ─────────────────────────────────────────────────────────────
# GRUPO 6 — Auditoría (Usuarios delegados a Django Auth)
# ─────────────────────────────────────────────────────────────

class AuditoriaSistema(models.Model):
    # Se usa el modelo User nativo de Django en lugar de crear una tabla custom
    usuario = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    accion = models.CharField(max_length=100)
    tabla_afectada = models.CharField(max_length=80)
    registro_id = models.IntegerField(blank=True, null=True)
    detalle = models.TextField(blank=True, null=True)
    ocurrido_en = models.DateTimeField(auto_now_add=True)

# ─────────────────────────────────────────────────────────────
# GRUPO 7 — Control de Roles y Perfiles
# ─────────────────────────────────────────────────────────────

class Rol(models.Model):
    nombre = models.CharField(max_length=50, unique=True)
    descripcion = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nombre

class PerfilUsuario(models.Model):
    usuario = models.OneToOneField(User, on_delete=models.CASCADE)
    rol = models.ForeignKey(Rol, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return f"{self.usuario.username} - {self.rol.nombre if self.rol else 'Sin Rol'}"