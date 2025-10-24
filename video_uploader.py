import os
import time
import requests
from datetime import datetime
import schedule
from database import get_db, Video, VideoStatus

API_BASE_URL = os.getenv("API_BASE_URL", "http://registroesportivo.com.br/api")
API_TOKEN = os.getenv("API_TOKEN", "secret123")

HEADERS = {
    "x-api-token": API_TOKEN,
    "Content-Type": "application/json"
}

class VideoUploader:
    def __init__(self, base_stream_dir):
        self.base_stream_dir = base_stream_dir

    def generate_upload_url(self, filename):
        """Gera URL pré-assinada para upload."""
        url = f"{API_BASE_URL}/generate_upload_url"
        response = requests.post(url, headers=HEADERS, json={"filename": filename})
        response.raise_for_status()
        return response.json()["url"]

    def check_file_exists(self, filename):
        """Verifica se o arquivo já existe no servidor."""
        url = f"{API_BASE_URL}/media_events?filename={filename}"
        response = requests.get(url, headers=HEADERS)
        return response.status_code == 409

    def register_video(self, filename, thumbnail_filename=None):
        """Registra o vídeo no servidor."""
        url = f"{API_BASE_URL}/media_events"
        payload = {"filename": filename}
        if thumbnail_filename:
            payload["thumbnail_url"] = thumbnail_filename
        
        response = requests.post(url, headers=HEADERS, json=payload)
        response.raise_for_status()
        return response.json()

    def upload_file(self, local_path, presigned_url):
        """Faz o upload do arquivo para o bucket."""
        with open(local_path, 'rb') as f:
            response = requests.put(presigned_url, data=f)
            response.raise_for_status()

    def process_video(self, video, db):
        """Processa um único vídeo."""
        try:
            # Constrói os caminhos dos arquivos
            full_path = os.path.join(self.base_stream_dir, video.path)
            thumb_path = f"{full_path}.jpeg"
            filename = video.name
            
            if not os.path.exists(full_path):
                print(f"Arquivo não encontrado: {full_path}")
                return False

            # Verifica se o arquivo já existe no servidor
            if self.check_file_exists(filename):
                print(f"Arquivo {filename} já existe no servidor. Marcando como enviado.")
                video.status = VideoStatus.SENT
                db.commit()
                return True

            # Upload do vídeo
            print(f"Gerando URL para upload de {filename}...")
            presigned_url = self.generate_upload_url(filename)
            
            print(f"Fazendo upload do vídeo {filename}...")
            self.upload_file(full_path, presigned_url)
            
            # Upload da thumbnail se existir
            thumbnail_filename = None
            if os.path.exists(thumb_path):
                thumbnail_filename = f"{filename}.jpeg"
                print(f"Fazendo upload da thumbnail {thumbnail_filename}...")
                thumb_presigned_url = self.generate_upload_url(thumbnail_filename)
                self.upload_file(thumb_path, thumb_presigned_url)

            # Registra o vídeo no servidor
            print(f"Registrando vídeo {filename} no servidor...")
            self.register_video(filename, thumbnail_filename)

            # Atualiza o status no banco de dados
            video.status = VideoStatus.SENT
            db.commit()
            print(f"Vídeo {filename} processado com sucesso!")
            return True

        except requests.HTTPError as e:
            print(f"Erro HTTP ao processar o vídeo {filename}: {str(e)}")
            return False
        except Exception as e:
            print(f"Erro ao processar o vídeo {filename}: {str(e)}")
            return False

    def upload_pending_videos(self):
        """Procura e processa vídeos pendentes."""
        try:
            print(f"[{datetime.now()}] Verificando vídeos pendentes...")
            db = next(get_db())
            
            # Busca todos os vídeos com status PENDING
            pending_videos = db.query(Video).filter(Video.status == VideoStatus.PENDING).all()
            
            if not pending_videos:
                print("Nenhum vídeo pendente encontrado.")
                return

            print(f"Encontrados {len(pending_videos)} vídeos pendentes.")
            
            for video in pending_videos:
                try:
                    self.process_video(video, db)
                except Exception as e:
                    print(f"Erro ao processar o vídeo {video.name}: {str(e)}")
                    db.rollback()

        except Exception as e:
            print(f"Erro durante o processo de upload: {str(e)}")
        finally:
            if 'db' in locals():
                db.close()

def start_uploader(stream_dir):
    """Inicia o agendador para executar o upload a cada 15 minutos."""
    uploader = VideoUploader(stream_dir)
    
    # Agenda a execução a cada 15 minutos
    schedule.every(15).minutes.do(uploader.upload_pending_videos)
    
    print("Iniciando serviço de upload de vídeos...")
    print(f"API Base URL: {API_BASE_URL}")
    print("Executando a cada 15 minutos")
    
    # Executa uma vez imediatamente ao iniciar
    uploader.upload_pending_videos()
    
    # Loop principal
    while True:
        schedule.run_pending()
        time.sleep(60)  # Espera 1 minuto antes de verificar novamente

if __name__ == "__main__":
    # Configurações
    STREAM_DIR = "./recordings/streams"  # Ajuste para o diretório correto
    
    start_uploader(STREAM_DIR)