"""Detector de emociones faciales con un modelo de Hugging Face."""


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
            self.clasificador = pipeline(
                "image-classification", model="abhilash88/face-emotion-detection"
            )
        return self.clasificador

    def predecir(self, imagen):
        """Devuelve la emoción principal y el porcentaje de cada clase."""
        r = self.cargar()(imagen)
        if not r:
            raise ValueError("El modelo no devolvió resultados")
        r = sorted(r, key=lambda x: x["score"], reverse=True)
        todas = {}
        for x in r:
            todas[x["label"]] = round(x["score"] * 100, 2)
        return {
            "emocion": r[0]["label"],
            "confianza": round(r[0]["score"] * 100, 2),
            "todas": todas,
        }
