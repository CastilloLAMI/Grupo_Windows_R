import unittest


from src.app import CAMPO_IMAGEN, validar_archivo




class ArchivoFalso:
    def __init__(self, filename):
        self.filename = filename




class TestValidarArchivo(unittest.TestCase):
    def test_falta_el_campo_imagen(self):
        with self.assertRaises(ValueError):
            validar_archivo({})


    def test_nombre_vacio(self):
        with self.assertRaises(ValueError):
            validar_archivo({CAMPO_IMAGEN: ArchivoFalso("")})


    def test_extension_no_permitida(self):
        with self.assertRaises(ValueError):
            validar_archivo({CAMPO_IMAGEN: ArchivoFalso("documento.txt")})


    def test_archivo_valido(self):
        archivo = ArchivoFalso("foto.png")
        self.assertIs(validar_archivo({CAMPO_IMAGEN: archivo}), archivo)




if __name__ == "__main__":
    unittest.main()
