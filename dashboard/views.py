import json
import random
from django.http import JsonResponse
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

# --- Importaciones de Django REST Framework para la seguridad ---
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny, IsAdminUser, BasePermission
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.views import TokenObtainPairView
from django.db.models import F, Count

# Asegúrate de importar todos los modelos que usamos
from .models import DispositivoIoT, Sensor, LecturaSensor, TipoVariable, Rol, PerfilUsuario, PasswordResetCode
from .serializers import PasswordResetRequestSerializer, PasswordResetConfirmSerializer


# ===============================
# 1. VISTAS DEL HARDWARE (ESP32) 
# ===============================

@csrf_exempt  
def recibir_datos_esp32(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Limpiamos la MAC recibida para evitar fallos por espacios o mayúsculas
            mac_recibida = str(data.get('mac_address', '')).strip()
            
            if not mac_recibida:
                return JsonResponse({'error': 'Falta el campo mac_address'}, status=400)

            dispositivo = DispositivoIoT.objects.filter(mac_address__iexact=mac_recibida).first()
            if not dispositivo:
                return JsonResponse({'error': f'Dispositivo con MAC {mac_recibida} no existe en la BD'}, status=404)

            if 'temperatura' in data:
                sensor_temp = Sensor.objects.filter(dispositivo=dispositivo, tipo_variable__nombre__icontains='temp').first()
                if sensor_temp:
                    LecturaSensor.objects.create(
                        sensor=sensor_temp,
                        valor=data['temperatura'],
                        sensacion_termica=data.get('sensacion_termica')
                    )

            if 'humedad' in data:
                sensor_hum = Sensor.objects.filter(dispositivo=dispositivo, tipo_variable__nombre__icontains='hum').first()
                if sensor_hum:
                    LecturaSensor.objects.create(sensor=sensor_hum, valor=data['humedad'])

            if 'presion' in data:
                sensor_pres = Sensor.objects.filter(dispositivo=dispositivo, tipo_variable__nombre__icontains='pres').first()
                if sensor_pres:
                    LecturaSensor.objects.create(sensor=sensor_pres, valor=data['presion'])

            return JsonResponse({'status': 'success', 'mensaje': 'Datos procesados'}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'El formato JSON es inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Solo se permiten peticiones POST'}, status=405)


# =============================================
# 2. VISTAS DEL FRONTEND  - Datos del Dashboard
# =============================================

# Nota: Por ahora mantenemos el GET público. Cuando configuremos Angular con JWT, 
# cambiaremos esto para que solo traiga los datos del dispositivo del usuario logueado.

