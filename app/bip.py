import RPi.GPIO as GPIO
import time

# Pin do buzzer
BUZZER_PIN = 12
LED_RED_PIN= 11

# Configuração do GPIO
# GPIO.setmode(GPIO.BCM)
GPIO.setmode(GPIO.BOARD) 
GPIO.setup(BUZZER_PIN, GPIO.OUT)
GPIO.setup(LED_RED_PIN, GPIO.OUT)

def beep(duration=0.1, frequency=2000):
    # Cria a instância PWM
    pwm = GPIO.PWM(BUZZER_PIN, frequency)
    pwm.start(90)  # 90% de ciclo de trabalho para som alto
    GPIO.output(LED_RED_PIN, True)
    time.sleep(duration)
    pwm.stop()
    GPIO.output(LED_RED_PIN, False)
    time.sleep(0.1)  # Pausa entre os bipes

def start_beep():
    # Som de inicialização: três bipes curtos
    for _ in range(3):
        beep(0.1)

def record_beep():
    # Som de início de gravação: um bipe longo
    beep(0.5)

def stop_record_beep():
    # Som de parada de gravação: três bipes curtos
    for _ in range(3):
        beep(0.1)

def stop_beep():
    # Som de parada de gravação: três bipes curtos
    for _ in range(3):
        beep(0.2)

def cleanup_gpio():
    GPIO.cleanup()

# try:
#     print("start beep...")
#     start_beep()
#     time.sleep(2)
    
#     print("record beep...")
#     record_beep()
#     time.sleep(2)
    
#     print("stop record beep...")
#     stop_record_beep()

# finally:
#     cleanup_gpio()
