import os
import tempfile
import unittest

import numpy as np
from PIL import Image

from src.preprocess import (
    EMOCIONES, TOTAL_PIXELES, etiqueta_a_emocion, normalizar,
    pixeles_desde_texto, preparar_imagen, validar_extension,
)


def texto_pixeles(valor=0):
    return " ".join([str(valor)] * TOTAL_PIXELES)


class TestValidarExtension(unittest.TestCase):

    def test_acepta_png_y_jpg(self):
        validar_extension("foto.png")
        validar_extension("foto.JPG")
        validar_extension("foto.jpeg")
        validar_extension("foto.PNG")

    def test_acepta_rutas_con_puntos(self):
        validar_extension("carpeta.1/mi.foto.png")

    def test_rechaza_otro_formato(self):
        with self.assertRaises(ValueError):
            validar_extension("foto.gif")

    def test_rechaza_sin_extension(self):
        with self.assertRaises(ValueError):
            validar_extension("foto")


class TestEtiquetas(unittest.TestCase):

    def test_todas_las_emociones(self):
        for indice, emocion in enumerate(EMOCIONES):
            with self.subTest(indice=indice):
                self.assertEqual(etiqueta_a_emocion(indice), emocion)

    def test_etiqueta_felicidad(self):
        self.assertEqual(etiqueta_a_emocion(3), "felicidad")

    def test_etiqueta_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            etiqueta_a_emocion(7)
        with self.assertRaises(ValueError):
            etiqueta_a_emocion(-1)


class TestPixeles(unittest.TestCase):

    def test_convierte_a_48x48(self):
        self.assertEqual(pixeles_desde_texto(texto_pixeles(10)).shape, (48, 48))

    def test_conserva_los_valores(self):
        matriz = pixeles_desde_texto(texto_pixeles(10))
        self.assertEqual(matriz[0, 0], 10)
        self.assertEqual(matriz[-1, -1], 10)

    def test_cantidad_incorrecta(self):
        with self.assertRaises(ValueError):
            pixeles_desde_texto("1 2 3")

    def test_texto_vacio(self):
        with self.assertRaises(ValueError):
            pixeles_desde_texto("")

    def test_pixeles_no_numericos(self):
        with self.assertRaises(ValueError):
            pixeles_desde_texto("a b c")

    def test_rechaza_pixeles_fuera_de_rango(self):
        with self.assertRaises(ValueError):
            pixeles_desde_texto(texto_pixeles(256))
        with self.assertRaises(ValueError):
            pixeles_desde_texto(texto_pixeles(-1))

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

    def test_imagen_rgba_se_convierte_a_gris(self):
        with tempfile.TemporaryDirectory() as carpeta:
            ruta = os.path.join(carpeta, "rostro.png")
            Image.new("RGBA", (20, 20), color=(255, 0, 0, 0)).save(ruta)
            resultado = preparar_imagen(ruta)
        self.assertEqual(resultado.shape, (48, 48))
        self.assertLessEqual(resultado.max(), 1.0)

    def test_imagen_inexistente(self):
        with self.assertRaises(FileNotFoundError):
            preparar_imagen("no_existe.png")

    def test_rechaza_formato_invalido(self):
        with self.assertRaises(ValueError):
            preparar_imagen("rostro.bmp")


if __name__ == "__main__":
    unittest.main()
