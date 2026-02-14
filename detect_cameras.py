#!/usr/bin/env python3
"""
Script para detectar e listar câmeras USB disponíveis.
Útil para diagnóstico e troubleshooting.
"""

import os
import subprocess
import sys

def detect_cameras():
    """Detecta todas as câmeras USB disponíveis"""
    print("=" * 60)
    print("DETECÇÃO DE CÂMERAS USB")
    print("=" * 60)
    print()
    
    # Lista todos os dispositivos de vídeo
    video_devices = []
    for i in range(32):
        device_path = f"/dev/video{i}"
        if os.path.exists(device_path):
            video_devices.append(device_path)
    
    if not video_devices:
        print("❌ Nenhum dispositivo de vídeo encontrado!")
        return []
    
    print(f"✓ Encontrados {len(video_devices)} dispositivos de vídeo")
    print()
    
    # Detecta câmeras USB
    usb_cameras = []
    
    for device_path in video_devices:
        try:
            result = subprocess.run(
                ['v4l2-ctl', '--device', device_path, '--all'],
                capture_output=True,
                text=True,
                timeout=2
            )
            
            output = result.stdout
            
            # Extrai informações
            driver = ""
            card = ""
            bus_info = ""
            capabilities = ""
            
            for line in output.split('\n'):
                if 'Driver name' in line:
                    driver = line.split(':', 1)[1].strip()
                elif 'Card type' in line:
                    card = line.split(':', 1)[1].strip()
                elif 'Bus info' in line:
                    bus_info = line.split(':', 1)[1].strip()
                elif 'Device Caps' in line:
                    capabilities = line.split(':', 1)[1].strip()
            
            # Verifica se é uvcvideo (câmera USB)
            if driver == 'uvcvideo':
                is_capture = 'Video Capture' in output and 'Metadata' not in capabilities
                
                usb_cameras.append({
                    'device': device_path,
                    'driver': driver,
                    'card': card,
                    'bus_info': bus_info,
                    'is_capture': is_capture
                })
        
        except (subprocess.TimeoutExpired, subprocess.CalledProcessError, Exception) as e:
            continue
    
    if not usb_cameras:
        print("❌ Nenhuma câmera USB encontrada!")
        return []
    
    # Exibe todas as câmeras encontradas
    print("CÂMERAS USB DETECTADAS:")
    print("-" * 60)
    
    for idx, cam in enumerate(usb_cameras):
        status = "✓ CAPTURA" if cam['is_capture'] else "⚠ METADATA"
        print(f"\nDispositivo: {cam['device']}")
        print(f"  Status:    {status}")
        print(f"  Card:      {cam['card']}")
        print(f"  Bus:       {cam['bus_info']}")
        print(f"  Driver:    {cam['driver']}")
    
    print()
    print("-" * 60)
    
    # Filtra apenas dispositivos de captura
    capture_cameras = [cam for cam in usb_cameras if cam['is_capture']]
    
    if not capture_cameras:
        print("❌ Nenhuma câmera de captura válida encontrada!")
        return []
    
    # Ordena por bus_info para manter consistência
    capture_cameras.sort(key=lambda x: x['bus_info'])
    
    print("\nMAPEAMENTO PARA O SISTEMA:")
    print("-" * 60)
    
    for idx, cam in enumerate(capture_cameras):
        print(f"Câmera {idx}: {cam['device']} (Bus: {cam['bus_info']})")
    
    print()
    print("=" * 60)
    print(f"✓ Total de câmeras de captura: {len(capture_cameras)}")
    print("=" * 60)
    
    return capture_cameras

if __name__ == "__main__":
    try:
        cameras = detect_cameras()
        sys.exit(0 if cameras else 1)
    except KeyboardInterrupt:
        print("\n\nDetecção cancelada pelo usuário.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERRO: {e}")
        sys.exit(1)
