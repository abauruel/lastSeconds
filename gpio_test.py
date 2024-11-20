import RPi.GPIO as GPIO

from app.api import register_buffer # Import Raspberry Pi GPIO library

GPIO.setwarnings(False) # Ignore warning for now
GPIO.setmode(GPIO.BOARD) # Use physical pin numbering
GPIO.setup(8, GPIO.IN) # Set pin 10 to be an input pin and set initial value to be pulled low (off)


def button_pressed_callback(channel):
    print("Button was pushed!")
    register_buffer()

GPIO.add_event_detect(8, GPIO.RISING, callback=button_pressed_callback, bouncetime=200)
