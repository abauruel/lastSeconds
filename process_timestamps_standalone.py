#!/usr/bin/env python3
"""
Script standalone para processar timestamps sem necessidade do serviço web.
Útil para processamento em horários de baixa carga ou manutenção.

Uso:
    # Processar últimos 3 dias (padrão)
    python3 process_timestamps_standalone.py
    
    # Processar dia específico
    python3 process_timestamps_standalone.py --date 20260214
    
    # Processar últimos N dias
    python3 process_timestamps_standalone.py --days 7
    
    # Processar apenas pendentes (sem reprocessar failed)
    python3 process_timestamps_standalone.py --pending-only
"""

import sys
import os
import argparse
from datetime import datetime

# Adiciona o diretório do app ao path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from ffmpeg_manager import FFMpegManager

def main():
    parser = argparse.ArgumentParser(
        description='Processa timestamps de vídeo de forma standalone'
    )
    parser.add_argument(
        '--date',
        type=str,
        help='Data específica no formato YYYYMMDD (ex: 20260214)'
    )
    parser.add_argument(
        '--days',
        type=int,
        default=3,
        help='Número de dias para processar (padrão: 3)'
    )
    parser.add_argument(
        '--pending-only',
        action='store_true',
        help='Processar apenas status "pending" (ignora "failed")'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Mostrar informações detalhadas de debug'
    )
    
    args = parser.parse_args()
    
    print("="*70)
    print("PROCESSAMENTO STANDALONE DE TIMESTAMPS")
    print("="*70)
    print(f"Iniciado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Configurações de diretórios (mesmas do capture3.py)
    BASE_DIR = "/media/pi/usb64gb/bts"
    BUFFER_DIR = os.path.join(BASE_DIR, "buffers")
    FINAL_DIR = os.path.join(BASE_DIR, "recordings")
    STREAM_DIR = os.path.join(BASE_DIR, "streams")
    BUFFER_DIR_VIDEO0 = os.path.join(BUFFER_DIR, "video0")
    BUFFER_DIR_VIDEO2 = os.path.join(BUFFER_DIR, "video2")
    
    # Garante que os diretórios existem
    os.makedirs(BUFFER_DIR_VIDEO0, exist_ok=True)
    os.makedirs(BUFFER_DIR_VIDEO2, exist_ok=True)
    os.makedirs(FINAL_DIR, exist_ok=True)
    os.makedirs(STREAM_DIR, exist_ok=True)
    
    # Inicializa o FFMpegManager sem iniciar os processos de gravação
    print("Inicializando FFMpegManager...")
    ffmpeg_manager = FFMpegManager(BUFFER_DIR_VIDEO0, BUFFER_DIR_VIDEO2, FINAL_DIR, STREAM_DIR)
    
    # NÃO inicia os processos FFmpeg (modo standalone)
    print("Modo standalone - processos FFmpeg não serão iniciados")
    print()
    
    # Prepara parâmetros
    date_str = args.date
    days_back = args.days
    
    if date_str:
        print(f"Processando data específica: {date_str}")
    else:
        print(f"Processando últimos {days_back} dias")
    
    if args.pending_only:
        print("Modo: apenas timestamps com status 'pending'")
    else:
        print("Modo: todos os timestamps 'pending' e 'failed'")
    
    print("-"*70)
    print()
    
    try:
        # Chama a função de processamento manual
        result = ffmpeg_manager.manual_process_timestamps(
            date_str=date_str,
            days_back=days_back
        )
        
        print()
        print("="*70)
        print("RESULTADO DO PROCESSAMENTO")
        print("="*70)
        print(f"Status: {result.get('status')}")
        print(f"Processados com sucesso: {result.get('processed', 0)}")
        print(f"Falharam: {result.get('failed', 0)}")
        
        if 'dates' in result:
            print(f"Datas processadas: {', '.join(result['dates'])}")
        
        if 'message' in result:
            print(f"Mensagem: {result['message']}")
        
        print()
        print(f"Finalizado em: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*70)
        
        # Exit code baseado no resultado
        if result.get('status') == 'success':
            sys.exit(0)
        else:
            sys.exit(1)
            
    except KeyboardInterrupt:
        print()
        print("Processamento interrompido pelo usuário")
        sys.exit(130)
    except Exception as e:
        print()
        print("="*70)
        print("ERRO NO PROCESSAMENTO")
        print("="*70)
        print(f"Tipo: {type(e).__name__}")
        print(f"Mensagem: {str(e)}")
        
        if args.verbose:
            import traceback
            print()
            print("Stack trace completo:")
            traceback.print_exc()
        
        sys.exit(1)

if __name__ == "__main__":
    main()
