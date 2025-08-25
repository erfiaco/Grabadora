import os
import subprocess
import time
import RPi.GPIO as GPIO
import LCD_I2C_classe as LCD
lcd = LCD.LCD_I2C()

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

# Ruta de la carpeta con los programas
PROGRAMS_FOLDER = "/home/Javo/Proyects/Looper/"

class ProgramSelector:
    def __init__(self):
        self.programs = self.get_programs_list()
        self.selected_index = 0
        self.running_process = None
        self.is_running_program = False
        
    def get_programs_list(self):
        """Obtiene la lista de programas de la carpeta Looper"""
        try:
            files = os.listdir(PROGRAMS_FOLDER)
            # Filtrar archivos ejecutables comunes
            programs = []
            for f in files:
                full_path = os.path.join(PROGRAMS_FOLDER, f)
                if (f.endswith('.py') or f.endswith('.sh') or 
                    os.access(full_path, os.X_OK) and os.path.isfile(full_path)):
                    programs.append(f)
            return sorted(programs)
        except FileNotFoundError:
            print(f"Error: No se encontró la carpeta {PROGRAMS_FOLDER}")
            return []
        except PermissionError:
            print(f"Error: Sin permisos para acceder a {PROGRAMS_FOLDER}")
            return []
    
    def display_menu(self):
        """Muestra el menú en la consola"""
        os.system('clear')  # Limpia la pantalla
        print("=== SELECTOR DE PROGRAMAS ===")
        print("Usa ↑/↓ para navegar, SELECT para elegir")
        print("=============================")
        
        for i, program in enumerate(self.programs):
            if i == self.selected_index:
                print(f"> [{i+1}] {program} <")
            else:
                print(f"  [{i+1}] {program}")
        
        print("=============================")
        print("SELECT: Ejecutar  |  ↑/↓: Navegar")
    
    def display_running_screen(self, program_name):
        """Muestra la pantalla cuando un programa está ejecutándose"""
        os.system('clear')
        print("═" * 40)
        print(f"PROGRAMA EN EJECUCIÓN: {program_name}")
        print("═" * 40)
        print("Presiona el botón BACK para detener")
        print("y volver al selector")
        print("═" * 40)
    
    def run_selected_program(self):
        """Ejecuta el programa seleccionado"""
        if not self.programs:
            print("No hay programas disponibles")
            return False
            
        selected_program = self.programs[self.selected_index]
        program_path = os.path.join(PROGRAMS_FOLDER, selected_program)
        
        print(f"Iniciando: {selected_program}")
        time.sleep(1)
        
        try:
            # Detener programa anterior si está corriendo
            self.stop_current_program()
            
            # Preparar el comando según el tipo de archivo
            if selected_program.endswith('.py'):
                cmd = ['python3', program_path]
            elif selected_program.endswith('.sh'):
                cmd = ['bash', program_path]
            else:
                cmd = [program_path]
            
            # Ejecutar el programa en segundo plano
            self.running_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_running_program = True
            
            # Mostrar pantalla de ejecución
            self.display_running_screen(selected_program)
            return True
            
        except Exception as e:
            print(f"Error al ejecutar {selected_program}: {e}")
            print("Asegúrate de que el archivo tiene permisos de ejecución:")
            print(f"chmod +x {program_path}")
            time.sleep(2)
            return False
    
    def stop_current_program(self):
        """Detiene el programa actualmente en ejecución"""
        if self.running_process:
            try:
                self.running_process.terminate()
                # Esperar un poco a que termine
                time.sleep(0.5)
                if self.running_process.poll() is None:
                    self.running_process.kill()
            except:
                pass
            finally:
                self.running_process = None
                self.is_running_program = False
    
    def check_buttons_menu(self):
        """Verifica botones cuando estamos en el menú"""
        try:
            # Botón UP
            if GPIO.input(BUTTON_UP) == GPIO.LOW:
                time.sleep(0.2)
                if GPIO.input(BUTTON_UP) == GPIO.LOW:
                    self.selected_index = (self.selected_index - 1) % len(self.programs)
                    return "menu"
            
            # Botón DOWN
            if GPIO.input(BUTTON_DOWN) == GPIO.LOW:
                time.sleep(0.2)
                if GPIO.input(BUTTON_DOWN) == GPIO.LOW:
                    self.selected_index = (self.selected_index + 1) % len(self.programs)
                    return "menu"
            
            # Botón SELECT
            if GPIO.input(BUTTON_SELECT) == GPIO.LOW:
                time.sleep(0.2)
                if GPIO.input(BUTTON_SELECT) == GPIO.LOW:
                    if self.run_selected_program():
                        return "running"
                    else:
                        return "menu"
            
        except Exception as e:
            print(f"Error leyendo botones: {e}")
        
        return "menu"
    
    def check_buttons_running(self):
        """Verifica botones cuando un programa está ejecutándose"""
        try:
            # Botón BACK para volver al menú
            if GPIO.input(BUTTON_BACK) == GPIO.LOW:
                time.sleep(0.2)
                if GPIO.input(BUTTON_BACK) == GPIO.LOW:
                    print("Deteniendo programa...")
                    self.stop_current_program()
                    time.sleep(1)
                    return "menu"
            
            # Verificar si el programa terminó por sí solo
            if self.running_process and self.running_process.poll() is not None:
                print("El programa terminó por sí solo")
                self.is_running_program = False
                return "menu"
                
        except Exception as e:
            print(f"Error leyendo botones: {e}")
        
        return "running"

def main():
    selector = ProgramSelector()
    
    if not selector.programs:
        print("No se encontraron programas en la carpeta Looper/")
        print("Asegúrate de que:")
        print(f"1. La carpeta {PROGRAMS_FOLDER} existe")
        print("2. Hay programas dentro (archivos .py, .sh o ejecutables)")
        print("3. Los programas tienen permisos de ejecución: chmod +x /home/Javo/Proyects/Looper/*")
        time.sleep(5)
        return
    
    current_state = "menu"
    
    try:
        while True:
            if current_state == "menu":
                selector.display_menu()
                current_state = selector.check_buttons_menu()
            elif current_state == "running":
                current_state = selector.check_buttons_running()
            
            time.sleep(0.1)
            
    except KeyboardInterrupt:
        print("\nSaliendo...")
    finally:
        selector.stop_current_program()
        GPIO.cleanup()

if __name__ == "__main__":
    main()