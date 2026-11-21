import ast
import unittest
from pathlib import Path

try:
    from src import interfaz
except ImportError:  # Sin tkinter (por ejemplo, un servidor sin interfaz gráfica)
    interfaz = None


class TestInterfaz(unittest.TestCase):
    RUTA = Path(__file__).resolve().parent.parent / "src" / "interfaz.py"

    def test_archivo_existe(self):
        self.assertTrue(self.RUTA.exists())

    def test_sintaxis_valida(self):
        codigo = self.RUTA.read_text(encoding="utf-8")
        arbol = ast.parse(codigo)
        self.assertIsNotNone(arbol)


@unittest.skipIf(interfaz is None, "tkinter no está disponible")
class TestFuncionesInterfaz(unittest.TestCase):

    def test_intervalo_y_camara(self):
        self.assertEqual(interfaz.segundos_intervalo(interfaz.texto_intervalo(10)), 10)
        self.assertEqual(interfaz.indice_camara("Cámara 2"), 2)

    def test_ajustar_tamano_mantiene_la_proporcion(self):
        self.assertEqual(interfaz.ajustar_tamano(640, 480, 320, 320), (320, 240))
        self.assertEqual(interfaz.ajustar_tamano(640, 360, 1000, 180), (320, 180))

    def test_segunda_emocion(self):
        self.assertEqual(
            interfaz.segunda_emocion({"felicidad": 80.0, "neutral": 15.0, "miedo": 5.0}),
            "Neutral (15.00 %)",
        )
        self.assertEqual(interfaz.segunda_emocion({"felicidad": 100.0}), interfaz.SIN_DATO)

    def test_filtrar_registros(self):
        registros = [{"emocion": "felicidad"}, {"emocion": "neutral"}]
        self.assertEqual(interfaz.filtrar_registros(registros), registros)
        self.assertEqual(interfaz.filtrar_registros(registros, "neutral"), [{"emocion": "neutral"}])

    def test_texto_lectura(self):
        resultado = {"total_rostros": 3, "predominante": "felicidad"}
        self.assertEqual(interfaz.texto_lectura(resultado, "10:42:15"), "10:42:15  ·  Felicidad  ·  3 rostros")
        resultado = {"total_rostros": 1, "predominante": "neutral"}
        self.assertIn("1 rostro", interfaz.texto_lectura(resultado, "10:42:20"))
        resultado = {"total_rostros": 0, "predominante": None}
        self.assertEqual(interfaz.texto_lectura(resultado, "10:42:25"), "10:42:25  ·  sin rostros")


if __name__ == "__main__":
    unittest.main()
