import os
import time
import datetime
import subprocess
import threading

# Variáveis globais para armazenamento de temperatura
temperature_data = []
temperature_monitor_active = True
temperature_thread = None

def start_temperature_monitoring(base_dir):
    """
    Inicia o monitoramento de temperatura em uma thread separada.
    
    Args:
        base_dir (str): Diretório base onde os logs de temperatura serão salvos
    
    Returns:
        threading.Thread: A thread de monitoramento iniciada
    """
    global temperature_monitor_active, temperature_thread
    
    # Reset para garantir que inicie corretamente
    temperature_monitor_active = True
    
    # Criar diretório para armazenar os logs de temperatura se não existir
    temperature_dir = os.path.join(base_dir, "temperature_logs")
    os.makedirs(temperature_dir, exist_ok=True)
    
    # Iniciar thread de monitoramento
    temperature_thread = threading.Thread(
        target=monitor_temperature,
        args=(temperature_dir,),
        daemon=True  # Thread será encerrada quando o programa principal terminar
    )
    temperature_thread.start()
    
    print("Monitoramento de temperatura iniciado.")
    return temperature_thread

def stop_temperature_monitoring():
    """
    Para o monitoramento de temperatura e salva os dados restantes.
    """
    global temperature_monitor_active, temperature_thread
    
    if temperature_thread and temperature_thread.is_alive():
        print("Encerrando monitoramento de temperatura...")
        temperature_monitor_active = False
        temperature_thread.join(timeout=2)  # Aguardar até 2 segundos pela thread
        print("Monitoramento de temperatura encerrado.")

def monitor_temperature(temperature_dir):
    """
    Função principal de monitoramento que é executada em segundo plano.
    Coleta a temperatura a cada segundo e salva os dados a cada 5 minutos.
    
    Args:
        temperature_dir (str): Diretório onde os logs serão salvos
    """
    global temperature_data, temperature_monitor_active
    last_save_time = time.time()
    
    print("Iniciando coleta de dados de temperatura...")
    
    while temperature_monitor_active:
        try:
            # Executar comando para obter temperatura
            result = subprocess.run(['vcgencmd', 'measure_temp'], capture_output=True, text=True)
            temp_output = result.stdout.strip()
            
            # Extrair valor numérico da temperatura (formato típico: temp=45.6'C)
            temp_value = temp_output.replace("temp=", "").replace("'C", "")
            
            # Obter hora atual
            current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Armazenar em memória
            temperature_data.append({"timestamp": current_time, "temperature": temp_value})
            
            # Verificar se passou 5 minutos (300 segundos) desde o último salvamento
            current_time_secs = time.time()
            if current_time_secs - last_save_time >= 300:  # 5 minutos
                save_temperature_data(temperature_dir)
                last_save_time = current_time_secs
                
            # Aguardar 1 segundo
            time.sleep(1)
            
        except Exception as e:
            print(f"Erro ao monitorar temperatura: {e}")
            time.sleep(5)  # Em caso de erro, espera 5 segundos antes de tentar novamente
    
    # Salva os dados restantes antes de encerrar o monitoramento
    save_temperature_data(temperature_dir)

def save_temperature_data(directory):
    """
    Salva os dados de temperatura coletados em um arquivo de texto.
    
    Args:
        directory (str): Diretório onde o arquivo será salvo
    """
    global temperature_data
    
    if not temperature_data:
        return
        
    try:
        # Nome do arquivo com data atual
        filename = os.path.join(directory, f"temperature_{datetime.datetime.now().strftime('%Y%m%d')}.txt")
        
        # Abrir arquivo em modo append
        with open(filename, 'a') as f:
            for data in temperature_data:
                f.write(f"{data['timestamp']} - Temperatura: {data['temperature']}°C\n")
                
        print(f"Dados de temperatura salvos em {filename}")
        
        # Limpar dados da memória após salvar
        temperature_data = []
        
    except Exception as e:
        print(f"Erro ao salvar dados de temperatura: {e}")