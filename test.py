import sounddevice as sd
import soundfile as sf
import numpy as np
import scipy.io.wavfile as wav
import datetime
import time
import os
import signal
from gpiozero import Button
from threading import Event, Thread

# ===== CONFIGURACION =====
sample_rate = 44100
channels = 2
mute = False
grabando = False
reproduciendo = False
ultimo_archivo = None
buffer = []
LOOPS_DIR = "loops"
exit_event = Event()

# Crear carpeta loops si no existe
if not os.path.exists(LOOPS_DIR):
    os.makedirs(LOOPS_DIR)

# ===== BOTONES =====
btn_grabar = Button(19)   # Iniciar/detener grabacion
btn_mute = Button(6)      # Silenciar/desmutear
btn_play = Button(13)     # Detener grabación y reproducir en bucle
btn_stop = Button(26)     # Detener reproducción/Salir (3 segundos)

# ===== FUNCIONES =====
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_estado():
    clear_screen()
    print("=== LOOPER RASPBERRY ===")
    print(f"Mute: {'ON' if mute else 'OFF'}")
    print(f"Estado: {'Grabando' if grabando else 'Reproduciendo' if reproduciendo else 'En espera'}")
    if ultimo_archivo:
        print(f"Último loop: {os.path.basename(ultimo_archivo)}")
    print("Esperando acción...")
    print("Mantén STOP 3 segundos para salir")

def callback_grabacion(indata, frames, time_info, status):
    global mute
    if status:
        print(status)
    if mute:
        indata = np.zeros_like(indata)
    if grabando and not exit_event.is_set():
        buffer.append(indata.copy())

def reproducir_loop():
    global reproduciendo
    if not ultimo_archivo or not os.path.exists(ultimo_archivo):
        print("\nNo hay archivo para reproducir")
        return
    
    print(f"\nReproduciendo {os.path.basename(ultimo_archivo)} en bucle...")
    data, fs = sf.read(ultimo_archivo, dtype='float32')
    
    reproduciendo = True
    while reproduciendo and not exit_event.is_set():
        sd.play(data, fs, device='pulse')
        sd.wait()
        if not reproduciendo or exit_event.is_set():
            break

def guardar_grabacion():
    global buffer, ultimo_archivo
    if buffer:
        audio = np.concatenate(buffer)
        nombre_archivo = os.path.join(LOOPS_DIR, f"loop_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        wav.write(nombre_archivo, sample_rate, audio)
        ultimo_archivo = nombre_archivo
        print(f"\nLoop guardado: {os.path.basename(nombre_archivo)}")
        buffer = []
        return nombre_archivo
    return None

# ===== MANEJO DE SALIDA =====
def monitorear_salida():
    while not exit_event.is_set():
        if btn_stop.is_pressed:
            tiempo_inicio = time.time()
            while btn_stop.is_pressed and not exit_event.is_set():
                if time.time() - tiempo_inicio >= 3:
                    print("\nSolicitud de salida detectada...")
                    exit_event.set()
                    return
                time.sleep(0.1)
        time.sleep(0.1)

def handler_senal(signum, frame):
    print("\nSeñal de interrupción recibida...")
    exit_event.set()

# ===== ACCIONES DE BOTONES =====
def iniciar_detener_grabacion():
    global grabando, buffer
    if not reproduciendo and not exit_event.is_set():
        if not grabando:
            buffer = []
            grabando = True
            print("\nIniciando grabación...")
        else:
            grabando = False
            print("\nDeteniendo grabación...")
            guardar_grabacion()
        mostrar_estado()

def alternar_mute():
    global mute
    mute = not mute
    print("\nMute " + ("activado" if mute else "desactivado"))
    mostrar_estado()

def detener_grabar_y_reproducir():
    global grabando, reproduciendo
    if grabando:
        # Detener grabación primero
        grabando = False
        archivo = guardar_grabacion()
        print("\nGrabación detenida, iniciando reproducción en bucle...")
        
        # Iniciar reproducción en bucle del nuevo archivo
        if archivo:
            reproduciendo = True
            Thread(target=reproducir_loop, daemon=True).start()
    elif ultimo_archivo and not exit_event.is_set():
        if reproduciendo:
            detener_reproduccion()
        else:
            reproduciendo = True
            Thread(target=reproducir_loop, daemon=True).start()
    mostrar_estado()

def detener_reproduccion():
    global reproduciendo
    if reproduciendo:
        reproduciendo = False
        sd.stop()
        print("\nReproducción detenida")
        mostrar_estado()

# Configurar manejadores de señales
signal.signal(signal.SIGINT, handler_senal)
signal.signal(signal.SIGTERM, handler_senal)

# Asignar funciones a botones
btn_grabar.when_pressed = iniciar_detener_grabacion
btn_mute.when_pressed = alternar_mute
btn_play.when_pressed = detener_grabar_y_reproducir
btn_stop.when_pressed = detener_reproduccion

# ===== PROGRAMA PRINCIPAL =====
mostrar_estado()

# Iniciar hilos
Thread(target=monitorear_salida, daemon=True).start()

try:
    with sd.InputStream(samplerate=sample_rate, channels=channels, 
                       callback=callback_grabacion, blocksize=1024):
        while not exit_event.is_set():
            time.sleep(0.1)
                
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    print("\nLimpiando recursos...")
    grabando = False
    reproduciendo = False
    sd.stop()
    if buffer:
        guardar_grabacion()
    print("Programa terminado correctamente")
    os._exit(0)