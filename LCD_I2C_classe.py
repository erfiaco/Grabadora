import smbus2 as smbus
import time

# Definición de constantes para el LCD
LCD_CHR = 1  # Modo de datos
LCD_CMD = 0  # Modo de comando

LCD_LINE_1 = 0x80  # Dirección RAM para la línea 1
LCD_LINE_2 = 0xC0  # Dirección RAM para la línea 2
LCD_WIDTH = 16     # Máximo de caracteres por línea

LCD_BACKLIGHT_ON = 0x08  # Luz de fondo encendida
LCD_BACKLIGHT_OFF = 0x00  # Luz de fondo apagada

ENABLE = 0b00000100  # Habilitar bit

class LCD_I2C:
    def __init__(self, i2c_address=0x27, bus_id=1):
        """Inicializa el LCD con I2C."""
        self.address = i2c_address
        try:
            self.bus = smbus.SMBus(bus_id)
            self.init_lcd()
            print(f"[INFO] LCD inicializado en la dirección I2C: {hex(self.address)}")
        except Exception as e:
            print(f"[ERROR] No se pudo inicializar el LCD: {e}")

    def init_lcd(self):
        """Inicializa el LCD con comandos básicos."""
        self.lcd_byte(0x33, LCD_CMD)  # Inicialización al modo 4 bits
        self.lcd_byte(0x32, LCD_CMD)  # Modo 4 bits
        self.lcd_byte(0x06, LCD_CMD)  # Modo de entrada
        self.lcd_byte(0x0C, LCD_CMD)  # Enciende el display sin cursor
        self.lcd_byte(0x28, LCD_CMD)  # Modo de 2 líneas y 5x7 caracteres
        self.clear()

    def lcd_byte(self, bits, mode):
        """Envía un byte al LCD."""
        try:
            high_bits = mode | (bits & 0xF0) | LCD_BACKLIGHT_ON
            low_bits = mode | ((bits << 4) & 0xF0) | LCD_BACKLIGHT_ON

            self.bus.write_byte(self.address, high_bits)
            self.lcd_toggle_enable(high_bits)

            self.bus.write_byte(self.address, low_bits)
            self.lcd_toggle_enable(low_bits)
        except Exception as e:
            print(f"[ERROR] No se pudo enviar datos al LCD: {e}")

    def lcd_toggle_enable(self, bits):
        """Alterna el bit de habilitación."""
        time.sleep(0.0005)
        self.bus.write_byte(self.address, (bits | ENABLE))
        time.sleep(0.0005)
        self.bus.write_byte(self.address, (bits & ~ENABLE))
        time.sleep(0.0005)

    def clear(self):
        """Limpia la pantalla del LCD."""
        self.lcd_byte(0x01, LCD_CMD)
        time.sleep(0.002)

    def write(self, message, line):
        """
        Escribe un mensaje en la línea especificada.
        :param message: El mensaje a mostrar (máx. 16 caracteres).
        :param line: Número de línea (1 o 2).
        """
        if line == 1:
            line_address = LCD_LINE_1
        elif line == 2:
            line_address = LCD_LINE_2
        else:
            raise ValueError("Solo se admiten las líneas 1 o 2.")

        self.lcd_byte(line_address, LCD_CMD)

        # Escribir el mensaje con relleno si es necesario
        for char in message.ljust(LCD_WIDTH, " "):
            self.lcd_byte(ord(char), LCD_CHR)

    def backlight(self, state):
        """Controla la luz de fondo del LCD."""
        try:
            if state:
                self.bus.write_byte(self.address, LCD_BACKLIGHT_ON)
            else:
                self.bus.write_byte(self.address, LCD_BACKLIGHT_OFF)
        except Exception as e:
            print(f"[ERROR] No se pudo controlar la luz de fondo: {e}")
    
    def mostrar_cargando(self, mensaje="Cargando"):
        """
        Muestra un mensaje dinámico de 'Cargando' con un efecto de puntos en el LCD.
        :param mensaje: Texto base a mostrar en el LCD.
        """
        puntos = [".", "..", "..."]
        while True:
            for p in puntos:
                self.clear()
                self.write(f"{mensaje}{p}", line=1)
                time.sleep(0.5)  # Control de velocidad del efecto
