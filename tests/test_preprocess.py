import os
import tempfile
import unittest

import numpy as np
from PIL import Image

from src.preprocess import (
    etiqueta_a_emocion, normalizar, pixeles_desde_texto, preparar_imagen, validar_extension,
)


class TestValidarExtension(unittest.TestCase):

    def test_acepta_png_y_jpg(self):
        validar_extension("foto.png")
        validar_extension("foto.JPG")
        validar_extension("foto.jpeg")

    def test_rechaza_otro_formato(self):
        with self.assertRaises(ValueError):
            validar_extension("foto.gif")


class TestEtiquetas(unittest.TestCase):

    def test_etiqueta_felicidad(self):
        self.assertEqual(etiqueta_a_emocion(3), "felicidad")

    def test_primera_y_ultima(self):
        self.assertEqual(etiqueta_a_emocion(0), "enfado")
        self.assertEqual(etiqueta_a_emocion(6), "neutral")

    def test_etiqueta_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            etiqueta_a_emocion(7)
        with self.assertRaises(ValueError):
            etiqueta_a_emocion(-1)


class TestPixeles(unittest.TestCase):

    def test_convierte_a_48x48(self):
        texto = " ".join(["10"] * 2304)
        self.assertEqual(pixeles_desde_texto(texto).shape, (48, 48))

    def test_cantidad_incorrecta(self):
        with self.assertRaises(ValueError):
            pixeles_desde_texto("1 2 3")

    def test_normalizar(self):
        np.testing.assert_allclose(normalizar([0, 255, 51]), [0.0, 1.0, 0.2])


class TestPrepararImagen(unittest.TestCase):

    def test_imagen_queda_48x48_y_normalizada(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "rostro.png")
            Image.new("RGB", (100, 80), color=(255, 255, 255)).save(ruta)
            resultado = preparar_imagen(ruta)
        self.assertEqual(resultado.shape, (48, 48))
        self.assertAlmostEqual(resultado.max(), 1.0)

    def test_rechaza_formato_invalido(self):
        with self.assertRaises(ValueError):
            preparar_imagen("rostro.bmp")


if __name__ == "__main__":
    unittest.main()
