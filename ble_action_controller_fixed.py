import asyncio
import requests
from bleak import BleakClient, BleakScanner, BleakError

SERVICE_UUID = "4fafc201-1fb5-459e-8fcc-c5c9c331914b"
CHARACTERISTIC_UUID = "beb5483e-36e1-4688-b7f5-ea07361b26a8"
DEVICE_NAME = "XIAO_ESP32C3_BLE"
DEVICE_ADDRESS = "34:85:18:03:F0:7E"  # Endereço fixo para conectar diretamente

def notification_handler(sender, data):
    message = data.decode('utf-8', errors='ignore')
    print(f"📩 Recebido: {message}")
    
    # Processa as mensagens especiais para envio de HTTP POST
    if message.lower() == "red":
        try:
            response = requests.post("http://localhost:5000/record/cam1")
            print(f"🔴 POST para cam01 - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Erro ao enviar POST para cam01: {e}")
    
    elif message.lower() == "blue":
        try:
            response = requests.post("http://localhost:5000/record/cam2")
            print(f"🔵 POST para cam02 - Status: {response.status_code}")
        except Exception as e:
            print(f"❌ Erro ao enviar POST para cam02: {e}")

async def connect_and_listen():
    """Conecta diretamente ao ESP32 e escuta notificações."""
    while True:
        client = None
        try:
            print(f"🔗 Tentando conectar em {DEVICE_ADDRESS}")
            
            # Conecta diretamente usando o endereço conhecido
            client = BleakClient(DEVICE_ADDRESS, timeout=30.0)
            await client.connect()
            print("✅ Conectado com sucesso!")
            
            # Aguarda para estabilizar conexão
            await asyncio.sleep(2)
            
            # Verifica se o serviço existe
            service_found = False
            for service in client.services:
                if service.uuid.lower() == SERVICE_UUID.lower():
                    service_found = True
                    print(f"✅ Serviço encontrado: {service.uuid}")
                    break
            
            if not service_found:
                print(f"❌ Serviço {SERVICE_UUID} não encontrado")
                await client.disconnect()
                await asyncio.sleep(5)
                continue
            
            # Verifica se a característica existe
            char_found = False
            for service in client.services:
                for char in service.characteristics:
                    if char.uuid.lower() == CHARACTERISTIC_UUID.lower():
                        char_found = True
                        print(f"✅ Característica encontrada: {char.uuid}")
                        break
                if char_found:
                    break
            
            if not char_found:
                print(f"❌ Característica {CHARACTERISTIC_UUID} não encontrada")
                await client.disconnect()
                await asyncio.sleep(5)
                continue
            
            # Se inscreve nas notificações
            print("📡 Se inscrevendo nas notificações...")
            await client.start_notify(CHARACTERISTIC_UUID, notification_handler)
            print("✅ Inscrito com sucesso! Aguardando mensagens...")
            
            # Mantém conexão ativa
            while client.is_connected:
                await asyncio.sleep(1)
            
            print("⚠️ Conexão perdida, tentando reconectar em 5s...\n")

        except BleakError as e:
            print(f"⚠️ Erro BLE: {type(e).__name__}: {str(e)}")
        except Exception as e:
            print(f"❌ Erro inesperado: {type(e).__name__}: {str(e)}")
        
        if client and client.is_connected:
            try:
                await client.disconnect()
            except:
                pass
        
        await asyncio.sleep(5)

async def main():
    print("🚀 Iniciando receptor BLE com reconexão automática")
    await connect_and_listen()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Encerrado pelo usuário")