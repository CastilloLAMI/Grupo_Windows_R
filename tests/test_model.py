import os
import sys
import unittest
from types import SimpleNamespace
from unittest import mock

from src.model import (
    MODELO_ID, TAREA, TOP_K, DetectorEmociones, etiqueta_a_emocion,
)
from src.preprocess import EMOCIONES

RESPUESTA_FALSA = [
    {"label": "LABEL_4", "score": 0.1},
    {"label": "LABEL_3", "score": 0.85},
    {"label": "LABEL_6", "score": 0.05},
]


class TestEtiquetas(unittest.TestCase):

    def test_traduce_las_siete_etiquetas(self):
        for indice, emocion in enumerate(EMOCIONES):
            with self.subTest(indice=indice):
                self.assertEqual(etiqueta_a_emocion(f"LABEL_{indice}"), emocion)

    def test_etiquetas_desconocidas_no_se_modifican(self):
        self.assertEqual(etiqueta_a_emocion("happy"), "happy")
        self.assertEqual(etiqueta_a_emocion("LABEL_9"), "LABEL_9")
        self.assertEqual(etiqueta_a_emocion("LABEL_x"), "LABEL_x")


class TestDetectorEmociones(unittest.TestCase):

    def test_emocion_principal(self):
        detector = DetectorEmociones(clasificador=lambda img: RESPUESTA_FALSA)
        resultado = detector.predecir("imagen")
        self.assertEqual(resultado["emocion"], "felicidad")
        self.assertEqual(resultado["confianza"], 85.0)

    def test_porcentajes_de_todas_las_clases(self):
        detector = DetectorEmociones(clasificador=lambda img: RESPUESTA_FALSA)
        todas = detector.predecir("imagen")["todas"]
        self.assertEqual(
            todas,
            {"felicidad": 85.0, "tristeza": 10.0, "neutral": 5.0},
        )

    def test_el_clasificador_recibe_la_imagen(self):
        clasificador = mock.Mock(return_value=RESPUESTA_FALSA)
        DetectorEmociones(clasificador=clasificador).predecir("rostro")
        clasificador.assert_called_once_with("rostro")

    def test_sin_resultados(self):
        detector = DetectorEmociones(clasificador=lambda img: [])
        with self.assertRaises(ValueError):
            detector.predecir("imagen")

    def test_carga_modelo_de_hugging_face(self):
        pipeline_falso = mock.Mock(return_value=lambda img: RESPUESTA_FALSA)
        falso = SimpleNamespace(pipeline=pipeline_falso)
        with (
            mock.patch.dict(sys.modules, {"transformers": falso}),
            mock.patch.dict(os.environ, {"EMOTI_MODELO": ""}),
        ):
            detector = DetectorEmociones()
            self.assertEqual(detector.predecir("imagen")["emocion"], "felicidad")
        pipeline_falso.assert_called_once_with(
            TAREA, model=MODELO_ID, top_k=TOP_K,
        )

    def test_usa_la_ruta_local_del_modelo(self):
        pipeline_falso = mock.Mock(return_value=lambda img: RESPUESTA_FALSA)
        falso = SimpleNamespace(pipeline=pipeline_falso)
        with mock.patch.dict(sys.modules, {"transformers": falso}):
            detector = DetectorEmociones(ruta_modelo="models/face-emotion-detection")
            detector.predecir("imagen")
        pipeline_falso.assert_called_once_with(
            TAREA, model="models/face-emotion-detection", top_k=TOP_K,
        )

    def test_carga_una_sola_vez(self):
        clasificador = mock.Mock(return_value=RESPUESTA_FALSA)
        detector = DetectorEmociones(clasificador=clasificador)
        self.assertIs(detector.cargar(), clasificador)
        self.assertIs(detector.cargar(), clasificador)


if __name__ == "__main__":
    unittest.main()
