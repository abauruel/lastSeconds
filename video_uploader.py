import os
import time
import requests
from datetime import datetime
import schedule
import socket
from database import get_db, Video, VideoStatus

API_BASE_URL = os.getenv("API_BASE_URL", "http://registroesportivo.com.br/api")
API_TOKEN = os.getenv("API_TOKEN", "secret123")

def check_internet_connection():
    """
    Verifica se há conexão com a internet tentando conectar com o Google DNS.
    Retorna True se houver conexão, False caso contrário.
    """
    try:
        # Tenta conectar com o Google DNS (8.8.8.8)
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False

HEADERS = {
    "x-api-token": API_TOKEN,
    "Content-Type": "application/json"
}

class VideoUploader:
    def __init__(self, base_stream_dir):
        self.base_stream_dir = base_stream_dir
        self.api_base_url = self._detect_api_protocol()

    def _detect_api_protocol(self):
        """Detecta se a API usa HTTP ou HTTPS."""
        base_urls_to_try = [
            API_BASE_URL,  # URL original
            API_BASE_URL.replace("http://", "https://"),  # Tenta HTTPS
            f"https://www.{API_BASE_URL.replace('http://', '').replace('https://', '')}"  # Adiciona www
        ]
        
        for url in base_urls_to_try:
            try:
                print(f"[video_upload] Testando URL base: {url}")
                response = requests.get(url, timeout=10)
                if response.status_code < 500:
                    print(f"[video_upload] URL base detectada: {url} (status: {response.status_code})")
                    return url
            except requests.RequestException as e:
                print(f"[video_upload] Falha ao testar {url}: {str(e)}")
                continue
        
        print(f"[video_upload] Usando URL padrão: {API_BASE_URL}")
        return API_BASE_URL

    def check_api_availability(self):
        """Verifica se a API está disponível."""
        print(f"[video_upload] Testando conectividade com API: {self.api_base_url}")
        
        # Lista de endpoints para testar
        test_endpoints = [
            "/health",
            "/media_events", 
            "/generate_upload_url",
            "/"  # raiz da API
        ]
        
        for endpoint in test_endpoints:
            try:
                url = f"{self.api_base_url}{endpoint}"
                print(f"[video_upload] Testando endpoint: {url}")
                response = requests.get(url, headers=HEADERS, timeout=10)
                print(f"[video_upload] Status {endpoint}: {response.status_code}")
                
                if response.status_code < 500:  # Aceita qualquer código que não seja erro de servidor
                    print(f"[video_upload] API disponível (endpoint {endpoint} respondeu com {response.status_code})")
                    return True
                    
            except requests.RequestException as e:
                print(f"[video_upload] Erro ao testar {endpoint}: {str(e)}")
                continue
        
        print(f"[video_upload] Nenhum endpoint da API está respondendo adequadamente")
        return False

    def _debug_api_endpoints(self):
        """Executa diagnóstico detalhado dos endpoints da API."""
        print("=" * 50)
        print("[video_upload] DIAGNÓSTICO DETALHADO DA API")
        print("=" * 50)
        
        print(f"URL base configurada: {API_BASE_URL}")
        print(f"URL base detectada: {self.api_base_url}")
        print(f"Token API: {API_TOKEN[:10]}..." if len(API_TOKEN) > 10 else API_TOKEN)
        
        # Testa diferentes variações da URL
        test_urls = [
            self.api_base_url,
            self.api_base_url.rstrip('/'),  # Remove barra final
            f"{self.api_base_url}/api" if not self.api_base_url.endswith('/api') else self.api_base_url,
            "https://registroesportivo.com.br/api",
            "https://www.registroesportivo.com.br/api",
            "http://registroesportivo.com.br/api",
        ]
        
        for test_url in test_urls:
            print(f"\n--- Testando: {test_url} ---")
            try:
                response = requests.get(test_url, headers=HEADERS, timeout=10)
                print(f"Status: {response.status_code}")
                print(f"Headers: {dict(response.headers)}")
                if response.text and len(response.text) < 500:
                    print(f"Conteúdo: {response.text[:200]}...")
            except Exception as e:
                print(f"Erro: {str(e)}")
        
        print("=" * 50)

    def generate_upload_url(self, filename):
        """Gera URL pré-assinada para upload."""
        # Lista de possíveis endpoints para tentar
        possible_endpoints = [
            "/generate_upload_url",
            "/upload/generate_url", 
            "/api/generate_upload_url",
            "/v1/generate_upload_url"
        ]
        
        for endpoint in possible_endpoints:
            url = f"{self.api_base_url}{endpoint}"
            try:
                print(f"[video_upload] Tentando gerar URL de upload via: {url}")
                response = requests.post(url, headers=HEADERS, json={"filename": filename}, timeout=30)
                response.raise_for_status()
                result = response.json()["url"]
                print(f"[video_upload] URL gerada com sucesso via {endpoint}")
                return result
            except requests.HTTPError as e:
                print(f"[video_upload] Erro {response.status_code} no endpoint {endpoint}: {str(e)}")
                if response.status_code == 404:
                    continue  # Tenta próximo endpoint
                else:
                    raise e  # Para outros erros, levanta a exceção
            except requests.RequestException as e:
                print(f"[video_upload] Erro de conexão no endpoint {endpoint}: {str(e)}")
                continue
        
        # Se chegou aqui, nenhum endpoint funcionou
        raise requests.HTTPError(f"Nenhum endpoint de upload funcionou. Testados: {possible_endpoints}")

    def check_file_exists(self, filename):
        """Verifica se o arquivo já existe no servidor."""
        url = f"{self.api_base_url}/media_events?filename={filename}"
        try:
            response = requests.get(url, headers=HEADERS, timeout=15)
            return response.status_code == 409
        except requests.RequestException as e:
            print(f"[video_upload] Erro ao verificar se arquivo {filename} existe: {str(e)}")
            return False  # Assume que não existe se não conseguir verificar

    def register_video(self, filename, thumbnail_filename=None):
        """Registra o vídeo no servidor."""
        possible_endpoints = [
            "/media_events",
            "/videos",
            "/api/media_events", 
            "/v1/media_events"
        ]
        
        payload = {"filename": filename}
        if thumbnail_filename:
            payload["thumbnail_url"] = thumbnail_filename
        
        for endpoint in possible_endpoints:
            url = f"{self.api_base_url}{endpoint}"
            try:
                print(f"[video_upload] Tentando registrar vídeo via: {url}")
                response = requests.post(url, headers=HEADERS, json=payload, timeout=30)
                response.raise_for_status()
                result = response.json()
                print(f"[video_upload] Vídeo registrado com sucesso via {endpoint}")
                return result
            except requests.HTTPError as e:
                print(f"[video_upload] Erro {response.status_code} no endpoint {endpoint}: {str(e)}")
                if response.status_code == 404:
                    continue  # Tenta próximo endpoint
                else:
                    raise e
            except requests.RequestException as e:
                print(f"[video_upload] Erro de conexão no endpoint {endpoint}: {str(e)}")
                continue
        
        raise requests.HTTPError(f"Nenhum endpoint de registro funcionou. Testados: {possible_endpoints}")

    def upload_file(self, local_path, presigned_url):
        """Faz o upload do arquivo para o bucket."""
        with open(local_path, 'rb') as f:
            # Timeout maior para upload de arquivos grandes
            response = requests.put(presigned_url, data=f, timeout=300)  # 5 minutos
            response.raise_for_status()

    def process_video(self, video, db):
        """Processa um único vídeo."""
        try:
            # Constrói os caminhos dos arquivos
            full_path = os.path.join(self.base_stream_dir, video.path)
            thumb_path = f"{full_path}.jpeg"
            filename = video.name
            
            if not os.path.exists(full_path):
                print(f"[video_upload] Arquivo não encontrado: {full_path}")
                return False

            # Verifica se o arquivo já existe no servidor
            if self.check_file_exists(filename):
                print(f"[video_upload] Arquivo {filename} já existe no servidor. Marcando como enviado.")
                try:
                    video.status = VideoStatus.SENT
                    db.commit()
                    return True
                except Exception as db_error:
                    print(f"[video_upload] Erro ao atualizar banco de dados para {filename}: {str(db_error)}")
                    db.rollback()
                    return False

            # Upload do vídeo
            print(f"[video_upload] Gerando URL para upload de {filename}...")
            presigned_url = self.generate_upload_url(filename)
            
            print(f"[video_upload] Fazendo upload do vídeo {filename}...")
            self.upload_file(full_path, presigned_url)
            
            # Upload da thumbnail se existir
            thumbnail_filename = None
            if os.path.exists(thumb_path):
                thumbnail_filename = f"{filename}.jpeg"
                print(f"[video_upload] Fazendo upload da thumbnail {thumbnail_filename}...")
                thumb_presigned_url = self.generate_upload_url(thumbnail_filename)
                self.upload_file(thumb_path, thumb_presigned_url)

            # Registra o vídeo no servidor
            print(f"[video_upload] Registrando vídeo {filename} no servidor...")
            self.register_video(filename, thumbnail_filename)

            # Atualiza o status no banco de dados
            try:
                video.status = VideoStatus.SENT
                db.commit()
                print(f"[video_upload] Vídeo {filename} processado com sucesso!")
                return True
            except Exception as db_error:
                print(f"[video_upload] Erro ao atualizar banco de dados para {filename}: {str(db_error)}")
                db.rollback()
                return False

        except requests.HTTPError as e:
            error_msg = str(e)
            print(f"[video_upload] Erro HTTP ao processar o vídeo {filename}: {error_msg}")
            
            # Se for erro 404, pode ser que a API esteja indisponível temporariamente
            if "404" in error_msg:
                print(f"[video_upload] Erro 404 - API endpoint não encontrado. Continuando para próximo vídeo.")
            elif "409" in error_msg:
                print(f"[video_upload] Erro 409 - Arquivo já existe. Continuando para próximo vídeo.")
            
            # Não faz rollback aqui pois não houve mudança no banco ainda
            return False
        except Exception as e:
            print(f"[video_upload] Erro geral ao processar o vídeo {filename}: {str(e)}")
            return False

    def upload_pending_videos(self):
        """Procura e processa vídeos pendentes."""
        db = None
        try:
            print(f"[video_upload] [{datetime.now()}] Verificando conexão com a internet...")
            if not check_internet_connection():
                print("[video_upload] Sem conexão com a internet. Tentando novamente no próximo ciclo.")
                return

            print(f"[video_upload] [{datetime.now()}] Verificando disponibilidade da API...")
            if not self.check_api_availability():
                print("[video_upload] API não está disponível. Tentando novamente no próximo ciclo.")
                return

            print(f"[video_upload] [{datetime.now()}] Verificando vídeos pendentes...")
            db = next(get_db())
            
            # Busca todos os vídeos com status PENDING
            pending_videos = db.query(Video).filter(Video.status == VideoStatus.PENDING).all()
            
            if not pending_videos:
                print("[video_upload] Nenhum vídeo pendente encontrado.")
                return

            print(f"[video_upload] Encontrados {len(pending_videos)} vídeos pendentes.")
            
            processed_count = 0
            success_count = 0
            
            for video in pending_videos:
                processed_count += 1
                print(f"[video_upload] Processando vídeo {processed_count}/{len(pending_videos)}: {video.name}")
                
                try:
                    success = self.process_video(video, db)
                    if success:
                        success_count += 1
                        print(f"[video_upload] ✓ Sucesso ao processar o vídeo {video.name}")
                    else:
                        print(f"[video_upload] ✗ Falha ao processar o vídeo {video.name}")
                except Exception as e:
                    print(f"[video_upload] ✗ Erro não tratado ao processar o vídeo {video.name}: {str(e)}")
                    try:
                        db.rollback()
                    except Exception as rollback_error:
                        print(f"[video_upload] Erro durante rollback: {str(rollback_error)}")
                
                # Continua para o próximo vídeo independentemente do resultado
                print(f"[video_upload] Continuando para próximo vídeo...")
            
            print(f"[video_upload] Processamento concluído: {success_count}/{processed_count} vídeos enviados com sucesso.")
            
            # Se nenhum vídeo foi processado com sucesso, executa diagnóstico detalhado
            if success_count == 0 and processed_count > 0:
                print("[video_upload] Nenhum vídeo foi processado com sucesso. Executando diagnóstico...")
                self._debug_api_endpoints()

        except Exception as e:
            print(f"[video_upload] Erro durante o processo de upload: {str(e)}")
            if db:
                try:
                    db.rollback()
                except Exception as rollback_error:
                    print(f"[video_upload] Erro durante rollback: {str(rollback_error)}")
        finally:
            if db:
                try:
                    db.close()
                except Exception as close_error:
                    print(f"[video_upload] Erro ao fechar conexão com banco de dados: {str(close_error)}")

def start_uploader(stream_dir):
    """Inicia o agendador para executar o upload a cada 15 minutos."""
    uploader = VideoUploader(stream_dir)
    
    # Agenda a execução a cada 15 minutos
    # schedule.every(15).minutes.do(uploader.upload_pending_videos)
    
    print("[video_upload] Iniciando serviço de upload de vídeos...")
    print(f"[video_upload] API Base URL: {API_BASE_URL}")
    print("[video_upload] Executando a cada 15 minutos")
    
    # Executa uma vez imediatamente ao iniciar
    uploader.upload_pending_videos()
    
    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Espera 1 minuto antes de verificar novamente

if __name__ == "__main__":
    # Configurações
    STREAM_DIR = "/home/pi/recordings/streams"  # Diretório no microSD
    
    start_uploader(STREAM_DIR)