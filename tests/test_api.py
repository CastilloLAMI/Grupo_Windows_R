import io
import unittest
from unittest import mock

from PIL import Image

from src.app import crear_app


class DetectorFalso:
    def predecir(self, imagen):
        return {"emocion": "felicidad", "confianza": 90.0, "todas": {"felicidad": 90.0}}


def imagen_png(nombre="rostro.png"):
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="PNG")
    buffer.seek(0)
    return {"imagen": (buffer, nombre)}


class TestApi(unittest.TestCase):

    def setUp(self):
        self.app = crear_app(detector=DetectorFalso())
        self.cliente = self.app.test_client()

    def test_salud(self):
        respuesta = self.cliente.get("/salud")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json(), {"estado": "ok"})

    def test_rutas_registradas(self):
        rutas = {regla.rule for regla in self.app.url_map.iter_rules()}
        self.assertIn("/salud", rutas)
        self.assertIn("/predecir", rutas)

    def test_predecir_ok(self):
        respuesta = self.cliente.post("/predecir", data=imagen_png())
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.get_json(),
            {"emocion": "felicidad", "confianza": 90.0, "todas": {"felicidad": 90.0}},
        )

    def test_extension_mayuscula(self):
        respuesta = self.cliente.post("/predecir", data=imagen_png("ROSTRO.PNG"))
        self.assertEqual(respuesta.status_code, 200)

    def test_falta_imagen(self):
        respuesta = self.cliente.post("/predecir", data={})
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("imagen", respuesta.get_json()["error"])

    def test_nombre_vacio(self):
        datos = {"imagen": (io.BytesIO(b""), "")}
        respuesta = self.cliente.post("/predecir", data=datos)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("No se seleccionó", respuesta.get_json()["error"])

    def test_formato_invalido(self):
        datos = {"imagen": (io.BytesIO(b"abc"), "rostro.gif")}
        respuesta = self.cliente.post("/predecir", data=datos)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn(".gif", respuesta.get_json()["error"])

    def test_archivo_corrupto(self):
        datos = {"imagen": (io.BytesIO(b"no soy una imagen"), "roto.png")}
        respuesta = self.cliente.post("/predecir", data=datos)
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("no es una imagen válida", respuesta.get_json()["error"])

    def test_detector_no_se_usa_si_el_archivo_es_invalido(self):
        detector = mock.Mock()
        cliente = crear_app(detector=detector).test_client()
        cliente.post("/predecir", data={"imagen": (io.BytesIO(b"x"), "roto.png")})
        detector.predecir.assert_not_called()

    def test_archivo_demasiado_grande(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 1024
        datos = {"imagen": (io.BytesIO(b"x" * 4096), "grande.png")}
        respuesta = self.cliente.post("/predecir", data=datos)
        self.assertEqual(respuesta.status_code, 413)
        self.assertIn("límite", respuesta.get_json()["error"])

    def test_crea_detector_por_defecto(self):
        self.assertIsNotNone(crear_app())


if __name__ == "__main__":
    unittest.main()
