import RPi.GPIO as GPIO

def setup_gpio():
    """Configura o GPIO."""
    GPIO.setwarnings(False)
    GPIO.setmode(GPIO.BOARD)
    # GPIO.setup(8, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Configura o pino 8 como entrada com pull-down
    return GPIO

def cleanup_gpio():
    """Limpa os recursos do GPIO."""
    GPIO.cleanup()