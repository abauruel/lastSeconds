"""
Módulo para reprodução de áudio quando eventos são registrados.
Usa paplay (PulseAudio) para reproduzir no dispositivo Bluetooth G200.
Pré-processa os arquivos na inicialização para evitar corte no início.
"""
import os
import sys
import threading
import subprocess
import time

# Caminhos dos arquivos de áudio
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
AUDIO_DIR = os.path.join(BASE_DIR, "assets")
GOAL_SOUND = os.path.join(AUDIO_DIR, "success.mp3")
START_SOUND = os.path.join(AUDIO_DIR, "comecou.mp3")

# Caminhos dos arquivos WAV pré-processados (amplificados)
GOAL_SOUND_WAV = "/tmp/goal_amplified.wav"
START_SOUND_WAV = "/tmp/start_amplified.wav"

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

def _preprocess_audio_files():
    """
    Pré-processa arquivos de áudio na inicialização.
    Converte MP3 para WAV com amplificação para reprodução instantânea.
    """
    if not AUDIO_AVAILABLE:
        return
    
    sys.stderr.write("🎵 Pré-processando arquivos de áudio...\n")
    sys.stderr.flush()
    
    audio_files = [
        (GOAL_SOUND, GOAL_SOUND_WAV, "evento"),
        (START_SOUND, START_SOUND_WAV, "início")
    ]
    
    for source, target, name in audio_files:
        try:
            if not os.path.exists(source):
                sys.stderr.write(f"⚠ Arquivo {name} não encontrado: {source}\n")
                sys.stderr.flush()
                continue
            
            # Converte e amplifica com ffmpeg
            result = subprocess.run(
                ['ffmpeg', '-y', '-v', 'quiet', '-i', source,
                 '-f', 'wav', '-ar', '44100', '-ac', '2',
                 '-filter:a', 'volume=0.98', target],
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                sys.stderr.write(f"  ✓ {name} pré-processado\n")
                sys.stderr.flush()
            else:
                sys.stderr.write(f"  ⚠ Erro ao pré-processar {name}\n")
                sys.stderr.flush()
                
        except Exception as e:
            sys.stderr.write(f"  ⚠ Erro {name}: {e}\n")
            sys.stderr.flush()
    
    sys.stderr.write("✓ Pré-processamento concluído\n")
    sys.stderr.flush()

# Pré-processa arquivos na importação do módulo
if AUDIO_AVAILABLE:
    _preprocess_audio_files()

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
    """
    Função interna que toca o áudio usando paplay com arquivo pré-processado.
    arquivos já estão amplificados e no formato WAV, garantindo reprodução instantânea.
    """
    with audio_lock:
        try:
            # Mapeia arquivo MP3 original para WAV pré-processado
            if audio_file == GOAL_SOUND:
                wav_file = GOAL_SOUND_WAV
            elif audio_file == START_SOUND:
                wav_file = START_SOUND_WAV
            else:
                sys.stderr.write(f"[{sound_name}] ⚠ Arquivo não mapeado: {audio_file}\n")
                sys.stderr.flush()
                return
            
            # Verifica se o arquivo WAV pré-processado existe
            if not os.path.exists(wav_file):
                sys.stderr.write(f"[{sound_name}] ⚠ Arquivo WAV não encontrado: {wav_file}\n")
                sys.stderr.write(f"[{sound_name}] Tentando reprocessar...\n")
                sys.stderr.flush()
                _preprocess_audio_files()
                
                # Verifica novamente
                if not os.path.exists(wav_file):
                    sys.stderr.write(f"[{sound_name}] ⚠ Falha no reprocessamento\n")
                    sys.stderr.flush()
                    return
            
            sys.stderr.write(f"[{sound_name}] ▶ Reproduzindo áudio no G200...\n")
            sys.stderr.flush()
            
            # Toca o arquivo WAV pré-processado diretamente via paplay
            # Volume 65536 = 100% do PulseAudio (já amplificado em 98% pelo ffmpeg)
            result_play = subprocess.run(
                ['paplay', '--volume=65536', wav_file],
                capture_output=True,
                timeout=10
            )
            
            if result_play.returncode == 0:
                sys.stderr.write(f"[{sound_name}] ✓ Áudio reproduzido (instantâneo, 98%)\n")
                sys.stderr.flush()
            else:
                stderr_output = result_play.stderr.decode() if result_play.stderr else "sem detalhes"
                sys.stderr.write(f"[{sound_name}] ⚠ Erro ao reproduzir: {stderr_output}\n")
                sys.stderr.flush()
            
        except subprocess.TimeoutExpired:
            sys.stderr.write(f"[{sound_name}] ⚠ Timeout na reprodução\n")
            sys.stderr.flush()
        except Exception as e:
            sys.stderr.write(f"[{sound_name}] ⚠ Erro: {e}\n")
            sys.stderr.flush()

def stop_audio():
    """Para qualquer áudio que esteja tocando."""
    try:
        subprocess.run(['pkill', '-9', 'paplay'], capture_output=True, timeout=1)
        sys.stderr.write("🔇 Áudio parado\n")
        sys.stderr.flush()
    except:
        pass
