#!/usr/bin/env python3
"""
Script de diagnóstico para problema de enumeração dinâmica de câmeras.

Problema original:
- Câmera 2 estava em /dev/video2
- Após desconexão/reconexão, mudou para /dev/video3
- Rota /health reportava: "Camera /dev/video2 not detected"

Solução implementada:
- Detecção dinâmica de câmeras via v4l2-ctl
- Não assume números fixos
"""

import os
import subprocess
import sys
import json
from datetime import datetime

class CameraDiagnostics:
    def __init__(self):
        self.cameras = []
        self.issues = []
        self.success = True
        
    def print_header(self, title):
        """Imprime um cabeçalho formatado"""
        print(f"\n{'='*60}")
        print(f"  {title}")
        print(f"{'='*60}\n")
    
    def print_status(self, icon, message, details=None):
        """Imprime status com ícone"""
        colors = {
            '✓': '\033[92m',  # Verde
            '✗': '\033[91m',  # Vermelho
            '⚠': '\033[93m',  # Amarelo
            'ℹ': '\033[94m',  # Azul
        }
        reset = '\033[0m'
        color = colors.get(icon, '')
        
        print(f"{color}{icon} {message}{reset}")
        if details:
            for line in details.split('\n'):
                print(f"  {line}")
    
    def check_v4l2_tools(self):
        """Verifica se v4l2-ctl está instalado"""
        self.print_header("1. Verificação de Ferramentas")
        
        try:
            result = subprocess.run(
                ["v4l2-ctl", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            self.print_status('✓', f"v4l2-ctl instalado: {result.stdout.strip()}")
            return True
        except FileNotFoundError:
            self.print_status('✗', "v4l2-ctl NÃO encontrado!")
            self.print_status('ℹ', "Instale com:", 
                "sudo apt-get update && sudo apt-get install -y v4l-utils")
            self.issues.append("v4l2-ctl não instalado")
            self.success = False
            return False
    
    def list_video_devices(self):
        """Lista todos os dispositivos /dev/video*"""
        self.print_header("2. Dispositivos de Vídeo Detectados")
        
        try:
            # Modo 1: via v4l2-ctl
            result = subprocess.run(
                ["v4l2-ctl", "--list-devices"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            print("Via v4l2-ctl --list-devices:")
            print("-" * 40)
            print(result.stdout)
            
            # Modo 2: via ls /dev/video*
            print("\nDisositivos em /dev/video*:")
            print("-" * 40)
            
            video_devices = []
            for i in range(0, 10):
                device = f"/dev/video{i}"
                if os.path.exists(device):
                    try:
                        stat = os.stat(device)
                        video_devices.append(device)
                        
                        # Tenta obter informações do dispositivo
                        try:
                            info = subprocess.run(
                                ["v4l2-ctl", "-d", device, "--list-formats"],
                                capture_output=True,
                                text=True,
                                timeout=2
                            )
                            has_formats = "PixelFormat" in info.stdout
                            icon = "✓" if has_formats else "⚠"
                            self.print_status(icon, f"{device} (acessível)")
                            video_devices.append(device)
                        except:
                            self.print_status('⚠', f"{device} (acessível mas sem formato)")
                    except Exception as e:
                        self.print_status('✗', f"{device} - Erro: {e}")
            
            self.cameras = video_devices
            
            if not video_devices:
                self.print_status('✗', "Nenhum dispositivo de vídeo encontrado!")
                self.issues.append("Nenhuma câmera detectada")
                self.success = False
            else:
                self.print_status('✓', f"Total de dispositivos: {len(video_devices)}")
            
            return len(video_devices) > 0
            
        except Exception as e:
            self.print_status('✗', f"Erro ao listar dispositivos: {e}")
            self.issues.append(f"Erro na listagem: {e}")
            self.success = False
            return False
    
    def analyze_enumeration_pattern(self):
        """Analisa o padrão de enumeração (par/ímpar)"""
        self.print_header("3. Análise do Padrão de Enumeração")
        
        print("Explicação: Números PARES (0,2,4...) = câmeras principais")
        print("            Números ÍMPARES (1,3,5...) = geralmente planos de fundo\n")
        
        pair_cameras = []
        odd_devices = []
        
        for device in sorted(self.cameras):
            try:
                num = int(device.split('video')[1])
                if num % 2 == 0:
                    pair_cameras.append(device)
                    self.print_status('✓', f"{device} → número {num} (PAR - câmera principal)")
                else:
                    odd_devices.append(device)
                    self.print_status('ℹ', f"{device} → número {num} (ÍMPAR - secundário)")
            except:
                self.print_status('⚠', f"{device} → não conseguiu analisar")
        
        print(f"\nResumo:")
        print(f"  Câmeras principais (PAR): {len(pair_cameras)} → {pair_cameras}")
        print(f"  Dispositivos sec. (ÍMPAR): {len(odd_devices)} → {odd_devices}")
        
        return pair_cameras
    
    def test_ffmpeg_manager(self):
        """Testa a função detect_usb_cameras()"""
        self.print_header("4. Teste da Detecção do FFMpeg Manager")
        
        try:
            # Tenta importar e testar
            sys.path.insert(0, '/home/pi/app')
            from ffmpeg_manager import FFMpegManager
            
            manager = FFMpegManager(
                '/tmp/video0',
                '/tmp/video2',
                '/tmp/final',
                '/tmp/stream'
            )
            
            detected = manager.detect_usb_cameras()
            
            print("Resultado de detect_usb_cameras():")
            print("-" * 40)
            for idx, device in sorted(detected.items()):
                self.print_status('✓', f"Camera {idx}: {device}")
            
            if len(detected) >= 2:
                self.print_status('✓', f"Total detectado: {len(detected)} câmeras")
            else:
                self.print_status('⚠', f"Apenas {len(detected)} câmera(s) detectada(s), esperado 2")
                self.issues.append(f"FFmpeg manager: apenas {len(detected)} câmera(s)")
            
            return True
            
        except Exception as e:
            self.print_status('✗', f"Erro ao testar FFmpeg manager: {e}")
            self.issues.append(f"FFmpeg manager error: {e}")
            return False
    
    def test_health_endpoint(self):
        """Testa a rota /health"""
        self.print_header("5. Teste da Rota /health")
        
        try:
            result = subprocess.run(
                ["curl", "-s", "http://localhost:5000/health"],
                capture_output=True,
                text=True,
                timeout=5
            )
            
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    cameras = data.get('cameras', {})
                    
                    detected = cameras.get('detected', [])
                    count = cameras.get('count', 0)
                    
                    print("Resposta de /health (câmeras):")
                    print("-" * 40)
                    print(f"Detectadas: {detected}")
                    print(f"Contagem: {count}")
                    
                    if count >= 2:
                        self.print_status('✓', f"{count} câmeras detectadas")
                    else:
                        self.print_status('⚠', f"Apenas {count} câmera(s), esperado 2")
                        self.issues.append(f"Health check: {count} câmera(s)")
                    
                    # Verifica detalhes
                    details = cameras.get('details', {})
                    if details:
                        print("\nDetalhes:")
                        for cam, device in sorted(details.items()):
                            print(f"  {cam}: {device}")
                    
                except json.JSONDecodeError:
                    self.print_status('✗', "Erro ao decodificar JSON da resposta")
                    self.issues.append("Health endpoint retornou JSON inválido")
            else:
                self.print_status('⚠', "Servidor não respondeu (porta 5000 não acessível)")
                self.print_status('ℹ', "Certifique-se de que app.py está rodando")
                
        except Exception as e:
            self.print_status('⚠', f"Erro ao testar /health: {e}")
    
    def check_ffmpeg_logs(self):
        """Verifica logs do FFmpeg"""
        self.print_header("6. Verificação de Logs do FFmpeg")
        
        log_paths = [
            "/media/pi/usb64gb/bts/ffmpeg_device0.log",
            "/media/pi/usb64gb/bts/ffmpeg_device1.log"
        ]
        
        for log_path in log_paths:
            if os.path.exists(log_path):
                print(f"\n{log_path}:")
                print("-" * 40)
                try:
                    with open(log_path, 'r') as f:
                        lines = f.readlines()
                        # Mostra últimas 10 linhas
                        for line in lines[-10:]:
                            if 'error' in line.lower() or 'error' in line.lower():
                                self.print_status('✗', line.strip())
                            elif 'input' in line.lower() or 'output' in line.lower():
                                self.print_status('ℹ', line.strip())
                except Exception as e:
                    self.print_status('⚠', f"Erro ao ler log: {e}")
            else:
                self.print_status('⚠', f"{log_path} - Não encontrado")
    
    def print_summary(self):
        """Imprime resumo final"""
        self.print_header("RESUMO FINAL")
        
        if self.success and not self.issues:
            self.print_status('✓', "Todos os testes passaram com sucesso!")
        elif self.issues:
            self.print_status('⚠', f"{len(self.issues)} problema(s) encontrado(s):")
            for i, issue in enumerate(self.issues, 1):
                print(f"  {i}. {issue}")
        
        print("\nProximos passos:")
        print("1. Se câmeras foram detectadas: experimente desconectar/reconectar USB")
        print("2. Execute este script novamente após mudança de dispositivo")
        print("3. Verifique se a câmera é detectada no novo número (/dev/videoX)")
        print("4. Consulte CAMERA_DETECTION_FIX.md para troubleshooting detalhado")

def main():
    print("\n")
    print("╔" + "="*58 + "╗")
    print("║" + " "*58 + "║")
    print("║" + "  DIAGNÓSTICO: Enumeração Dinâmica de Câmeras USB".center(58) + "║")
    print("║" + " "*58 + "║")
    print("╚" + "="*58 + "╝")
    
    diag = CameraDiagnostics()
    
    # Executa testes
    diag.check_v4l2_tools()
    if diag.cameras or diag.cameras == []:  # Continue mesmo se vazio
        diag.list_video_devices()
        if diag.cameras:
            pair_cameras = diag.analyze_enumeration_pattern()
            diag.test_ffmpeg_manager()
            diag.test_health_endpoint()
            diag.check_ffmpeg_logs()
    
    diag.print_summary()
    
    print("\n" + "="*60 + "\n")

if __name__ == '__main__':
    main()
