import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password

# --- Importaciones de Django REST Framework para la seguridad ---
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny

# Asegúrate de importar todos los modelos que usamos
from .models import DispositivoIoT, Sensor, LecturaSensor, TipoVariable


# ==============================================================================
# 1. VISTAS DEL HARDWARE (ESP32) - Sin protección JWT porque es un microcontrolador
# ==============================================================================

@csrf_exempt  
def recibir_datos_esp32(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            mac_recibida = data.get('mac_address')
            
            try:
                dispositivo = DispositivoIoT.objects.get(mac_address=mac_recibida)
            except DispositivoIoT.DoesNotExist:
                return JsonResponse({'error': f'Dispositivo con MAC {mac_recibida} no registrado'}, status=404)

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


# ==============================================================================
# 2. VISTAS DEL FRONTEND (ANGULAR) - Datos del Dashboard
# ==============================================================================

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

        User.objects.create(
            username=username,
            email=email,
            password=make_password(password)
        )

        return JsonResponse({'status': 'success', 'mensaje': 'Usuario creado exitosamente'}, status=201)

    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


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