#!/bin/bash
# Watch contínuo do status de saúde (atualiza a cada 5 segundos)

watch -n 5 -c 'curl -s http://localhost:5000/health 2>&1 | python3 -c "
import sys, json
from datetime import datetime

try:
    d = json.load(sys.stdin)
    
    # Header
    print(\"=\"*60)
    print(\"🏥 HEALTH STATUS - {}\".format(datetime.now().strftime(\"%H:%M:%S\")))
    print(\"=\"*60)
    print()
    
    # Status geral
    status_emoji = {
        \"healthy\": \"✅\",
        \"degraded\": \"⚠️\",
        \"unhealthy\": \"❌\",
        \"error\": \"🔥\"
    }
    print(\"Status: {} {}\".format(status_emoji.get(d[\"status\"], \"❓\"), d[\"status\"].upper()))
    print()
    
    # Processos FFmpeg
    ffmpeg = d.get(\"ffmpeg_processes\", {})
    print(\"📹 FFmpeg Processes:\")
    print(\"   Running: {}/{}\".format(ffmpeg.get(\"count\", 0), ffmpeg.get(\"expected\", 2)))
    if ffmpeg.get(\"zombies\", 0) > 0:
        print(\"   🧟 Zombies: {}\".format(ffmpeg[\"zombies\"]))
    print()
    
    # Streams
    streams = d.get(\"streams\", {})
    for stream_name, stream_data in streams.items():
        if isinstance(stream_data, dict) and \"recording\" in stream_data:
            status = \"✅\" if stream_data[\"recording\"] else \"❌\"
            print(\"{} {}:\".format(status, stream_name.upper()))
            print(\"   File: {}\".format(stream_data.get(\"latest_file\", \"N/A\")))
            print(\"   Age: {}s\".format(stream_data.get(\"file_age_seconds\", \"N/A\")))
            print(\"   Size: {:.2f}MB\".format(stream_data.get(\"file_size_bytes\", 0) / 1024 / 1024))
        elif isinstance(stream_data, dict) and \"error\" in stream_data:
            print(\"❌ {}: {}\".format(stream_name.upper(), stream_data[\"error\"]))
        print()
    
    # Câmeras
    cameras = d.get(\"cameras\", {})
    print(\"🎥 Cameras: {} detected\".format(cameras.get(\"count\", 0)))
    
    # Disco
    disk = d.get(\"disk\", {})
    if \"usage_percent\" in disk:
        usage = disk[\"usage_percent\"]
        emoji = \"✅\" if usage < 80 else \"⚠️\" if usage < 90 else \"❌\"
        print(\"{} Disk: {}% used\".format(emoji, usage))
    
    # Temperatura
    system = d.get(\"system\", {})
    if \"cpu_temperature_celsius\" in system:
        temp = system[\"cpu_temperature_celsius\"]
        emoji = \"✅\" if temp < 60 else \"⚠️\" if temp < 70 else \"❌\"
        print(\"{} CPU: {:.1f}°C\".format(emoji, temp))
    
    print()
    
    # Issues
    issues = d.get(\"issues\", [])
    if issues:
        print(\"⚠️  ISSUES ({}):\".format(len(issues)))
        for i, issue in enumerate(issues[:5], 1):
            print(\"   {}. {}\".format(i, issue))
    else:
        print(\"✅ No issues detected\")
    
    print()
    print(\"=\"*60)
    
except json.JSONDecodeError as e:
    print(\"❌ Failed to parse JSON: {}\".format(e))
except Exception as e:
    print(\"❌ Error: {}\".format(e))
"'
