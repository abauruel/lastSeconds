import RPi.GPIO as GPIO
import time

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(8, GPIO.IN, pull_up_down=GPIO.PUD_UP)

try:
    while True:
        if GPIO.input(8) == GPIO.LOW:
            print("Botão pressionado!")
        time.sleep(0.1)
except KeyboardInterrupt:
    GPIO.cleanup()