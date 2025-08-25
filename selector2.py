import os
import subprocess
import time
import RPi.GPIO as GPIO

# Configuración de pines GPIO (ajusta según tu configuración)
BUTTON_SELECT = 26  # Botón para seleccionar
BUTTON_UP = 6      # Botón para subir en la lista
BUTTON_DOWN = 13    # Botón para bajar en la lista
BUTTON_BACK = 19    # Botón para volver

# Configuración de GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_SELECT, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_UP, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_DOWN, GPIO.IN, pull_up_down=GPIO.PUD_UP)
GPIO.setup(BUTTON_BACK, GPIO.IN, pull_up_down=GPIO.PUD_UP)

PROGRAMS_FOLDER = "/home/Javo/Proyects/Looper/"

class ProgramSelector:
    def __init__(self):
        self.programs = self.get_programs_list()
        self.selected_index = 0
        self.current_vt = 2  # Empezamos en VT2 (F2)
        
    def get_programs_list(self):
        """Obtiene la lista de programas"""
        try:
            files = os.listdir(PROGRAMS_FOLDER)
            programs = []
            for f in files:
                full_path = os.path.join(PROGRAMS_FOLDER, f)
                if os.path.isfile(full_path) and not f.startswith('.'):
                    programs.append(f)
            return sorted(programs)
        except:
            print("Error: No se pudo leer la carpeta Looper/")
            return []
    
    def display_menu(self):
        """Muestra el menú"""
        os.system('clear')
        print("🎮 SELECTOR DE PROGRAMAS")
        print("========================")
        print("↑/↓: Navegar  |  SELECT: Ejecutar en F2/F3")
        print("BACK: Salir   |  CTRL+C: Salir")
        print("========================")
        
        for i, program in enumerate(self.programs):
            prefix = "➤ " if i == self.selected_index else "  "
            print(f"{prefix}[{i+1}] {program}")
        
        print("========================")
        print(f"Próximo programa en: F{self.current_vt}")
    
    def run_program_in_vt(self):
        """Ejecuta programa en consola virtual separada"""
        if not self.programs:
            return False
            
        program_name = self.programs[self.selected_index]
        program_path = os.path.join(PROGRAMS_FOLDER, program_name)
        
        print(f"🔽 Ejecutando {program_name} en F{self.current_vt}...")
        time.sleep(1)
        
        try:
            # Determinar comando según extensión
            if program_name.endswith('.py'):
                cmd = f"python3 '{program_path}'"
            elif program_name.endswith('.sh'):
                cmd = f"bash '{program_path}'"
            else:
                cmd = f"'{program_path}'"
            
            # Ejecutar en consola virtual
            full_cmd = f"sudo openvt -c {self.current_vt} -- {cmd}"
            subprocess.Popen(full_cmd, shell=True)
            
            # Cambiar a esa consola
            os.system(f"sudo chvt {self.current_vt}")
            
            # Rotar entre VT2 y VT3
            self.current_vt = 3 if self.current_vt == 2 else 2
            
            return True
            
        except Exception as e:
            print(f"❌ Error: {e}")
            return False
    
    def check_buttons(self):
        """Verifica los botones"""
        try:
            # Botón UP
            if GPIO.input(BUTTON_UP) == GPIO.LOW:
                time.sleep(0.2)
                if GPIO.input(BUTTON_UP) == GPIO.LOW:
                    self.selected_index = (self.selected_index - 1) % len(self.programs)
                    return True
            
            # Botón DOWN
            if GPIO.input(BUTTON_DOWN) == GPIO.LOW:
                time.sleep(0.2)
                if GPIO.input(BUTTON_DOWN) == GPIO.LOW:
                    self.selected_index = (self.selected_index + 1) % len(self.programs)
                    return True
            
            # Botón SELECT
            if GPIO.input(BUTTON_SELECT) == GPIO.LOW:
                time.sleep(0.2)
                if GPIO.input(BUTTON_SELECT) == GPIO.LOW:
                    self.run_program_in_vt()
                    return True
            
            # Botón BACK - Volver al selector desde cualquier VT
            if GPIO.input(BUTTON_BACK) == GPIO.LOW:
                time.sleep(0.2)
                if GPIO.input(BUTTON_BACK) == GPIO.LOW:
                    os.system("sudo chvt 1")  # Volver a VT1 (donde está el selector)
                    return True
            
        except Exception as e:
            print(f"Error en botones: {e}")
        
        return False

def main():
    selector = ProgramSelector()
    
    if not selector.programs:
        print("❌ No hay programas en Looper/")
        print("Coloca tus programas en /home/Javo/Proyects/Looper/")
        time.sleep(3)
        return
    
    try:
        while True:
            selector.display_menu()
            selector.check_buttons()
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\n👋 Saliendo...")
    finally:
        GPIO.cleanup()

if __name__ == "__main__":
    main()