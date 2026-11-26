import io
import os
import tempfile
import unittest
from unittest import mock

from PIL import Image

from src.app import a_bgr, crear_app
from src.camara import DetectorRostros
from src.historial import cerrar_sesion, iniciar_sesion
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
        self.assertIn("/sesiones", rutas)
        self.assertIn("/", rutas)
        self.assertIn("/analizar-cuadro", rutas)
        self.assertIn("/sesiones/<int:sesion_id>/cerrar", rutas)

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
        self.assertEqual(historial[0]["todas"]["felicidad"], 90.0)
        self.assertEqual(set(historial[0]["todas"]), set(EMOCIONES))
        self.assertEqual(historial[0]["fuente"], "imagen")

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

    def test_sesiones_vacias(self):
        self.assertEqual(self.cliente.get("/sesiones").get_json(), [])

    def test_predecir_se_guarda_en_la_sesion_activa(self):
        sesion_id = iniciar_sesion("Matemática", "5.º A", ruta=self.ruta_bd)
        self.cliente.post("/predecir", data=imagen_png())
        cerrar_sesion(sesion_id, self.ruta_bd)
        self.cliente.post("/predecir", data=imagen_png())

        sesiones = self.cliente.get("/sesiones").get_json()
        self.assertEqual(len(sesiones), 1)
        self.assertEqual(sesiones[0]["detecciones"], 1)
        self.assertFalse(sesiones[0]["activa"])

        de_la_sesion = self.cliente.get(f"/historial?sesion_id={sesion_id}").get_json()
        self.assertEqual(len(de_la_sesion), 1)
        self.assertEqual(de_la_sesion[0]["sesion_id"], sesion_id)
        self.assertEqual(len(self.cliente.get("/historial").get_json()), 2)

        estadisticas = self.cliente.get(f"/estadisticas?sesion_id={sesion_id}").get_json()
        self.assertEqual(estadisticas["total"], 1)
        self.assertEqual(estadisticas["lecturas"], 1)

    def test_sesion_id_invalido(self):
        for ruta in ("/historial", "/estadisticas"):
            with self.subTest(ruta=ruta):
                respuesta = self.cliente.get(f"{ruta}?sesion_id=abc")
                self.assertEqual(respuesta.status_code, 400)
                respuesta = self.cliente.get(f"{ruta}?sesion_id=999")
                self.assertEqual(respuesta.status_code, 404)
                self.assertIn("999", respuesta.get_json()["error"])

    def test_pagina_de_inicio(self):
        respuesta = self.cliente.get("/")
        self.assertEqual(respuesta.status_code, 200)
        self.assertIn("text/html", respuesta.content_type)
        html = respuesta.get_data(as_text=True)
        respuesta.close()
        self.assertIn("EMOTICONTIGO", html)
        for ruta in ("/predecir", "/estadisticas", "/historial", "/sesiones"):
            self.assertIn(ruta, html)


class CascadaFalsa:
    """Imita el clasificador Haar de OpenCV: devuelve siempre los mismos recuadros."""

    def __init__(self, rostros):
        self.rostros = rostros

    def detectMultiScale(self, gris, **argumentos):
        return self.rostros


def cuadro_jpg(ancho=320, alto=240):
    buffer = io.BytesIO()
    Image.new("RGB", (ancho, alto), (200, 170, 150)).save(buffer, format="JPEG")
    buffer.seek(0)
    return {"imagen": (buffer, "cuadro.jpg")}


