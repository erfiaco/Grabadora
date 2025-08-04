import sounddevice as sd
import soundfile as sf
import numpy as np
import scipy.io.wavfile as wav
import datetime
import time
import os
from pynput import keyboard

sample_rate = 44100
channels = 2
mute = False
grabando = False
reproducir_despues = False
reproduciendo = False
ultimo_archivo = None
buffer = []
esperando_inicio = True

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def mostrar_menu(ultimo_archivo=None):
    clear_screen()
    print("=== MENÚ GRABADORA ===")
    print("1. Presiona [s] para comenzar a grabar")
    if ultimo_archivo:
        print(f"Último archivo: {ultimo_archivo}")
        print("2. Presiona [p] para reproducir el último archivo")
    print("3. Presiona [q] para salir")
    print("\nEsperando comando...")

def callback(indata, frames, time, status):
    global mute
    if status:
        print(status)
    if mute:
        indata = np.zeros_like(indata)
    buffer.append(indata.copy())

def on_press(key):
    global mute, grabando, reproducir_despues, esperando_inicio, reproduciendo

    try:
        if key.char == 's' and esperando_inicio:
            grabando = True
            esperando_inicio = False
            print("\n🎙️ Comenzando grabación...")
        elif key.char == 'a' and not esperando_inicio:
            mute = not mute
            print("\n🎚️ Mute activado" if mute else "\n🔊 Mute desactivado")
        elif key.char == 'h' and grabando:
            reproducir_despues = True
            grabando = False
            return False
        elif key.char == 'p' and ultimo_archivo and not grabando:
            reproducir_archivo(ultimo_archivo)
            mostrar_menu(ultimo_archivo)  # Mostrar menú después de reproducir
        elif key.char == 'q':
            return False  # Salir del programa
    except AttributeError:
        if key == keyboard.Key.space:
            if grabando:
                grabando = False
                return False
            elif reproduciendo:
                reproduciendo = False
                print("\n⏹️ Reproducción detenida")

def reproducir_archivo(nombre_archivo):
    global reproduciendo
    if not os.path.exists(nombre_archivo):
        print("\n❌ Archivo no encontrado")
        return
    
    print(f"\n▶️ Reproduciendo {nombre_archivo} en bucle (pulsa espacio para detener)...")
    data, fs = sf.read(nombre_archivo, dtype='float32')
    
    reproduciendo = True
    with keyboard.Listener(on_press=on_press) as listener:
        while reproduciendo:
            sd.play(data, fs, device='pulse')
            sd.wait()
            if not reproduciendo:
                break
        listener.stop()

# Menú principal inicial
mostrar_menu()

with keyboard.Listener(on_press=on_press) as listener:
    # Espera para comenzar grabación
    while esperando_inicio:
        time.sleep(0.1)
    
    # Grabación
    if grabando:
        with sd.InputStream(samplerate=sample_rate, channels=channels, callback=callback):
            while grabando:
                sd.sleep(200)
    listener.stop()

# Guardar archivo si se grabó algo
if buffer:
    audio = np.concatenate(buffer)
    nombre_archivo = f"grabacion_{datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.wav"
    wav.write(nombre_archivo, sample_rate, audio)
    ultimo_archivo = nombre_archivo
    print(f"\n✅ Grabación guardada como: {nombre_archivo}")

    # Reproducción en bucle si se solicitó
    if reproducir_despues:
        reproducir_archivo(nombre_archivo)

# Menú post-grabación
if ultimo_archivo:
    while True:
        mostrar_menu(ultimo_archivo)
        with keyboard.Listener(on_press=on_press) as listener:
            # Esperar 1 segundo para evitar consumo excesivo de CPU
            time.sleep(1)
            listener.stop()
else:
    print("\n❌ No se grabó ningún audio. Saliendo...")