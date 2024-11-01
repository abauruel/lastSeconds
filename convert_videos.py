import os
import time 

def generateThumb(file):
    command = f'ffmpeg -loglevel error -y -i {file} -ss 00:00:03.000 -vframes 1 {file}.png'
    proc = os.popen(command)
    proc.close()

def convertFile(filepath):
    command =  f'ffmpeg -loglevel error -y -i {filepath} -c:v copy {filepath}.mp4 && rm -rf {filepath}'
    proc = os.popen(command)
    time.sleep(1)
    generateThumb(f'{filepath}.mp4')
    proc.close()

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