class TestSesionesYCamaraWeb(unittest.TestCase):
    """La cámara del navegador y las sesiones de clase, para usar todo desde el contenedor."""

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta_bd = os.path.join(self.carpeta.name, "web.db")
        rostros = DetectorRostros(CascadaFalsa([(10, 20, 60, 60), (150, 40, 60, 60)]))
        self.cliente = crear_app(
            detector=DetectorFalso(), ruta_bd=self.ruta_bd, detector_rostros=rostros,
        ).test_client()

    def tearDown(self):
        self.carpeta.cleanup()

    def abrir(self, **datos):
        cuerpo = {"curso": "Matemática", "grado_seccion": "5.º A", **datos}
        return self.cliente.post("/sesiones", json=cuerpo)

    def test_abrir_sesion(self):
        respuesta = self.abrir(docente="Prof. Ana")
        self.assertEqual(respuesta.status_code, 201)
        sesion = respuesta.get_json()
        self.assertTrue(sesion["activa"])
        self.assertEqual(sesion["curso"], "Matemática")
        self.assertEqual(sesion["docente"], "Prof. Ana")

    def test_abrir_sesion_con_datos_incompletos(self):
        self.assertEqual(self.abrir(curso="  ").status_code, 400)
        respuesta = self.cliente.post("/sesiones", data="no es json")
        self.assertEqual(respuesta.status_code, 400)
        self.assertIn("JSON", respuesta.get_json()["error"])

    def test_cerrar_sesion(self):
        sesion_id = self.abrir().get_json()["id"]
        respuesta = self.cliente.post(f"/sesiones/{sesion_id}/cerrar")
        self.assertEqual(respuesta.status_code, 200)
        self.assertFalse(respuesta.get_json()["activa"])
        self.assertEqual(self.cliente.post(f"/sesiones/{sesion_id}/cerrar").status_code, 409)
        self.assertEqual(self.cliente.post("/sesiones/999/cerrar").status_code, 404)

    def test_analizar_cuadro_sin_sesion(self):
        respuesta = self.cliente.post("/analizar-cuadro", data=cuadro_jpg())
        self.assertEqual(respuesta.status_code, 409)
        self.assertIn("sesión", respuesta.get_json()["error"])

    def test_analizar_cuadro_con_varios_rostros(self):
        sesion_id = self.abrir().get_json()["id"]
        respuesta = self.cliente.post("/analizar-cuadro", data=cuadro_jpg())
        self.assertEqual(respuesta.status_code, 200)
        datos = respuesta.get_json()
        self.assertEqual(datos["total_rostros"], 2)
        self.assertEqual(datos["rostros"][0]["caja"], [10, 20, 60, 60])
        self.assertEqual(datos["predominante"], "felicidad")
        self.assertEqual((datos["ancho"], datos["alto"]), (320, 240))
        self.assertEqual(datos["sesion_id"], sesion_id)

        historial = self.cliente.get(f"/historial?sesion_id={sesion_id}").get_json()
        self.assertEqual(len(historial), 2)
        self.assertTrue(all(registro["fuente"] == "camara" for registro in historial))
        self.assertEqual(self.cliente.get(f"/estadisticas?sesion_id={sesion_id}").get_json()["lecturas"], 1)

    def test_analizar_cuadro_valida_la_imagen(self):
        self.abrir()
        self.assertEqual(self.cliente.post("/analizar-cuadro").status_code, 400)
        malo = {"imagen": (io.BytesIO(b"no soy una imagen"), "cuadro.jpg")}
        respuesta = self.cliente.post("/analizar-cuadro", data=malo)
        self.assertEqual(respuesta.status_code, 400)

    def test_a_bgr_invierte_los_canales(self):
        bgr = a_bgr(Image.new("RGB", (2, 2), (255, 0, 0)))
        self.assertEqual(bgr.shape, (2, 2, 3))
        self.assertEqual(tuple(int(v) for v in bgr[0, 0]), (0, 0, 255))


class TestPrecarga(unittest.TestCase):
    """En Docker (EMOTI_PRECARGAR=1) el modelo se carga al crear la app."""

    class DetectorContado(DetectorFalso):
        def __init__(self):
            self.cargas = 0

        def cargar(self):
            self.cargas += 1

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta_bd = os.path.join(self.carpeta.name, "precarga.db")

    def tearDown(self):
        self.carpeta.cleanup()

    def test_precarga_con_la_variable(self):
        detector = self.DetectorContado()
        with mock.patch.dict(os.environ, {"EMOTI_PRECARGAR": "1"}):
            crear_app(detector=detector, ruta_bd=self.ruta_bd)
        self.assertEqual(detector.cargas, 1)

    def test_sin_la_variable_no_precarga(self):
        detector = self.DetectorContado()
        with mock.patch.dict(os.environ, {"EMOTI_PRECARGAR": "0"}):
            crear_app(detector=detector, ruta_bd=self.ruta_bd)
        self.assertEqual(detector.cargas, 0)


if __name__ == "__main__":
    unittest.main()
