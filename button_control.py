from gpiozero import Button, LED
import requests
from signal import pause
import threading
import time

button_pin = 17 # GPIO pin number
led_pin = 27

# Initialize button and LED
button = Button(button_pin)
led =LED(led_pin)

# Global variable to control LED blinking
is_recording = False
def start_recording():
  global is_recording
  response = requests.post('http://127.0.0.1:5000/start_capture')
  print(response.json())
  if(response.status_code==200):
    is_recording = True

def stop_recording():
  global is_recording
  response = requests.post('http://127.0.0.1:5000/stop_capture')
  print(response.json())
  if(response.status_code==200):
    is_recording = False
    led.off()

def blink_led():
  global is_recording
  while True:
    if(is_recording):
      led.on()
      time.sleep(0.5)
      led.off()
      time.sleep(0.5)
    else:
      led.off()
      time.sleep(0.1)

# Bind the button press events
button.when_pressed = start_recording
button.when_released = stop_recording

# Start the LED blinking thread
led_thread = threading.Thread(target=blink_led)
led_thread.start()

# Keep the script running
pause()