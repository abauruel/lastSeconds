"""
Módulo para reprodução de áudio quando eventos são registrados.
Usa paplay (PulseAudio) para reproduzir no dispositivo Bluetooth G200.
"""
import os
import sys
import threading
import subprocess

# Caminhos dos arquivos de áudio
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "assets")
GOAL_SOUND = os.path.join(AUDIO_DIR, "goodresult.mp3")
START_SOUND = os.path.join(AUDIO_DIR, "comecou.mp3")

# Lock para evitar sobreposição de áudios
audio_lock = threading.Lock()

# Verifica se paplay está disponível
try:
    result = subprocess.run(['which', 'paplay'], capture_output=True, timeout=2)
    AUDIO_AVAILABLE = result.returncode == 0
    if AUDIO_AVAILABLE:
        sys.stderr.write("✓ Audio player disponível (paplay - PulseAudio)\n")
        sys.stderr.flush()
    else:
        sys.stderr.write("⚠ paplay não encontrado - áudio desabilitado\n")
        sys.stderr.flush()
except Exception as e:
    AUDIO_AVAILABLE = False
    sys.stderr.write(f"⚠ Audio player não disponível: {e}\n")
    sys.stderr.flush()

def play_event_sound(blocking=False):
    """
    Toca o som de evento (gol).
    
    Args:
        blocking (bool): Se True, bloqueia até o áudio terminar. 
                        Se False, toca em thread separada (padrão).
    """
    sys.stderr.write(f"[play_event_sound] Chamado - AUDIO_AVAILABLE={AUDIO_AVAILABLE}, blocking={blocking}\n")
    sys.stderr.flush()
    
    if not AUDIO_AVAILABLE:
        sys.stderr.write("[play_event_sound] Áudio não disponível, retornando\n")
        sys.stderr.flush()
        return
    
    if blocking:
        _play_audio_internal(GOAL_SOUND, "evento")
    else:
        # Executa em thread separada para não bloquear a resposta da API
        sys.stderr.write("[play_event_sound] Iniciando thread para tocar áudio\n")
        sys.stderr.flush()
        thread = threading.Thread(
            target=_play_audio_internal, 
            args=(GOAL_SOUND, "evento"), 
            daemon=True
        )
        thread.start()
        sys.stderr.write(f"[play_event_sound] Thread iniciada: {thread.name}\n")
        sys.stderr.flush()

def play_start_sound(blocking=False):
    """
    Toca o som de início.
    
    Args:
        blocking (bool): Se True, bloqueia até o áudio terminar. 
                        Se False, toca em thread separada (padrão).
    """
    if not AUDIO_AVAILABLE:
        return
    
    if blocking:
        _play_audio_internal(START_SOUND, "início")
    else:
        thread = threading.Thread(
            target=_play_audio_internal, 
            args=(START_SOUND, "início"), 
            daemon=True
        )
        thread.start()

def _play_audio_internal(audio_file, sound_name):
    """Função interna que toca o áudio usando ffmpeg + paplay com amplificação."""
    with audio_lock:
        try:
            sys.stderr.write(f"[{sound_name}] Reproduzindo áudio no G200...\n")
            sys.stderr.flush()
            
            # Verifica se o arquivo existe
            if not os.path.exists(audio_file):
                sys.stderr.write(f"[{sound_name}] ⚠ Arquivo não encontrado: {audio_file}\n")
                sys.stderr.flush()
                return
            
            # Cria arquivo temporário amplificado
            temp_file = "/tmp/audio_amplified.wav"
            
            # Usa ffmpeg para amplificar o áudio
            # volume=0.98 = 98% de amplificação
            result_ffmpeg = subprocess.run(
                ['ffmpeg', '-y', '-v', 'quiet', '-i', audio_file, 
                 '-f', 'wav', '-ar', '44100', '-ac', '2', 
                 '-filter:a', 'volume=0.98', temp_file],
                capture_output=True,
                timeout=5
            )
            
            if result_ffmpeg.returncode != 0:
                sys.stderr.write(f"[{sound_name}] ⚠ Erro ao amplificar áudio\n")
                sys.stderr.flush()
                return
            
            # Toca o arquivo amplificado via paplay
            result_play = subprocess.run(
                ['paplay', '--volume=65536', temp_file],
                capture_output=True,
                timeout=10
            )
            
            # Remove arquivo temporário
            try:
                os.remove(temp_file)
            except:
                pass
            
            if result_play.returncode == 0:
                sys.stderr.write(f"[{sound_name}] ✓ Áudio reproduzido (volume 98%)\n")
                sys.stderr.flush()
            else:
                sys.stderr.write(f"[{sound_name}] ⚠ Erro ao reproduzir: {result_play.stderr.decode()}\n")
                sys.stderr.flush()
            
        except subprocess.TimeoutExpired:
            sys.stderr.write(f"[{sound_name}] ⚠ Timeout\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[{sound_name}] ⚠ Erro: {e}\n")
            sys.stderr.flush()

def stop_audio():
    """Para qualquer áudio que esteja tocando."""
    try:
        subprocess.run(['pkill', '-9', 'paplay'], capture_output=True, timeout=1)
        subprocess.run(['pkill', '-9', 'ffmpeg'], capture_output=True, timeout=1)
        sys.stderr.write("🔇 Áudio parado\n")
        sys.stderr.flush()
    except:
        pass
