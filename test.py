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
import LCD_I2C_classe as LCD
import psutil   # <=== añadido para monitor de CPU/memoria

lcd = LCD.LCD_I2C()

# Force gpiozero to use RPi.GPIO
os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio"

# ===== CONFIGURACION =====
CHUNK=2048
sample_rate = 44100
channels = 1
mute = False
grabando = False
reproduciendo = False
ultimo_archivo = None
buffer = []
LOOPS_DIR = "loops"
exit_event = Event()

# Contadores de errores de audio
underruns = 0
overruns = 0

# Crear carpeta loops si no existe
if not os.path.exists(LOOPS_DIR):
    os.makedirs(LOOPS_DIR)

# ===== BOTONES =====
btn_grabar = Button(26)   # Iniciar/detener grabacion
btn_mute = Button(6)      # Silenciar/desmutear
btn_play = Button(13)     # Reproducir en bucle (siempre)
btn_stop = Button(19)     # Detener reproducir (3 segundos)

# ===== FUNCIONES =====
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_estado():
    clear_screen()
    print("=== LOOPER RASPBERRY ===")
    print(f"Mute: {'ON' if mute else 'OFF'}")
    print(f"Estado: {'Grabando' if grabando else 'Reproduciendo' if reproduciendo else 'En espera'}")
    if ultimo_archivo:
        print(f"ultimo loop: {os.path.basename(ultimo_archivo)}")
    print("Esperando accion")
    print("Mantener STOP 3 segundos para salir")
    lcd.write(f"Estado: {'Grabando' if grabando else 'Reproduciendo' if reproduciendo else 'En espera'}",1)
    lcd.write(f"Mute: {'ON' if mute else 'OFF'}",2)

def callback_grabacion(indata, frames, time_info, status):
    global mute, overruns
    if status:
        print(status)
        if status.input_overflow:
            overruns += 1
    if mute:
        indata = np.zeros_like(indata)
    if grabando and not exit_event.is_set():
        buffer.append(indata.copy())

def reproducir_en_bucle():
    global reproduciendo, underruns
    if not ultimo_archivo or not os.path.exists(ultimo_archivo):
        print(f"\nNo hay archivo para reproducir. ultimo_archivo: {ultimo_archivo}")
        return
    
    print(f"\nReproduciendo {os.path.basename(ultimo_archivo)} en bucle infinito...")
    data, fs = sf.read(ultimo_archivo, dtype='float32')
    
    reproduciendo = True
    while reproduciendo and not exit_event.is_set():
        try:
            sd.play(data, fs, device='pulse')
            sd.wait()
        except sd.PortAudioError as e:
            print(f"Error en reproduccion: {e}")
            underruns += 1
            time.sleep(0.1)
    
    print("Reproduccion terminada")
    reproduciendo = False

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

# ===== MONITOR DEL SISTEMA =====
def monitor_sistema():
    global underruns, overruns
    while not exit_event.is_set():
        cpu = psutil.cpu_percent(interval=1)
        memoria = psutil.virtual_memory().percent
        try:
            lat_in = sd.query_devices(None, 'input')['default_low_input_latency']
            lat_out = sd.query_devices(None, 'output')['default_low_output_latency']
        except Exception:
            lat_in, lat_out = 0, 0
        print(f"[MONITOR] CPU: {cpu:.1f}% | Memoria: {memoria:.1f}% | Lat_in: {lat_in*1000:.1f} ms | Lat_out: {lat_out*1000:.1f} ms | Overruns: {overruns} | Underruns: {underruns}")
        time.sleep(1)

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
    print("\nSenal de interrupcion recibida...")
    exit_event.set()

# ===== ACCIONES DE BOTONES =====
def iniciar_detener_grabacion():
    global grabando, buffer, reproduciendo
    if reproduciendo:
        detener_reproduccion()
    
    if not exit_event.is_set():
        if not grabando:
            buffer = []
            grabando = True
            print("\nIniciando grabacion")
        else:
            print("heeey")
        mostrar_estado()

def alternar_mute():
    global mute
    mute = not mute
    lcd.write("Mute ON" if mute else "Mute OFF",2)

def manejar_play():
    global grabando, reproduciendo
    if grabando:
        grabando = False
        archivo = guardar_grabacion()
        if archivo:
            print("\nGrabacion detenida, iniciando reproduccion en bucle...")
            reproduciendo = True
            Thread(target=reproducir_en_bucle, daemon=False).start()
    elif ultimo_archivo:
        if reproduciendo:
            detener_reproduccion()
        else:
            print("\nIniciando reproduccion en bucle...")
            reproduciendo = True
            Thread(target=reproducir_en_bucle, daemon=False).start()
    else:
        print("\nNo hay grabacion para reproducir")
    mostrar_estado()

def detener_reproduccion():
    global reproduciendo, grabando
    if reproduciendo:
        reproduciendo = False
        print("\nReproduccion detenida")
    if grabando:
        grabando = False
        print("\nGrabacion detenida por STOP")
        guardar_grabacion()
    mostrar_estado()

# Configurar manejadores de senales
signal.signal(signal.SIGINT, handler_senal)
signal.signal(signal.SIGTERM, handler_senal)

# Asignar funciones a botones
btn_grabar.when_pressed = iniciar_detener_grabacion
btn_mute.when_pressed = alternar_mute
btn_play.when_pressed = manejar_play
btn_stop.when_pressed = detener_reproduccion

# ===== PROGRAMA PRINCIPAL =====
mostrar_estado()

# Iniciar hilos
Thread(target=monitorear_salida, daemon=False).start()
Thread(target=monitor_sistema, daemon=True).start()  # <=== añadido monitor del sistema

try:
    with sd.InputStream(samplerate=sample_rate, channels=channels, 
                       callback=callback_grabacion, blocksize=1024):
        while not exit_event.is_set():
            time.sleep(0.1)
                
except Exception as e:
    print(f"Error: {str(e)}")
finally:
    print("\nLimpiando recursos...")
    lcd.clear()
    grabando = False
    reproduciendo = False
    sd.stop()
    if buffer:
        guardar_grabacion()
    print("Programa terminado correctamente")
    os._exit(0)
