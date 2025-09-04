import sqlite3
import requests
import os
import time
import threading


DB_PATH = 'recordings.db'  # Altere para o caminho do seu banco
SERVER_URL = 'https://seuservidor.com/upload'  # Altere para o endpoint do seu servidor
INTERVAL_SECONDS = 60  # Tempo entre execuções

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS video_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_path TEXT NOT NULL,
            send_to_server INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    conn.close()


def send_file(path):
    if not os.path.exists(path):
        print(f"Arquivo não encontrado: {path}")
        return False
    with open(path, 'rb') as f:
        files = {'file': f}
        try:
            response = requests.post(SERVER_URL, files=files)
            return response.status_code == 200
        except Exception as e:
            print(f"Erro ao enviar arquivo: {e}")
            return False

def send_pending():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT id, file_path FROM video_records WHERE send_to_server=0")
    registros = cursor.fetchall()
    for id_, file_path in registros:
        if send_file(file_path):
            cursor.execute("UPDATE video_records SET send_to_server=1 WHERE id=?", (id_,))
            conn.commit()
            print(f"Arquivo enviado e status atualizado: {file_path}")
        else:
            print(f"Falha ao enviar: {file_path}")
    conn.close()

def scheduler_send():
    while True:
        send_pending()
        time.sleep(INTERVAL_SECONDS)
