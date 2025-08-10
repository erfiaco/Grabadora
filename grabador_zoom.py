import sounddevice as sd
import soundfile as sf
import numpy as np
import scipy.io.wavfile as wav
import datetime
import time
import os
from gpiozero import Button

# ===== CONFIGURACION =====
sample_rate = 44100
channels = 2
mute = False
grabando = False
reproducir_despues = False
reproduciendo = False
ultimo_archivo = None
buffer = []
esperando_inicio = True
LOOPS_DIR = "loops"

# Crear carpeta loops si no existe
if not os.path.exists(LOOPS_DIR):
    os.makedirs(LOOPS_DIR)

# ===== BOTONES =====
btn_grabar = Button(19)   # Iniciar grabacion
btn_mute = Button(6)      # Silenciar/desmutear
btn_play = Button(13)     # Detener grabacion y reproducir desde inicio (loop)
btn_stop = Button(26)     # Detener todo

# ===== FUNCIONES =====
def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_menu():
    clear_screen()
    print("=== MENU GRABADORA ===")
    print(f"Mute: {'ON' if mute else 'OFF'}")
    if ultimo_archivo:
        print(f"Ultimo archivo: {os.path.basename(ultimo_archivo)}")
    print("Esperando pulsacion de botones...")

def callback(indata, frames, time_info, status):
    global mute
    if status:
        print(status)
    if mute:
        indata = np.zeros_like(indata)
    buffer.append(indata.copy())

def reproducir_archivo(nombre_archivo):
    global reproduciendo
    if not os.path.exists(nombre_archivo):
        print("\nArchivo no encontrado")
        return
    
    print(f"\nReproduciendo {os.path.basename(nombre_archivo)} en bucle...")
    data, fs = sf.read(nombre_archivo, dtype='float32')
    
    reproduciendo = True
    while reproduciendo:
        sd.play(data, fs, device='pulse')
        sd.wait()

# ===== ACCIONES DE BOTONES =====
def iniciar_grabacion():
    global grabando, esperando_inicio
    if esperando_inicio:
        grabando = True
        esperando_inicio = False
        print("\nComenzando grabacion...")

def alternar_mute():
    global mute
    mute = not mute
    print("\nMute activado" if mute else "\nMute desactivado")

def detener_y_reproducir():
    global grabando, reproducir_despues
    if grabando:
        reproducir_despues = True
        grabando = False
        print("\nGrabacion detenida, reproduciendo en bucle...")

def detener_todo():
    global grabando, reproduciendo
    grabando = False
    reproduciendo = False
    print("\nTodo detenido")

# ===== ASIGNAR FUNCIONES A BOTONES =====
btn_grabar.when_pressed = iniciar_grabacion
btn_mute.when_pressed = alternar_mute
btn_play.when_pressed = detener_y_reproducir
btn_stop.when_pressed = detener_todo

# ===== PROGRAMA PRINCIPAL =====
mostrar_menu()

# Espera para comenzar grabacion
while esperando_inicio:
    time.sleep(0.1)

# Grabacion
if grabando:
    with sd.InputStream(samplerate=sample_rate, channels=channels, callback=callback):
        while grabando:
            sd.sleep(200)

# Guardar archivo si se grabo algo
if buffer:
    audio = np.concatenate(buffer)
    nombre_archivo = os.path.join(LOOPS_DIR, f"grabacion_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.wav")
    wav.write(nombre_archivo, sample_rate, audio)
    ultimo_archivo = nombre_archivo
    print(f"\nGrabacion guardada como: {os.path.basename(nombre_archivo)}")

    # Reproduccion en bucle si se solicito
    if reproducir_despues:
        reproducir_archivo(nombre_archivo)

print("\nFin del programa")