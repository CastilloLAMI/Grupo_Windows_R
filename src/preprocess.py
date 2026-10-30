"""Preparación de imágenes para el detector de emociones."""
import os

import numpy as np
from PIL import Image

EMOCIONES = ["enfado", "asco", "miedo", "felicidad", "tristeza", "sorpresa", "neutral"]


def validar_extension(nombre_archivo):
    """Lanza ValueError si el archivo no es jpg, jpeg o png."""
    ext = os.path.splitext(nombre_archivo)[1].lower()
    if ext not in [".jpg", ".jpeg", ".png"]:
        raise ValueError("Formato no permitido: " + ext)


def etiqueta_a_emocion(etiqueta):
    """Convierte la etiqueta de FER2013 (0 a 6) en el nombre de la emoción."""
    if etiqueta < 0 or etiqueta > 6:
        raise ValueError("Etiqueta fuera de rango (0-6)")
    return EMOCIONES[etiqueta]


def pixeles_desde_texto(texto):
    """Convierte la columna 'pixels' de FER2013 en una matriz de 48x48."""
    valores = np.array(texto.split(), dtype=float)
    if len(valores) != 2304:
        raise ValueError("Se esperaban 2304 píxeles")
    return valores.reshape(48, 48)


def normalizar(imagen):
    """Escala los píxeles de 0-255 a 0-1."""
    return np.asarray(imagen, dtype=float) / 255


def preparar_imagen(ruta):
    """Abre la imagen, la pasa a gris y la deja en 48x48."""
    validar_extension(ruta)
    img = Image.open(ruta).convert("L").resize((48, 48))
    return normalizar(np.array(img))
