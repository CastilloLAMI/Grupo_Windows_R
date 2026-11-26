import os
import tempfile
import unittest


from src.app import crear_app


class DetectorFalso:
    def predecir(self, imagen):
        return {"emocion": "neutral", "confianza": 100.0, "todas": {"neutral": 100.0}}


class TestRutasApp(unittest.TestCase):
    def setUp(self):
        carpeta = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        self.addCleanup(carpeta.cleanup)
        ruta_bd = os.path.join(carpeta.name, "prueba.db")
        self.cliente = crear_app(detector=DetectorFalso(), ruta_bd=ruta_bd).test_client()


    def test_salud(self):
        respuesta = self.cliente.get("/salud")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json(), {"estado": "ok"})


    def test_estadisticas_responde_200(self):
        self.assertEqual(self.cliente.get("/estadisticas").status_code, 200)


    def test_predecir_sin_imagen_da_400(self):
        self.assertEqual(self.cliente.post("/predecir").status_code, 400)


    def test_historial_limite_no_numerico_da_400(self):
        self.assertEqual(self.cliente.get("/historial?limite=abc").status_code, 400)


    def test_historial_limite_fuera_de_rango_da_400(self):
        self.assertEqual(self.cliente.get("/historial?limite=0").status_code, 400)
        self.assertEqual(self.cliente.get("/historial?limite=101").status_code, 400)


if __name__ == "__main__":
    unittest.main()
