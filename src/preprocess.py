"""Preparación de imágenes para el detector de emociones."""
import os

import numpy as np
from PIL import Image

# Clases de FER2013, en el orden de sus etiquetas (0 a 6)
EMOCIONES = ["enfado", "asco", "miedo", "felicidad", "tristeza", "sorpresa", "neutral"]
EXTENSIONES_VALIDAS = (".jpg", ".jpeg", ".png")
TAMANO_IMAGEN = 48
TOTAL_PIXELES = TAMANO_IMAGEN * TAMANO_IMAGEN
VALOR_MAXIMO_PIXEL = 255


def validar_extension(nombre_archivo):
    """Lanza ValueError si el archivo no es jpg, jpeg o png."""
    extension = os.path.splitext(nombre_archivo)[1].lower()
    if extension not in EXTENSIONES_VALIDAS:
        raise ValueError("Formato no permitido: " + extension)


def etiqueta_a_emocion(etiqueta):
    """Convierte la etiqueta de FER2013 (0 a 6) en el nombre de la emoción."""
    if etiqueta < 0 or etiqueta >= len(EMOCIONES):
        raise ValueError(f"Etiqueta fuera de rango (0-{len(EMOCIONES) - 1})")
    return EMOCIONES[etiqueta]


def pixeles_desde_texto(texto):
    """Convierte la columna 'pixels' de FER2013 en una matriz de 48x48."""
    valores = np.array(texto.split(), dtype=float)
    if len(valores) != TOTAL_PIXELES:
        raise ValueError(f"Se esperaban {TOTAL_PIXELES} píxeles")
    return valores.reshape(TAMANO_IMAGEN, TAMANO_IMAGEN)


def normalizar(imagen):
    """Escala los píxeles de 0-255 a 0-1."""
    return np.asarray(imagen, dtype=float) / VALOR_MAXIMO_PIXEL


def preparar_imagen(ruta):
    """Abre la imagen, la pasa a gris y la deja en 48x48."""
    validar_extension(ruta)
    imagen = Image.open(ruta).convert("L").resize((TAMANO_IMAGEN, TAMANO_IMAGEN))
    return normalizar(np.array(imagen))
