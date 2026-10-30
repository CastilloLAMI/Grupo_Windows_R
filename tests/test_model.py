import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from src.model import DetectorEmociones

RESPUESTA_FALSA = [
    {"label": "sad", "score": 0.1},
    {"label": "happy", "score": 0.85},
    {"label": "neutral", "score": 0.05},
]


class TestDetectorEmociones(unittest.TestCase):

    def test_emocion_principal(self):
        detector = DetectorEmociones(clasificador=lambda img: RESPUESTA_FALSA)
        resultado = detector.predecir("imagen")
        self.assertEqual(resultado["emocion"], "happy")
        self.assertEqual(resultado["confianza"], 85.0)

    def test_porcentajes_de_todas_las_clases(self):
        detector = DetectorEmociones(clasificador=lambda img: RESPUESTA_FALSA)
        todas = detector.predecir("imagen")["todas"]
        self.assertEqual(todas, {"happy": 85.0, "sad": 10.0, "neutral": 5.0})

    def test_sin_resultados(self):
        detector = DetectorEmociones(clasificador=lambda img: [])
        with self.assertRaises(ValueError):
            detector.predecir("imagen")

    def test_carga_modelo_de_hugging_face(self):
        # Se reemplaza transformers por uno falso para no descargar el modelo
        pipeline_falso = mock.Mock(return_value=lambda img: RESPUESTA_FALSA)
        falso = SimpleNamespace(pipeline=pipeline_falso)
        with mock.patch.dict(sys.modules, {"transformers": falso}):
            detector = DetectorEmociones()
            self.assertEqual(detector.predecir("imagen")["emocion"], "happy")
        pipeline_falso.assert_called_once()

    def test_carga_una_sola_vez(self):
        clasificador = mock.Mock(return_value=RESPUESTA_FALSA)
        detector = DetectorEmociones(clasificador=clasificador)
        self.assertIs(detector.cargar(), clasificador)


if __name__ == "__main__":
    unittest.main()
