from gpio_config import setup_gpio

GPIO = setup_gpio()

try:
    # Limpa os recursos do GPIO antes de configurar
    # GPIO.cleanup()

    # Configura o pino 8 como entrada com pull-down
    GPIO.setup(8, GPIO.IN, pull_up_down=GPIO.PUD_UP)

    def register_button_callback(callback):
        """Registra um callback para o botão."""
        GPIO.add_event_detect(8, GPIO.FALLING, callback=callback, bouncetime=200)
        print("Callback registrado com sucesso no pino 8.")

except RuntimeError as e:
    print(f"Erro ao configurar o GPIO: {e}")