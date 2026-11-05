"""Prueba de integración con el modelo real.

Se omite por defecto para que la suite sea rápida. Para ejecutarla:

    $env:EMOTI_INTEGRACION = "1"
    python -m unittest tests.test_integracion -v
"""
import os
import unittest

from PIL import Image

from src.model import DetectorEmociones
from src.preprocess import EMOCIONES

MODO_REAL = os.getenv("EMOTI_INTEGRACION") == "1"


@unittest.skipUnless(MODO_REAL, "Defina EMOTI_INTEGRACION=1 para usar el modelo real")
class TestIntegracionModelo(unittest.TestCase):

    def test_predice_las_siete_emociones(self):
        detector = DetectorEmociones()
        imagen = Image.new("RGB", (224, 224), color=(128, 128, 128))
        resultado = detector.predecir(imagen)
        self.assertIn(resultado["emocion"], EMOCIONES)
        self.assertEqual(set(resultado["todas"]), set(EMOCIONES))
        self.assertAlmostEqual(sum(resultado["todas"].values()), 100.0, delta=1.0)


if __name__ == "__main__":
    unittest.main()
