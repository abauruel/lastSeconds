import time
import threading
from rpi_ws281x import PixelStrip, Color

# Configuração da fita LED
LED_COUNT = 8
LED_PIN = 10
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 200
LED_INVERT = False
LED_CHANNEL = 0

# Inicialização da fita (só é feita quando o módulo é usado)
_strip = None

# Controle de threads
_led_lock = threading.Lock()
_led_state = "off"  # "off", "red_blinking", "green_blinking", etc.
_blink_thread = None
_stop_event = threading.Event()

def _initialize_strip():
    global _strip
    if _strip is None:
        _strip = PixelStrip(LED_COUNT, LED_PIN, LED_FREQ_HZ, LED_DMA,
                           LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL)
        _strip.begin()
    return _strip

def _set_all_leds(r, g, b):
    """Define a mesma cor para todos os LEDs"""
    strip = _initialize_strip()
    for i in range(LED_COUNT):
        strip.setPixelColor(i, Color(r, g, b))
    strip.show()

def _blink_loop(color, interval):
    """Função para piscar LEDs em loop até que o evento de parada seja disparado"""
    strip = _initialize_strip()
    r, g, b = color
    
    while not _stop_event.is_set():
        # Liga
        _set_all_leds(r, g, b)
        if _stop_event.wait(interval):  # Espera por 'interval' segundos ou até o evento ser disparado
            break
            
        # Desliga
        _set_all_leds(0, 0, 0)
        if _stop_event.wait(interval):  # Espera novamente
            break
    
    # Garante que os LEDs fiquem desligados ao sair
    _set_all_leds(0, 0, 0)

def start_blinking(color=(255, 0, 0), interval=0.5):
    """Inicia o piscar dos LEDs em thread separada"""
    global _blink_thread, _led_state
    
    with _led_lock:
        # Para qualquer piscar atual
        if _blink_thread and _blink_thread.is_alive():
            _stop_event.set()
            _blink_thread.join(timeout=1.0)
            _stop_event.clear()
        
        # Inicia novo piscar
        _led_state = f"{color}_blinking"
        _blink_thread = threading.Thread(target=_blink_loop, args=(color, interval), daemon=True)
        _blink_thread.start()
        print(f"LED começou a piscar na cor ({color[0]}, {color[1]}, {color[2]})")

def stop_blinking():
    """Para o piscar dos LEDs"""
    global _blink_thread, _led_state
    
    with _led_lock:
        if _blink_thread and _blink_thread.is_alive():
            _stop_event.set()
            _blink_thread.join(timeout=1.0)
            _stop_event.clear()
            _blink_thread = None
            
        _led_state = "off"
        _set_all_leds(0, 0, 0)
        print("LED parou de piscar")

def blink_n_times(color=(0, 255, 0), n=4, interval=0.2):
    """Pisca n vezes em uma cor específica, não usa thread"""
    stop_blinking()  # Para qualquer piscar em andamento
    
    strip = _initialize_strip()
    r, g, b = color
    
    print(f"LED piscando {n} vezes na cor ({r}, {g}, {b})")
    for _ in range(n):
        _set_all_leds(r, g, b)
        time.sleep(interval)
        _set_all_leds(0, 0, 0)
        time.sleep(interval)

def blink_sequence(color_sequence, n_times=4, interval=0.2, then_restart_red=True):
    """
    Executa uma sequência de piscadas e depois volta ao piscar vermelho se solicitado
    Esta função é projetada para ser chamada em uma nova thread
    """
    stop_blinking()  # Para qualquer piscar em andamento
    
    # Pisca cada cor na sequência
    for color in color_sequence:
        for _ in range(n_times):
            _set_all_leds(*color)
            time.sleep(interval)
            _set_all_leds(0, 0, 0)
            time.sleep(interval)
    
    # Se solicitado, volta a piscar vermelho
    if then_restart_red:
        start_blinking(color=(255, 0, 0), interval=0.5)

def blink_green_then_red(n=4, interval=0.2):
    """Pisca verde n vezes e depois volta a piscar vermelho em uma nova thread"""
    threading.Thread(
        target=blink_sequence,
        args=([(0, 255, 0)], n, interval, True),
        daemon=True
    ).start()

def cleanup():
    """Limpeza ao finalizar"""
    stop_blinking()

# Para teste independente
if __name__ == "__main__":
    try:
        print("Testando piscar vermelho por 3 segundos...")
        start_blinking(color=(255, 0, 0), interval=0.5)
        # time.sleep(3)
        
        print("Testando piscar verde 4 vezes...")
        blink_n_times(color=(0, 255, 0), n=4, interval=0.2)
        
        print("Voltando a piscar vermelho por 3 segundos...")
        start_blinking(color=(255, 0, 0), interval=0.5)
        time.sleep(3)
        
        print("Testando sequência verde depois vermelho...")
        blink_green_then_red(n=4, interval=0.2)
        time.sleep(5)  # Tempo para observar o efeito completo
        
        print("Teste finalizado")
        cleanup()
        
    except KeyboardInterrupt:
        print("Teste interrompido")
        cleanup()