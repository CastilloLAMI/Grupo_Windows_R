import io
import unittest


from PIL import Image


from src.app import MENSAJE_IMAGEN_INVALIDA, abrir_imagen


class ArchivoFalso:
    def __init__(self, contenido):
        self.stream = io.BytesIO(contenido)


def crear_png(tamano=(10, 10)):
    buffer = io.BytesIO()
    Image.new("L", tamano).save(buffer, "PNG")
    return buffer.getvalue()


class TestAbrirImagen(unittest.TestCase):
    def test_convierte_a_rgb(self):
        imagen = abrir_imagen(ArchivoFalso(crear_png()))
        self.assertEqual(imagen.mode, "RGB")


    def test_conserva_el_tamano(self):
        imagen = abrir_imagen(ArchivoFalso(crear_png((20, 30))))
        self.assertEqual(imagen.size, (20, 30))


    def test_imagen_corrupta(self):
        with self.assertRaises(ValueError) as contexto:
            abrir_imagen(ArchivoFalso(b"esto no es una imagen"))
        self.assertEqual(str(contexto.exception), MENSAJE_IMAGEN_INVALIDA)


if __name__ == "__main__":
    unittest.main()
