# load_sprite.py
import pygame
from PIL import Image

def load_gif_frames(file_path, cell_size):
    """
    Loads a GIF and returns a list of Pygame surfaces scaled to cell_size.
    """
    gif = Image.open(file_path)
    frames = []

    try:
        while True:
            frame = gif.copy()
            frame = frame.convert("RGBA")
            frame = pygame.image.fromstring(frame.tobytes(), frame.size, frame.mode)
            frame = pygame.transform.scale(frame, (cell_size, cell_size))
            frames.append(frame)
            gif.seek(gif.tell() + 1)
    except EOFError:
        pass

    return frames
