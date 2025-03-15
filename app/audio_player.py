import pygame
import time


def play_song(index):
    pygame.mixer.init()
    sound_file="./app/assets/goal.mp3"
    start_song="./app/assets/comecou.mp3"

    if index == 1:
      pygame.mixer.music.load(start_song)
    else:
      pygame.mixer.music.load(sound_file)

# Toca o som
    print("Tocando som...")
    pygame.mixer.music.play()

    # Espera até que o som termine de tocar
    while pygame.mixer.music.get_busy():
      time.sleep(0.1)

    print("Som finalizado.")
