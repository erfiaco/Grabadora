#!/usr/bin/env python3
import RPi.GPIO as GPIO
import os
import time

BUTTON_PIN = 5

GPIO.setmode(GPIO.BCM)
GPIO.setup(BUTTON_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

print("Servicio de botn de apagado iniciado.")

try:
    while True:
        if GPIO.input(BUTTON_PIN) == GPIO.LOW:  # botón pulsado
            print("Botn detectado, apagando Raspberry...")
            time.sleep(2)  # anti-rebote
            os.system("sudo shutdown -h now")
        time.sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()
