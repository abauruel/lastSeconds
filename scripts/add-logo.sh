#!/bin/bash
# script adiciona logo no canto inferior esquerdo dos videos.
# Lista todos os arquivos mp4 da pasta
DATA=$(date +%Y%m%d)
cd /media/pi/usb64gb/bts/streams/$DATA
ls -l
# Loop sobre cada arquivo mp4
i=1
for movie in *.mp4; do
    if [[ -f "$movie" ]]; then
        echo "Processando: $movie"
        echo "Processando $movie (arquivo $i)"
        # Exemplo de comando ffmpeg para adicionar logo
        ffmpeg -i "$movie" -i /home/pi/app/name_text_5.png -filter_complex "overlay=18:600" -codec:v h264_v4l2m2m -codec:a copy "$movie-logo.mp4"
        cp -f "$movie-logo.mp4" "$movie" # Substitui o arquivo original pelo novo com logo 
        ((i++))
    fi
done
