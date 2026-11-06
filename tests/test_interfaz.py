import ast
import unittest
from pathlib import Path


class TestInterfaz(unittest.TestCase):
    RUTA = Path(__file__).resolve().parent.parent / "src" / "interfaz.py"

    def test_archivo_existe(self):
        self.assertTrue(self.RUTA.exists())

    def test_sintaxis_valida(self):
        codigo = self.RUTA.read_text(encoding="utf-8")
        arbol = ast.parse(codigo)
        self.assertIsNotNone(arbol)


if __name__ == "__main__":
    unittest.main()
