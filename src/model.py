"""Detector de emociones faciales con un modelo de Hugging Face."""

MODELO_ID = "abhilash88/face-emotion-detection"
TAREA = "image-classification"
DECIMALES = 2


def a_porcentaje(puntaje):
    """Convierte un puntaje de 0-1 en porcentaje con 2 decimales."""
    return round(puntaje * 100, DECIMALES)


class DetectorEmociones:
    """Envuelve el pipeline de clasificación de imágenes.

    `clasificador` es cualquier función que reciba una imagen y devuelva
    una lista como [{"label": "happy", "score": 0.9}, ...]. Si no se pasa,
    se carga el modelo de Hugging Face la primera vez que se usa.
    """

    def __init__(self, clasificador=None):
        self.clasificador = clasificador

    def cargar(self):
        if self.clasificador is None:
            from transformers import pipeline
            self.clasificador = pipeline(TAREA, model=MODELO_ID)
        return self.clasificador

    def predecir(self, imagen):
        """Devuelve la emoción principal y el porcentaje de cada clase."""
        resultados = self.cargar()(imagen)
        if not resultados:
            raise ValueError("El modelo no devolvió resultados")
        ordenados = sorted(resultados, key=lambda r: r["score"], reverse=True)
        principal = ordenados[0]
        return {
            "emocion": principal["label"],
            "confianza": a_porcentaje(principal["score"]),
            "todas": {r["label"]: a_porcentaje(r["score"]) for r in ordenados},
        }
