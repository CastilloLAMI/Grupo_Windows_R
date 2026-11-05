import io
import os
import tempfile
import unittest
from unittest import mock

from PIL import Image

from src.app import crear_app
from src.preprocess import EMOCIONES


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
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta_bd = os.path.join(self.carpeta.name, "prueba.db")
        self.app = crear_app(detector=DetectorFalso(), ruta_bd=self.ruta_bd)
        self.cliente = self.app.test_client()

    def tearDown(self):
        self.carpeta.cleanup()

    def test_salud(self):
        respuesta = self.cliente.get("/salud")
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.get_json(), {"estado": "ok"})

    def test_rutas_registradas(self):
        rutas = {regla.rule for regla in self.app.url_map.iter_rules()}
        self.assertIn("/salud", rutas)
        self.assertIn("/predecir", rutas)
        self.assertIn("/estadisticas", rutas)
        self.assertIn("/historial", rutas)

    def test_predecir_ok(self):
        respuesta = self.cliente.post("/predecir", data=imagen_png())
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(
            respuesta.get_json(),
            {"emocion": "felicidad", "confianza": 90.0, "todas": {"felicidad": 90.0}},
        )

    def test_predecir_guarda_historial(self):
        self.cliente.post("/predecir", data=imagen_png())
        historial = self.cliente.get("/historial").get_json()
        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["emocion"], "felicidad")
        self.assertEqual(historial[0]["confianza"], 90.0)
        self.assertEqual(historial[0]["todas"], {"felicidad": 90.0})

    def test_estadisticas_vacias(self):
        datos = self.cliente.get("/estadisticas").get_json()
        self.assertEqual(datos["total"], 0)
        self.assertEqual(datos["promedio_confianza"], 0.0)
        self.assertEqual(set(datos["por_emocion"]), set(EMOCIONES))

    def test_estadisticas_con_analisis(self):
        self.cliente.post("/predecir", data=imagen_png())
        self.cliente.post("/predecir", data=imagen_png())
        datos = self.cliente.get("/estadisticas").get_json()
        self.assertEqual(datos["total"], 2)
        self.assertEqual(datos["por_emocion"]["felicidad"], 2)
        self.assertEqual(datos["promedio_confianza"], 90.0)

    def test_historial_respeta_el_limite(self):
        for _ in range(3):
            self.cliente.post("/predecir", data=imagen_png())
        historial = self.cliente.get("/historial?limite=2").get_json()
        self.assertEqual(len(historial), 2)

    def test_historial_limite_invalido(self):
        for limite in ("0", "101", "abc"):
            with self.subTest(limite=limite):
                respuesta = self.cliente.get(f"/historial?limite={limite}")
                self.assertEqual(respuesta.status_code, 400)
                self.assertIn("límite", respuesta.get_json()["error"].lower())

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
        cliente = crear_app(detector=detector, ruta_bd=self.ruta_bd).test_client()
        cliente.post("/predecir", data={"imagen": (io.BytesIO(b"x"), "roto.png")})
        detector.predecir.assert_not_called()

    def test_archivo_demasiado_grande(self):
        self.app.config["MAX_CONTENT_LENGTH"] = 1024
        datos = {"imagen": (io.BytesIO(b"x" * 4096), "grande.png")}
        respuesta = self.cliente.post("/predecir", data=datos)
        self.assertEqual(respuesta.status_code, 413)
        self.assertIn("límite", respuesta.get_json()["error"])

    def test_crea_detector_por_defecto(self):
        self.assertIsNotNone(crear_app(ruta_bd=self.ruta_bd))


if __name__ == "__main__":
    unittest.main()