def obtener_ultimos_datos(request):
    if request.method == 'GET':
        try:
            ultima_temp = LecturaSensor.objects.filter(sensor__tipo_variable__nombre__icontains='temp').order_by('-id').first()
            ultima_hum = LecturaSensor.objects.filter(sensor__tipo_variable__nombre__icontains='hum').order_by('-id').first()
            ultima_pres = LecturaSensor.objects.filter(sensor__tipo_variable__nombre__icontains='pres').order_by('-id').first()

            datos = {
                'temperatura': float(ultima_temp.valor) if ultima_temp else 0,
                'humedad': float(ultima_hum.valor) if ultima_hum else 0,
                'presion': float(ultima_pres.valor) if ultima_pres else 0,
            }
            return JsonResponse(datos, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Solo método GET permitido'}, status=405)

def obtener_historial(request):
    if request.method == 'GET':
        datos_historial = {
            'dias': ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'],
            'riesgo': [65, 72, 88, 95, 82, 60, 55] 
        }
        return JsonResponse(datos_historial, status=200)

@csrf_exempt 
def control_dispositivo(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            equipo = data.get('equipo')
            accion = data.get('accion')
            print(f"=== COMANDO DE INTERFAZ RECIBIDO: {equipo} -> {accion} ===")
            return JsonResponse({'status': 'success', 'mensaje': f'Orden recibida para {equipo}'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    return JsonResponse({'error': 'Solo método POST permitido'}, status=405)


# ==============================================================================
# 3. VISTAS SAAS: AUTENTICACIÓN Y VINCULACIÓN (NUEVAS)
# ==============================================================================

# Cualquier persona puede registrarse (AllowAny)
@api_view(['POST'])
@permission_classes([AllowAny])
def registrar_usuario(request):
    try:
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')

        if not username or not password:
            return JsonResponse({'error': 'Usuario y contraseña son obligatorios'}, status=400)

        if User.objects.filter(username=username).exists():
            return JsonResponse({'error': 'El nombre de usuario ya existe'}, status=400)

        nuevo_usuario = User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )

        # Asignar el rol por defecto de "usuario_cliente"
        rol_cliente, _ = Rol.objects.get_or_create(nombre='usuario_cliente', defaults={'descripcion': 'Usuario estándar del sistema'})
        PerfilUsuario.objects.create(usuario=nuevo_usuario, rol=rol_cliente)

        return JsonResponse({'status': 'success', 'mensaje': 'Usuario creado exitosamente'}, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@api_view(['POST'])
@permission_classes([AllowAny])
def solicitar_restablecimiento(request):
    serializer = PasswordResetRequestSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    email = serializer.validated_data['email']
    try:
        usuario = User.objects.get(email__iexact=email)
        
        # Generar código de 4 dígitos
        codigo_aleatorio = str(random.randint(1000, 9999))
        
        # Guardar en la BD (borrar códigos anteriores del mismo usuario para limpieza)
        PasswordResetCode.objects.filter(user=usuario).delete()
        PasswordResetCode.objects.create(user=usuario, code=codigo_aleatorio)
        
        # Configuración del correo HTML
        asunto = 'Código de recuperación - Estación Térmica'
        contexto = {
            'username': usuario.username,
            'codigo': codigo_aleatorio
        }
        html_content = render_to_string('emails/password_reset.html', contexto)
        text_content = strip_tags(html_content) # Versión en texto plano para clientes antiguos

        email_mensaje = EmailMultiAlternatives(
            asunto,
            text_content,
            None, # Usa DEFAULT_FROM_EMAIL de settings.py
            [email]
        )
        email_mensaje.attach_alternative(html_content, "text/html")
        email_mensaje.send()
        
        return Response({'status': 'success', 'mensaje': 'Código enviado al correo'}, status=200)
    except User.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=404)
    except Exception as e:
        print(f"DEBUG: Error enviando correo: {e}")
        return Response({'error': str(e)}, status=500)

@api_view(['POST'])
@permission_classes([AllowAny])
def confirmar_restablecimiento(request):
    serializer = PasswordResetConfirmSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(serializer.errors, status=400)
    
    email = serializer.validated_data['email']
    codigo = serializer.validated_data['codigo']
    nueva_password = serializer.validated_data['nueva_password']
    
    try:
        usuario = User.objects.get(email=email)
        reset_obj = PasswordResetCode.objects.filter(user=usuario, code=codigo).first()
        
        if not reset_obj:
            return Response({'error': 'Código inválido'}, status=400)
        
        if reset_obj.is_expired():
            return Response({'error': 'Código expirado'}, status=400)
        
        usuario.set_password(nueva_password)
        usuario.save()
        reset_obj.delete() # Limpiar código usado
        
        return Response({'status': 'success', 'mensaje': 'Contraseña actualizada exitosamente'}, status=200)
    except User.DoesNotExist:
        return Response({'error': 'Usuario no encontrado'}, status=404)


# ==============================================================================
# 4. VISTAS SAAS: ADMINISTRACIÓN Y LOGIN PERSONALIZADO
# ==============================================================================

# --- Permiso Customizado basado en el Rol ---
class IsRoleAdmin(BasePermission):
    """
    Permite el acceso solo a usuarios que tengan asociado explícitamente el rol de 'admin'
    en nuestro modelo Rol.
    """
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        try:
            return request.user.perfilusuario.rol.nombre.lower() == 'admin'
        except Exception:
            return False

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        try:
            token['is_admin'] = user.perfilusuario.rol.nombre.lower() == 'admin'
        except Exception:
            token['is_admin'] = user.is_staff or user.is_superuser
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        try:
            data['is_admin'] = self.user.perfilusuario.rol.nombre.lower() == 'admin'
        except Exception:
            data['is_admin'] = self.user.is_staff or self.user.is_superuser
        return data

class CustomLoginView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

class AdminUsuariosView(APIView):
    permission_classes = [IsRoleAdmin]

    def get(self, request):
        # Se anota la cantidad de dispositivos que le pertenecen a este usuario
        usuarios = User.objects.annotate(
            cantidad_dispositivos=Count('dispositivoiot')
        ).values('id', 'username', 'email', 'is_staff', 'cantidad_dispositivos')
        return Response(list(usuarios))
        
    def post(self, request):
        try:
            username = request.data.get('username')
            email = request.data.get('email', '')
            password = request.data.get('password')
            rol_nombre = request.data.get('rol', 'usuario_cliente')

            if not username or not password:
                return Response({'error': 'Usuario y contraseña son obligatorios'}, status=400)

            if User.objects.filter(username=username).exists():
                return Response({'error': 'El nombre de usuario ya existe'}, status=400)

            nuevo_usuario = User.objects.create(
                username=username,
                email=email,
                password=make_password(password)
            )

            rol, _ = Rol.objects.get_or_create(nombre=rol_nombre)
            PerfilUsuario.objects.create(usuario=nuevo_usuario, rol=rol)

            return Response({'status': 'success', 'mensaje': 'Usuario creado exitosamente'}, status=201)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

    def put(self, request):
        try:
            user_id = request.data.get('id')
            if not user_id:
                return Response({'error': 'Se requiere el ID del usuario para actualizar'}, status=400)

            usuario = User.objects.get(id=user_id)
            
            if 'username' in request.data:
                usuario.username = request.data['username']
            if 'email' in request.data:
                usuario.email = request.data['email']
            if 'password' in request.data and request.data['password']:
                usuario.password = make_password(request.data['password'])
            
            usuario.save()

            # Si se envía un rol para actualizar
            if 'rol' in request.data:
                rol_nombre = request.data['rol']
                rol, _ = Rol.objects.get_or_create(nombre=rol_nombre)
                perfil, _ = PerfilUsuario.objects.get_or_create(usuario=usuario)
                perfil.rol = rol
                perfil.save()

            return Response({'status': 'success', 'mensaje': 'Usuario actualizado exitosamente'}, status=200)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)
            
    def delete(self, request):
        try:
            # Permitimos recibir el ID tanto por la URL (?id=X) como en el body
            user_id = request.query_params.get('id') or request.data.get('id')
            
            if not user_id:
                return Response({'error': 'Se requiere el ID del usuario para eliminar'}, status=400)

            usuario = User.objects.get(id=user_id)
            usuario.delete()

            return Response({'status': 'success', 'mensaje': 'Usuario eliminado exitosamente'}, status=200)
        except User.DoesNotExist:
            return Response({'error': 'Usuario no encontrado'}, status=404)
        except Exception as e:
            return Response({'error': str(e)}, status=500)

class AdminDispositivosView(APIView):
    permission_classes = [IsRoleAdmin]

    def get(self, request):
        # Se anota el campo "nombre" para que devuelva la clave "equipo" requerida por el frontend
        # Se incluye "propietario" apuntando a la clave foránea del usuario
        dispositivos = DispositivoIoT.objects.annotate(
            equipo=F('nombre'),
            propietario=F('usuario_propietario_id')
        ).values('id', 'equipo', 'estado', 'propietario')
        return Response(list(dispositivos))

class AdminUsuariosDispositivosView(APIView):
    # Usamos nuestro nuevo permiso basado en la base de datos
    permission_classes = [IsRoleAdmin]

    def get(self, request):
        usuarios = User.objects.all().prefetch_related('perfilusuario')
        resultado = []
        for usuario in usuarios:
            dispositivos = DispositivoIoT.objects.filter(usuario_propietario=usuario).values('id', 'nombre', 'mac_address', 'estado')
            try:
                rol = usuario.perfilusuario.rol.nombre
            except Exception:
                rol = 'Sin Rol'
            resultado.append({
                'id': usuario.id,
                'username': usuario.username,
                'rol': rol,
                'dispositivos_asociados': list(dispositivos)
            })
        return Response(resultado)


# SOLO usuarios con Token válido (logueados) pueden vincular placas
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def vincular_dispositivo(request):
    try:
        mac_recibida = request.data.get('mac_address')
        codigo_ingresado = request.data.get('codigo_validacion')
        nombre_personalizado = request.data.get('nombre')
        
        # El decorador IsAuthenticated garantiza que request.user es un usuario válido
        usuario_actual = request.user 

        if not mac_recibida or not codigo_ingresado:
            return JsonResponse({'error': 'Faltan datos de vinculación'}, status=400)

        # 1. Crear (o actualizar si ya existía) el dispositivo y asignarle el dueño
        dispositivo, creado = DispositivoIoT.objects.update_or_create(
            mac_address=mac_recibida,
            defaults={
                'nombre': nombre_personalizado,
                'usuario_propietario': usuario_actual,
                'codigo_validacion': codigo_ingresado
            }
        )

        # 2. Asegurar que las variables maestras existan
        var_temp, _ = TipoVariable.objects.get_or_create(nombre='Temperatura')
        var_hum, _ = TipoVariable.objects.get_or_create(nombre='Humedad')
        var_pres, _ = TipoVariable.objects.get_or_create(nombre='Presión')

        # 3. Soldar los cables virtuales (crear sensores si la placa es nueva)
        if creado:
            Sensor.objects.get_or_create(dispositivo=dispositivo, tipo_variable=var_temp)
            Sensor.objects.get_or_create(dispositivo=dispositivo, tipo_variable=var_hum)
            Sensor.objects.get_or_create(dispositivo=dispositivo, tipo_variable=var_pres)

        return JsonResponse({
            'status': 'success', 
            'mensaje': f'¡Dispositivo {nombre_personalizado} vinculado con éxito a {usuario_actual.username}!'
        }, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)