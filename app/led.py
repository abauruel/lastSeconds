import RPi.GPIO as GPIO
import time

pinoLED = 13
is_recording = False
# Configura o modo de numeração dos pinos
GPIO.setmode(GPIO.BOARD)

# Define o pino 12 como o pino do LED

# Configura o pino do LED como saída
GPIO.setup(pinoLED, GPIO.OUT)


def record_ligth(start):
    global is_recording
    is_recording = start
    while is_recording:
        GPIO.output(pinoLED, True)  # Acende o LED
        time.sleep(0.8)  # Aguarda meio segundo
        GPIO.output(pinoLED, False)  # Apaga o LED
        time.sleep(0.8)  # Aguarda meio segundo

def stop_record_ligth():
    global is_recording
    is_recording = False
    GPIO.output(pinoLED, False)  # Apaga o LED