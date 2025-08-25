import sounddevice as sd
import soundfile as sf
import numpy as np
import scipy.io.wavfile as wav
import datetime
import time
import os
import signal
from gpiozero import Button
from threading import Event, Thread, Lock
import LCD_I2C_classe as LCD
import threading

# Force gpiozero to use RPi.GPIO
os.environ["GPIOZERO_PIN_FACTORY"] = "rpigpio"

# Initialize globals
lcd = LCD.LCD_I2C()
sample_rate = 44100
channels = 2
mute = False
grabando = False
reproduciendo = False
ultimo_archivo = None
buffer = []
LOOPS_DIR = "loops"
exit_event = Event()
ultimo_archivo_lock = Lock()
playback_thread = None  # Track playback thread

# Crear carpeta loops si no existe
if not os.path.exists(LOOPS_DIR):
    os.makedirs(LOOPS_DIR)

# Botones con debounce
btn_grabar = Button(26, bounce_time=0.1)
btn_mute = Button(6, bounce_time=0.1)
btn_play = Button(13, bounce_time=0.1)
btn_stop = Button(19, bounce_time=0.1)

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
    lcd.write(f"Estado: {'Grabando' if grabando else 'Reproduciendo' if reproduciendo else 'En espera'}", 1)
    lcd.write(f"Mute: {'ON' if mute else 'OFF'}", 2)

def callback_grabacion(indata, frames, time_info, status):
    global mute
    if status:
        print(f"Input stream status: {status}")
    if mute:
        indata = np.zeros_like(indata)
    if grabando and not exit_event.is_set():
        buffer.append(indata.copy())

def reproducir_en_bucle():
    global reproduciendo, playback_thread
    with ultimo_archivo_lock:
        if not ultimo_archivo or not os.path.exists(ultimo_archivo):
            print(f"\nNo hay archivo para reproducir. ultimo_archivo: {ultimo_archivo}")
            reproduciendo = False
            mostrar_estado()
            return
        archivo = ultimo_archivo
    
    print(f"\nReproduciendo {os.path.basename(archivo)} en bucle infinito...")
    try:
        data, fs = sf.read(archivo, dtype='float32')
    except Exception as e:
        print(f"\nError al leer archivo: {e}")
        reproduciendo = False
        mostrar_estado()
        return

    reproduciendo = True
    while reproduciendo and not exit_event.is_set():
        try:
            print("\nStarting playback cycle")  # Debug log
            sd.play(data, fs, device='pulse')
            sd.wait()
            print("\nPlayback cycle completed")  # Debug log
            if not reproduciendo or exit_event.is_set():
                print("\nStopping playback due to state change")  # Debug log
                sd.stop()
                break
        except Exception as e:
            print(f"\nError en reproducción: {e}")
            reproduciendo = False
            break
    reproduciendo = False
    playback_thread = None
    print("\nReproducción terminada")
    mostrar_estado()

def guardar_grabacion():
    global buffer, ultimo_archivo
    if buffer:
        audio = np.concatenate(buffer)
        nombre_archivo = os.path.join(LOOPS_DIR, f"loop_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.wav")
        try:
            wav.write(nombre_archivo, sample_rate, audio)
            with ultimo_archivo_lock:
                ultimo_archivo = nombre_archivo
            print(f"\nLoop guardado: {os.path.basename(nombre_archivo)}")
            buffer = []
            return nombre_archivo
        except Exception as e:
            print(f"\nError al guardar grabación: {e}")
            return None
    return None

def iniciar_detener_grabacion():
    global grabando, buffer, reproduciendo
    if reproduciendo:
        detener_reproduccion()
    
    if not exit_event.is_set():
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
    lcd.write("Mute ON" if mute else "Mute OFF", 2)
    mostrar_estado()

def manejar_play():
    global grabando, reproduciendo, playback_thread
    if exit_event.is_set():
        return
    print("\nPlay button pressed")  # Debug log
    if grabando:
        grabando = False
        archivo = guardar_grabacion()
        if archivo:
            print("\nGrabación detenida, iniciando reproducción en bucle...")
            with ultimo_archivo_lock:
                if not exit_event.is_set() and not playback_thread:
                    reproduciendo = True
                    playback_thread = Thread(target=reproducir_en_bucle, daemon=True)
                    playback_thread.start()
    elif ultimo_archivo:
        with ultimo_archivo_lock:
            if reproduciendo:
                print("\nStopping existing playback")  # Debug log
                detener_reproduccion()
            else:
                print("\nIniciando reproducción en bucle...")
                if not exit_event.is_set() and not playback_thread:
                    reproduciendo = True
                    playback_thread = Thread(target=reproducir_en_bucle, daemon=True)
                    playback_thread.start()
    else:
        print("\nNo hay grabación para reproducir")
    mostrar_estado()

def detener_reproduccion():
    global reproduciendo, grabando, playback_thread
    if reproduciendo:
        reproduciendo = False
        sd.stop()
        playback_thread = None
        print("\nReproducción detenida")
    if grabando:
        grabando = False
        print("\nGrabación detenida por STOP")
        guardar_grabacion()
    mostrar_estado()

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

# Configurar manejadores de señales
try:
    if threading.current_thread() is threading.main_thread():
        signal.signal(signal.SIGINT, handler_senal)
        signal.signal(signal.SIGTERM, handler_senal)
    else:
        print("Advertencia: No se pueden configurar manejadores de señales fuera del hilo principal")
except ValueError as e:
    print(f"Error al configurar manejadores de señales: {e}")

# Asignar funciones a botones
btn_grabar.when_pressed = iniciar_detener_grabacion
btn_mute.when_pressed = alternar_mute
btn_play.when_pressed = manejar_play
btn_stop.when_pressed = detener_reproduccion

# Programa principal
mostrar_estado()
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
    lcd.clear()
    try:
        lcd.close()  # Assuming LCD_I2C_classe has a close method
    except AttributeError:
        pass
    grabando = False
    reproduciendo = False
    sd.stop()
    if buffer:
        guardar_grabacion()
    print("Programa terminado correctamente")
    os._exit(0)