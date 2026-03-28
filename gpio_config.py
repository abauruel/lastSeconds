try:
    import RPi.GPIO as GPIO
    GPIO_AVAILABLE = True
except (ImportError, RuntimeError):
    # Fallback para desenvolvimento/teste sem hardware GPIO
    print("⚠️ RPi.GPIO não disponível - usando mock")
    GPIO_AVAILABLE = False
    
    class MockGPIO:
        """Mock GPIO para desenvolvimento sem hardware"""
        BOARD = "BOARD"
        BCM = "BCM"
        IN = "IN"
        OUT = "OUT"
        PUD_DOWN = "PUD_DOWN"
        PUD_UP = "PUD_UP"
        
        @staticmethod
        def setwarnings(state):
            pass
        
        @staticmethod
        def setmode(mode):
            pass
        
        @staticmethod
        def setup(*args, **kwargs):
            pass
        
        @staticmethod
        def cleanup(*args, **kwargs):
            pass
        
        @staticmethod
        def input(*args):
            return False
        
        @staticmethod
        def output(*args):
            pass
    
    GPIO = MockGPIO()

def get_gpio():
    """Retorna o módulo GPIO (real ou mock)."""
    return GPIO

def setup_gpio():
    """Configura o GPIO."""
    if GPIO_AVAILABLE:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BOARD)
        # GPIO.setup(8, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)  # Configura o pino 8 como entrada com pull-down
    return GPIO

def cleanup_gpio():
    """Limpa os recursos do GPIO."""
    if GPIO_AVAILABLE:
        GPIO.cleanup()