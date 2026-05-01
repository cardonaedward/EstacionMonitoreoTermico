from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import DispositivoIoT, Sensor, LecturaSensor

@csrf_exempt  # Desactiva la seguridad web normal para permitir que el ESP32 envíe datos
def recibir_datos_esp32(request):
    if request.method == 'POST':
        try:
            # 1. Leer el JSON que llega del circuito
            data = json.loads(request.body)
            mac_recibida = data.get('mac_address')
            
            # 2. Buscar si el dispositivo existe en la base de datos
            try:
                dispositivo = DispositivoIoT.objects.get(mac_address=mac_recibida)
            except DispositivoIoT.DoesNotExist:
                return JsonResponse({'error': f'Dispositivo con MAC {mac_recibida} no registrado'}, status=404)

            # 3. Guardar Temperatura
            if 'temperatura' in data:
                sensor_temp = Sensor.objects.filter(dispositivo=dispositivo, tipo_variable__nombre__icontains='temp').first()
                if sensor_temp:
                    LecturaSensor.objects.create(
                        sensor=sensor_temp,
                        valor=data['temperatura'],
                        sensacion_termica=data.get('sensacion_termica') # Si no viene en Wokwi, guardará null o vacío
                    )
                else:
                    print(f"ALERTA: Falta registrar un sensor de TEMPERATURA para el dispositivo {dispositivo.nombre}")

            # 4. Guardar Humedad
            if 'humedad' in data:
                sensor_hum = Sensor.objects.filter(dispositivo=dispositivo, tipo_variable__nombre__icontains='hum').first()
                if sensor_hum:
                    LecturaSensor.objects.create(sensor=sensor_hum, valor=data['humedad'])
                else:
                    print(f"ALERTA: Falta registrar un sensor de HUMEDAD para el dispositivo {dispositivo.nombre}")

            # 5. Guardar Presión
            if 'presion' in data:
                sensor_pres = Sensor.objects.filter(dispositivo=dispositivo, tipo_variable__nombre__icontains='pres').first()
                if sensor_pres:
                    LecturaSensor.objects.create(sensor=sensor_pres, valor=data['presion'])
                else:
                    print(f"ALERTA: Falta registrar un sensor de PRESIÓN para el dispositivo {dispositivo.nombre}")

            return JsonResponse({'status': 'success', 'mensaje': 'Datos procesados'}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'El formato JSON es inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Solo se permiten peticiones POST'}, status=405)

# --- NUEVAS VISTAS PARA ANGULAR (FRONTEND) ---

def obtener_ultimos_datos(request):
    """
    Angular consulta esta vista para llenar las 3 tarjetas principales del Dashboard.
    Busca el último registro de cada sensor y lo devuelve.
    """
    if request.method == 'GET':
        try:
            # Usamos fragmentos cortos ('temp', 'hum', 'pres') para evitar fallos por tildes o nombres largos
            ultima_temp = LecturaSensor.objects.filter(sensor__tipo_variable__nombre__icontains='temp').order_by('-id').first()
            ultima_hum = LecturaSensor.objects.filter(sensor__tipo_variable__nombre__icontains='hum').order_by('-id').first()
            ultima_pres = LecturaSensor.objects.filter(sensor__tipo_variable__nombre__icontains='pres').order_by('-id').first()

            datos = {
                # Convertimos explícitamente a float para quitar los decimales en texto (ej. '40.000' -> 40.0)
                'temperatura': float(ultima_temp.valor) if ultima_temp else 0,
                'humedad': float(ultima_hum.valor) if ultima_hum else 0,
                'presion': float(ultima_pres.valor) if ultima_pres else 0,
            }
            return JsonResponse(datos, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Solo método GET permitido'}, status=405)

def obtener_historial(request):
    """
    Angular consulta esta vista para armar las gráficas de la pestaña Reportes.
    Por ahora enviamos una estructura base que luego conectaremos con consultas por día.
    """
    if request.method == 'GET':
        datos_historial = {
            'dias': ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo'],
            'riesgo': [65, 72, 88, 95, 82, 60, 55] 
        }
        return JsonResponse(datos_historial, status=200)


@csrf_exempt # Desactivamos seguridad temporalmente para que Angular pueda enviar comandos
def control_dispositivo(request):
    """
    Angular envía comandos POST a esta vista cuando oprimes "Encender Ventilador" o "Reiniciar".
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            equipo = data.get('equipo')
            accion = data.get('accion')

            # Aquí es donde en el futuro enviaremos el comando de vuelta al ESP32 (ej. por MQTT o guardándolo en una tabla)
            print(f"=== COMANDO DE INTERFAZ RECIBIDO: {equipo} -> {accion} ===")

            return JsonResponse({'status': 'success', 'mensaje': f'Orden recibida para {equipo}'}, status=200)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
            
    return JsonResponse({'error': 'Solo método POST permitido'}, status=405)