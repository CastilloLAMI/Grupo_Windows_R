"""Detector de emociones faciales con un modelo de Hugging Face."""
import os

from src.preprocess import EMOCIONES, etiqueta_a_emocion as emocion_por_indice

MODELO_ID = "abhilash88/face-emotion-detection"
TAREA = "image-classification"
DECIMALES = 2
PREFIJO_ETIQUETA = "LABEL_"
TOP_K = len(EMOCIONES)


def a_porcentaje(puntaje):
    """Convierte un puntaje de 0-1 en porcentaje con 2 decimales."""
    return round(puntaje * 100, DECIMALES)


def etiqueta_a_emocion(etiqueta):
    """Traduce una etiqueta del modelo (LABEL_0 a LABEL_6) al español."""
    if not etiqueta.startswith(PREFIJO_ETIQUETA):
        return etiqueta
    try:
        indice = int(etiqueta[len(PREFIJO_ETIQUETA):])
    except ValueError:
        return etiqueta
    if indice < 0 or indice >= len(EMOCIONES):
        return etiqueta
    return emocion_por_indice(indice)


class DetectorEmociones:
    """Envuelve el pipeline de clasificación de imágenes.

    `clasificador` es cualquier función que reciba una imagen y devuelva
    una lista como [{"label": "LABEL_3", "score": 0.9}, ...]. Si no se pasa,
    se carga el modelo de Hugging Face la primera vez que se usa.

    `ruta_modelo` permite usar una copia local del modelo. Si no se indica,
    se toma la variable de entorno EMOTI_MODELO o se descarga de Hugging Face.
    """

    def __init__(self, clasificador=None, ruta_modelo=None):
        self.clasificador = clasificador
        self.ruta_modelo = ruta_modelo or os.getenv("EMOTI_MODELO") or None

    def cargar(self):
        if self.clasificador is None:
            from transformers import pipeline
            origen = self.ruta_modelo or MODELO_ID
            self.clasificador = pipeline(TAREA, model=origen, top_k=TOP_K)
        return self.clasificador

    def predecir(self, imagen):
        """Devuelve la emoción principal y el porcentaje de cada clase."""
        resultados = self.cargar()(imagen)
        if not resultados:
            raise ValueError("El modelo no devolvió resultados")
        ordenados = sorted(resultados, key=lambda r: r["score"], reverse=True)
        principal = ordenados[0]
        return {
            "emocion": etiqueta_a_emocion(principal["label"]),
            "confianza": a_porcentaje(principal["score"]),
            "todas": {
                etiqueta_a_emocion(r["label"]): a_porcentaje(r["score"])
                for r in ordenados
            },
        }
