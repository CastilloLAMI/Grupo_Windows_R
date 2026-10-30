import io
import unittest

from PIL import Image

from src.app import crear_app


class DetectorFalso:
    def predecir(self, imagen):
        return {"emocion": "happy", "confianza": 90.0, "todas": {"happy": 90.0}}


def imagen_png():
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    buffer.seek(0)
    return buffer


class TestApi(unittest.TestCase):

    def setUp(self):
        self.cliente = crear_app(detector=DetectorFalso()).test_client()

    def test_salud(self):
        respuesta = self.cliente.get("/salud")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json(), {"estado": "ok"})

    def test_predecir_ok(self):
        datos = {"imagen": (imagen_png(), "rostro.png")}
        respuesta = self.cliente.post("/predecir", data=datos)
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json()["emocion"], "happy")

    def test_falta_imagen(self):
        respuesta = self.cliente.post("/predecir", data={})
        self.assertEqual(respuesta.status_code, 400)

    def test_nombre_vacio(self):
        datos = {"imagen": (io.BytesIO(b""), "")}
        respuesta = self.cliente.post("/predecir", data=datos)
        self.assertEqual(respuesta.status_code, 400)

    def test_formato_invalido(self):
        datos = {"imagen": (io.BytesIO(b"abc"), "rostro.gif")}
        respuesta = self.cliente.post("/predecir", data=datos)
        self.assertEqual(respuesta.status_code, 400)

    def test_crea_detector_por_defecto(self):
        self.assertIsNotNone(crear_app())


if __name__ == "__main__":
    unittest.main()
