import os
import time 
import subprocess 

def generateThumb(file):
    print(f'Generating thumb for {file}')
    command = f'ffmpeg -loglevel error -y -i ./{file} -ss 00:00:01.000 -vframes 1 {file}.jpeg '
    proc = os.popen(command)
    proc.close()

def convertFile(filepath):
    # command =  f'ffmpeg -loglevel error -y -i {filepath} -c:v copy {filepath}.mp4 && rm -rf {filepath}'
    command =  (f'ffmpeg -fflags +genpts '
                # f'-loglevel error -y '
                f'-i {filepath} -vf "hflip,format=yuv420p" -b:v 2M -pix_fmt yuv420p '
                f'-movflags +faststart '
                f'-colorspace bt709 -color_trc bt709 -color_primaries bt709 -color_range pc '
                f'-an '
                f'{filepath}.mp4 && rm -rf {filepath}')
    # proc = os.popen(command)
    subprocess.run(command, shell=True, check=True)
    # time.sleep(2)
    generateThumb(f'{filepath}.mp4')
    # proc.close()

def listar_arquivos_sem_extensao(diretorio):
    # Lista todos os arquivos no diretório especificado
    arquivos = os.listdir(diretorio)
    
    # Filtra os arquivos que não possuem extensão
    arquivos_sem_extensao = [arquivo for arquivo in arquivos if '.' not in arquivo]
    
    # Imprime o nome dos arquivos sem extensão
    for arquivo in arquivos_sem_extensao:
        convertFile(f'{diretorio}/{arquivo}')

# Exemplo de uso
# diretorio = 'output'
# listar_arquivos_sem_extensao(diretorio)