"""División de imágenes grandes o de relación de aspecto extrema en tiles para OCR."""

import math

from PIL import Image

MAX_DIMENSION = 3000   # px, lado máximo antes de necesitar downscale o tiling
MAX_GRID = 3           # tope de filas/columnas en la grilla de tiling
TILE_OVERLAP_RATIO = 0.10  # 10% de solapamiento entre tiles


def prepare_tiles(image_path: str) -> list[Image.Image]:
    """Aplica downscale y/o tiling según haga falta y devuelve las imágenes a transcribir.

    Si la imagen ya entra dentro de `MAX_DIMENSION` en ambos lados, devuelve una lista
    con la imagen sin modificar. Si algún lado supera `MAX_DIMENSION`, se calcula una
    grilla de filas/columnas (según cuántas veces entra `MAX_DIMENSION` en cada lado,
    con tope `MAX_GRID`x`MAX_GRID`) y se recortan los tiles con solapamiento entre
    ellos, preservando la mayor resolución original posible. Si un tile individual
    sigue superando `MAX_DIMENSION` (la grilla se topó con `MAX_GRID`), ese tile se
    redimensiona proporcionalmente antes de devolverlo.

    Args:
        image_path: ruta a la imagen a preparar.

    Devuelve la lista de tiles en orden de lectura (de arriba hacia abajo,
    de izquierda a derecha).
    """
    image = Image.open(image_path)
    width, height = image.size

    cols = min(math.ceil(width / MAX_DIMENSION), MAX_GRID) if width > MAX_DIMENSION else 1
    rows = min(math.ceil(height / MAX_DIMENSION), MAX_GRID) if height > MAX_DIMENSION else 1

    if cols == 1 and rows == 1:
        return [image]

    tile_width = width / cols
    tile_height = height / rows
    overlap_x = tile_width * TILE_OVERLAP_RATIO
    overlap_y = tile_height * TILE_OVERLAP_RATIO

    tiles = []
    for row in range(rows):
        top = max(0, round(row * tile_height - overlap_y))
        bottom = min(height, round((row + 1) * tile_height + overlap_y))
        for col in range(cols):
            left = max(0, round(col * tile_width - overlap_x))
            right = min(width, round((col + 1) * tile_width + overlap_x))
            tile = image.crop((left, top, right, bottom))
            tiles.append(_downscale_if_needed(tile))

    return tiles


def _downscale_if_needed(image: Image.Image) -> Image.Image:
    """Redimensiona `image` proporcionalmente si su lado mayor supera `MAX_DIMENSION`."""
    width, height = image.size
    max_side = max(width, height)
    if max_side <= MAX_DIMENSION:
        return image

    scale = MAX_DIMENSION / max_side
    new_size = (round(width * scale), round(height * scale))
    return image.resize(new_size)
