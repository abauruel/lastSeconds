import sqlite3
import os


DB_PATH = os.environ.get("DB_PATH")
DEVICE_ID = os.environ.get("DEVICE_ID")

def save_output_to_db(output_file, db_path=DB_PATH):
    """Salva o caminho do arquivo de saída no banco de dados SQLite."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()    
    name = os.path.basename(output_file)
    cursor.execute("INSERT INTO output_files (file_path, name, device_id) VALUES (?, ?, ?)", (output_file, name, DEVICE_ID))
    conn.commit()
    conn.close()

def mark_file_as_sent(file_id, db_path=DB_PATH):
  """Atualiza a tabela output_files marcando o arquivo como enviado."""
  conn = sqlite3.connect(db_path)
  cursor = conn.cursor()
  cursor.execute("""
    UPDATE output_files
    SET send_to_server = 1,
      sent_at = CURRENT_TIMESTAMP
    WHERE id = ?
  """, (file_id,))
  conn.commit()
  conn.close()

def list_unsent_files(db_path=DB_PATH):
    """Retorna todos os registros onde send_to_server = 0."""
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("""
      SELECT id, file_path, created_at, device_id
      FROM output_files
      WHERE send_to_server = 0
    """)
    results = cursor.fetchall()
    conn.close()
    return results
