import unittest

from src import constantes


class TestConstantes(unittest.TestCase):
    def test_tamano_maximo_es_5_mb(self):
        self.assertEqual(constantes.TAMANO_MAXIMO_BYTES, 5 * 1024 * 1024)

    def test_extensiones_permitidas(self):
        self.assertIn("jpg", constantes.EXTENSIONES_PERMITIDAS)
        self.assertIn("png", constantes.EXTENSIONES_PERMITIDAS)

    def test_limites_historial_coherentes(self):
        self.assertLessEqual(constantes.LIMITE_HISTORIAL_MIN, constantes.LIMITE_HISTORIAL_DEFECTO)
        self.assertLessEqual(constantes.LIMITE_HISTORIAL_DEFECTO, constantes.LIMITE_HISTORIAL_MAX)

    def test_siete_emociones(self):
        self.assertEqual(len(constantes.ETIQUETAS_FER2013), constantes.CANTIDAD_EMOCIONES)


if __name__ == "__main__":
    unittest.main()
