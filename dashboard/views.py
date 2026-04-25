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
                sensor_temp = Sensor.objects.filter(dispositivo=dispositivo, tipo_variable__nombre__icontains='Temperatura').first()
                if sensor_temp:
                    LecturaSensor.objects.create(
                        sensor=sensor_temp,
                        valor=data['temperatura'],
                        sensacion_termica=data.get('sensacion_termica') # Guardamos el Heat Index aquí
                    )

            # 4. Guardar Humedad
            if 'humedad' in data:
                sensor_hum = Sensor.objects.filter(dispositivo=dispositivo, tipo_variable__nombre__icontains='Humedad').first()
                if sensor_hum:
                    LecturaSensor.objects.create(sensor=sensor_hum, valor=data['humedad'])

            # 5. Guardar Presión
            if 'presion' in data:
                sensor_pres = Sensor.objects.filter(dispositivo=dispositivo, tipo_variable__nombre__icontains='Presión').first()
                if sensor_pres:
                    LecturaSensor.objects.create(sensor=sensor_pres, valor=data['presion'])

            return JsonResponse({'status': 'success', 'mensaje': 'Datos de la estación guardados correctamente'}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({'error': 'El formato JSON es inválido'}, status=400)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)

    return JsonResponse({'error': 'Solo se permiten peticiones POST'}, status=405)