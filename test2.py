import sounddevice as sd
import soundfile as sf
import numpy as np
import threading
import time

# ===== NUEVA IMPLEMENTACIÓN PARA LOOPER =====
class Looper:
    def __init__(self):
        self.audio_data = None
        self.sample_rate = 44100
        self.is_playing = False
        self.current_position = 0
        self.stream = None
        self.lock = threading.Lock()
    
    def load_audio(self, filepath):
        """Cargar audio para loopear"""
        try:
            data, sr = sf.read(filepath, dtype='float32')
            self.audio_data = data
            self.sample_rate = sr
            self.current_position = 0
            print(f"Audio cargado: {filepath}")
            return True
        except Exception as e:
            print(f"Error cargando audio: {e}")
            return False
    
    def audio_callback(self, outdata, frames, time_info, status):
        """Callback para reproducción continua en tiempo real"""
        if status:
            print(status)
        
        with self.lock:
            if self.audio_data is None or not self.is_playing:
                outdata.fill(0)
                return
            
            available = len(self.audio_data) - self.current_position
            if available >= frames:
                # Suficiente audio disponible
                outdata[:] = self.audio_data[self.current_position:self.current_position + frames]
                self.current_position += frames
            else:
                # Llegamos al final, loopear
                outdata[:available] = self.audio_data[self.current_position:]
                remaining = frames - available
                outdata[available:] = self.audio_data[:remaining]
                self.current_position = remaining
    
    def start_loop(self):
        """Iniciar reproducción en bucle"""
        if self.audio_data is None:
            print("No hay audio cargado")
            return False
        
        with self.lock:
            if self.is_playing:
                return True  # Ya está reproduciendo
            
            self.is_playing = True
            self.current_position = 0
            
            # Crear stream de salida
            try:
                self.stream = sd.OutputStream(
                    samplerate=self.sample_rate,
                    channels=self.audio_data.shape[1] if len(self.audio_data.shape) > 1 else 1,
                    callback=self.audio_callback,
                    blocksize=256,  # Bloque pequeño para baja latencia
                    dtype='float32'
                )
                self.stream.start()
                print("Loop iniciado")
                return True
            except Exception as e:
                print(f"Error iniciando stream: {e}")
                self.is_playing = False
                return False
    
    def stop_loop(self):
        """Detener reproducción"""
        with self.lock:
            if self.stream:
                self.stream.stop()
                self.stream.close()
                self.stream = None
            self.is_playing = False
            print("Loop detenido")

# ===== INSTANCIA GLOBAL DEL LOOPER =====
looper = Looper()

# ===== MODIFICAR LAS FUNCIONES EXISTENTES =====
def reproducir_en_bucle():
    """Función simplificada para el hilo"""
    if looper.start_loop():
        # Mantener el hilo vivo mientras se reproduce
        while looper.is_playing and not exit_event.is_set():
            time.sleep(0.1)

def manejar_play():
    global grabando, reproduciendo
    print(f"DEBUG: manejar_play() - grabando: {grabando}")
    
    if grabando:
        print("DEBUG: Caso 1 - Grabando = True")
        grabando = False
        archivo = guardar_grabacion()
        if archivo:
            if looper.load_audio(archivo):
                print("\nGrabación detenida, iniciando reproducción en bucle...")
                reproduciendo = True
                Thread(target=reproducir_en_bucle, daemon=True).start()
    elif ultimo_archivo:
        print("DEBUG: Caso 2 - Hay último archivo")
        if reproduciendo:
            print("DEBUG: Ya está reproduciendo, deteniendo...")
            detener_reproduccion()
        else:
            print("DEBUG: Iniciando reproducción desde último archivo")
            if looper.load_audio(ultimo_archivo):
                print("\nIniciando reproducción en bucle...")
                reproduciendo = True
                Thread(target=reproducir_en_bucle, daemon=True).start()
    else:
        print("\nNo hay grabación para reproducir")
    mostrar_estado()

def detener_reproduccion():
    global reproduciendo
    print(f"DEBUG: detener_reproduccion() - reproduciendo antes: {reproduciendo}")
    if reproduciendo:
        looper.stop_loop()
        reproduciendo = False
        print("\nReproducción detenida")
        mostrar_estado()
    print(f"DEBUG: detener_reproduccion() - reproduciendo después: {reproduciendo}")