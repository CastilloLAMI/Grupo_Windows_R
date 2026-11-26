import csv
import json
import os
import sqlite3
import tempfile
import unittest

from src import alcance
from src.historial import (
    CURSO_ANTERIOR, FUENTE_ANTERIOR, FUENTE_CAMARA, FUENTE_IMAGEN, RUTA_ESQUEMA, TABLA_RESPALDO,
    VERSION_ESQUEMA, cerrar_sesion, conexion_bd, exportar_csv, guardar_analisis, guardar_lectura,
    iniciar_sesion, inicializar_bd, listar_historial, listar_sesiones, obtener_estadisticas,
    obtener_sesion, sesion_activa, version_esquema,
)
from src.preprocess import EMOCIONES

RESULTADO = {
    "emocion": "felicidad",
    "confianza": 90.0,
    "todas": {"felicidad": 90.0, "neutral": 10.0},
}


def rostro(emocion, confianza):
    return {"caja": (0, 0, 10, 10), "emocion": emocion, "confianza": confianza,
            "todas": {emocion: confianza}}


def cuadro(*rostros):
    lista = list(rostros)
    predominante = lista[0]["emocion"] if lista else None
    return {"total_rostros": len(lista), "rostros": lista, "predominante": predominante, "distribucion": {}}


class BaseBD(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "historial.db")
        inicializar_bd(self.ruta)

    def tearDown(self):
        self.carpeta.cleanup()


class TestEsquema(BaseBD):

    def test_crea_las_tres_tablas_y_la_version(self):
        with conexion_bd(self.ruta) as conexion:
            tablas = {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({"sesion", "lectura", "deteccion"} <= tablas)
        self.assertEqual(version_esquema(self.ruta), VERSION_ESQUEMA)

    def test_inicializar_dos_veces_no_falla(self):
        inicializar_bd(self.ruta)
        self.assertEqual(listar_sesiones(self.ruta), [])

    def test_el_esquema_tiene_una_columna_por_emocion(self):
        with conexion_bd(self.ruta) as conexion:
            columnas = {fila["name"] for fila in conexion.execute("PRAGMA table_info(deteccion)")}
        self.assertTrue(set(EMOCIONES) <= columnas)
        texto = RUTA_ESQUEMA.read_text(encoding="utf-8")
        for emocion in EMOCIONES:
            self.assertIn(f"'{emocion}'", texto)

    def test_ninguna_tabla_guarda_imagenes(self):
        """Privacidad: ninguna columna se llama imagen, foto, rostro, cara o pixel."""
        with conexion_bd(self.ruta) as conexion:
            for tabla in ("sesion", "lectura", "deteccion"):
                columnas = {fila["name"]: None for fila in conexion.execute(f"PRAGMA table_info({tabla})")}
                self.assertEqual(alcance.validar_historial(columnas), [], tabla)

    def test_rechaza_emociones_fuera_del_modelo(self):
        with self.assertRaises(sqlite3.IntegrityError):
            guardar_analisis({"emocion": "aprendizaje", "confianza": 50.0, "todas": {}}, self.ruta)

    def test_las_claves_foraneas_estan_activas(self):
        with self.assertRaises(sqlite3.IntegrityError):
            guardar_lectura(cuadro(rostro("felicidad", 80.0)), FUENTE_CAMARA, sesion_id=999, ruta=self.ruta)

    def test_borrar_una_sesion_borra_sus_lecturas_y_detecciones(self):
        sesion_id = iniciar_sesion("Matemática", "5.º A", ruta=self.ruta)
        guardar_lectura(cuadro(rostro("felicidad", 80.0)), FUENTE_CAMARA, sesion_id, self.ruta)
        with conexion_bd(self.ruta) as conexion:
            conexion.execute("DELETE FROM sesion WHERE id = ?", (sesion_id,))
        with conexion_bd(self.ruta) as conexion:
            self.assertEqual(conexion.execute("SELECT COUNT(*) FROM lectura").fetchone()[0], 0)
            self.assertEqual(conexion.execute("SELECT COUNT(*) FROM deteccion").fetchone()[0], 0)


class TestSesiones(BaseBD):

    def test_iniciar_y_cerrar(self):
        sesion_id = iniciar_sesion("  Matemática ", "5.º A", "Prof. Ana", self.ruta)
        activa = sesion_activa(self.ruta)
        self.assertEqual(activa["id"], sesion_id)
        self.assertEqual(activa["curso"], "Matemática")
        self.assertEqual(activa["docente"], "Prof. Ana")
        self.assertTrue(activa["activa"])

        self.assertTrue(cerrar_sesion(sesion_id, self.ruta))
        self.assertIsNone(sesion_activa(self.ruta))
        cerrada = obtener_sesion(sesion_id, self.ruta)
        self.assertFalse(cerrada["activa"])
        self.assertGreaterEqual(cerrada["fin"], cerrada["inicio"])

    def test_cerrar_dos_veces_o_una_inexistente(self):
        sesion_id = iniciar_sesion("Arte", "3.º B", ruta=self.ruta)
        self.assertTrue(cerrar_sesion(sesion_id, self.ruta))
        self.assertFalse(cerrar_sesion(sesion_id, self.ruta))
        self.assertFalse(cerrar_sesion(999, self.ruta))
        self.assertIsNone(obtener_sesion(999, self.ruta))

    def test_solo_una_sesion_abierta(self):
        primera = iniciar_sesion("Arte", "3.º B", ruta=self.ruta)
        segunda = iniciar_sesion("Música", "3.º B", ruta=self.ruta)
        self.assertEqual(sesion_activa(self.ruta)["id"], segunda)
        self.assertFalse(obtener_sesion(primera, self.ruta)["activa"])

    def test_docente_vacio_se_guarda_como_nulo(self):
        sesion_id = iniciar_sesion("Arte", "3.º B", "   ", self.ruta)
        self.assertIsNone(obtener_sesion(sesion_id, self.ruta)["docente"])

    def test_datos_obligatorios(self):
        for curso, grado in (("", "5.º A"), ("Arte", "  "), (None, "5.º A")):
            with self.subTest(curso=curso, grado=grado), self.assertRaises(ValueError):
                iniciar_sesion(curso, grado, ruta=self.ruta)

    def test_listar_cuenta_lecturas_y_detecciones(self):
        vacia = iniciar_sesion("Arte", "3.º B", ruta=self.ruta)
        con_datos = iniciar_sesion("Música", "3.º B", ruta=self.ruta)
        guardar_lectura(cuadro(rostro("felicidad", 80.0), rostro("neutral", 60.0)),
                        FUENTE_CAMARA, con_datos, self.ruta)
        guardar_lectura(cuadro(), FUENTE_CAMARA, con_datos, self.ruta)

        sesiones = listar_sesiones(self.ruta)
        self.assertEqual([sesion["id"] for sesion in sesiones], [con_datos, vacia])
        self.assertEqual((sesiones[0]["lecturas"], sesiones[0]["detecciones"]), (2, 2))
        self.assertEqual((sesiones[1]["lecturas"], sesiones[1]["detecciones"]), (0, 0))
        self.assertEqual(len(listar_sesiones(self.ruta, limite=1)), 1)


class TestLecturas(BaseBD):

    def test_guarda_y_recupera_un_analisis(self):
        fecha = guardar_analisis(RESULTADO, self.ruta)
        self.assertIsInstance(fecha, str)

        historial = listar_historial(self.ruta)
        self.assertEqual(len(historial), 1)
        registro = historial[0]
        self.assertEqual(registro["emocion"], "felicidad")
        self.assertEqual(registro["confianza"], 90.0)
        self.assertEqual(registro["fuente"], FUENTE_IMAGEN)
        self.assertIsNone(registro["sesion_id"])
        self.assertEqual(set(registro["todas"]), set(EMOCIONES))
        self.assertEqual(registro["todas"]["felicidad"], 90.0)
        self.assertEqual(registro["todas"]["neutral"], 10.0)
        self.assertEqual(registro["todas"]["asco"], 0.0)
        self.assertEqual(alcance.validar_historial(registro), [])

    def test_lectura_de_camara_con_varios_rostros(self):
        sesion_id = iniciar_sesion("Matemática", "5.º A", ruta=self.ruta)
        lectura_id = guardar_lectura(
            cuadro(rostro("felicidad", 80.0), rostro("sorpresa", 70.0)), FUENTE_CAMARA, sesion_id, self.ruta,
        )
        historial = listar_historial(self.ruta)
        self.assertEqual(len(historial), 2)
        self.assertTrue(all(registro["lectura_id"] == lectura_id for registro in historial))
        self.assertTrue(all(registro["sesion_id"] == sesion_id for registro in historial))
        with conexion_bd(self.ruta) as conexion:
            lectura = conexion.execute("SELECT * FROM lectura WHERE id = ?", (lectura_id,)).fetchone()
        self.assertEqual(lectura["total_rostros"], 2)
        self.assertEqual(lectura["predominante"], "felicidad")
        self.assertEqual(lectura["fuente"], FUENTE_CAMARA)

    def test_lectura_sin_rostros(self):
        lectura_id = guardar_lectura(cuadro(), FUENTE_CAMARA, ruta=self.ruta)
        self.assertIsInstance(lectura_id, int)
        self.assertEqual(listar_historial(self.ruta), [])
        self.assertEqual(obtener_estadisticas(self.ruta)["lecturas"], 1)

    def test_fuente_no_valida(self):
        with self.assertRaises(ValueError):
            guardar_lectura(cuadro(), "internet", ruta=self.ruta)

    def test_porcentajes_fuera_de_rango_se_limitan(self):
        guardar_analisis({"emocion": "miedo", "confianza": 100.0000001, "todas": {"miedo": -0.1}}, self.ruta)
        registro = listar_historial(self.ruta)[0]
        self.assertEqual(registro["confianza"], 100.0)
        self.assertEqual(registro["todas"]["miedo"], 0.0)

    def test_historial_mas_reciente_primero(self):
        guardar_analisis({**RESULTADO, "emocion": "enfado"}, self.ruta)
        guardar_analisis(RESULTADO, self.ruta)

        emociones = [fila["emocion"] for fila in listar_historial(self.ruta)]
        self.assertEqual(emociones, ["felicidad", "enfado"])

    def test_historial_respeta_limite(self):
        for _ in range(3):
            guardar_analisis(RESULTADO, self.ruta)

        self.assertEqual(len(listar_historial(self.ruta, limite=2)), 2)

    def test_historial_por_sesion(self):
        primera = iniciar_sesion("Arte", "3.º B", ruta=self.ruta)
        guardar_analisis(RESULTADO, self.ruta, sesion_id=primera)
        segunda = iniciar_sesion("Música", "3.º B", ruta=self.ruta)
        guardar_lectura(cuadro(rostro("tristeza", 60.0)), FUENTE_CAMARA, segunda, self.ruta)

        self.assertEqual([r["emocion"] for r in listar_historial(self.ruta, sesion_id=primera)], ["felicidad"])
        self.assertEqual([r["emocion"] for r in listar_historial(self.ruta, sesion_id=segunda)], ["tristeza"])
        self.assertEqual(len(listar_historial(self.ruta)), 2)


class TestEstadisticas(BaseBD):

    def test_estadisticas_vacias(self):
        datos = obtener_estadisticas(self.ruta)
        self.assertEqual(datos["total"], 0)
        self.assertEqual(datos["lecturas"], 0)
        self.assertEqual(datos["promedio_confianza"], 0.0)
        self.assertEqual(set(datos["por_emocion"]), set(EMOCIONES))
        self.assertTrue(all(valor == 0 for valor in datos["por_emocion"].values()))

    def test_estadisticas_con_datos(self):
        guardar_analisis(RESULTADO, self.ruta)
        guardar_analisis({**RESULTADO, "confianza": 80.0}, self.ruta)

        datos = obtener_estadisticas(self.ruta)
        self.assertEqual(datos["total"], 2)
        self.assertEqual(datos["lecturas"], 2)
        self.assertEqual(datos["por_emocion"]["felicidad"], 2)
        self.assertEqual(datos["promedio_confianza"], 85.0)

    def test_estadisticas_por_sesion(self):
        sesion_id = iniciar_sesion("Matemática", "5.º A", ruta=self.ruta)
        guardar_lectura(cuadro(rostro("felicidad", 80.0), rostro("neutral", 60.0)),
                        FUENTE_CAMARA, sesion_id, self.ruta)
        guardar_analisis({**RESULTADO, "emocion": "tristeza"}, self.ruta)

        datos = obtener_estadisticas(self.ruta, sesion_id=sesion_id)
        self.assertEqual(datos["total"], 2)
        self.assertEqual(datos["lecturas"], 1)
        self.assertEqual(datos["por_emocion"]["tristeza"], 0)
        self.assertEqual(datos["promedio_confianza"], 70.0)
        self.assertEqual(obtener_estadisticas(self.ruta)["total"], 3)


class TestMigracion(unittest.TestCase):
    """Una base de la versión 1 (tabla `analisis`) se convierte sin perder datos."""

    ESQUEMA_V1 = (
        "CREATE TABLE analisis (id INTEGER PRIMARY KEY AUTOINCREMENT, fecha TEXT NOT NULL, "
        "emocion TEXT NOT NULL, confianza REAL NOT NULL, todas TEXT NOT NULL)"
    )

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "antigua.db")
        with conexion_bd(self.ruta) as conexion:
            conexion.execute(self.ESQUEMA_V1)
            for fecha, emocion, confianza in (
                ("2026-11-19T15:00:00+00:00", "felicidad", 82.5),
                ("2026-11-20T16:30:00+00:00", "neutral", 64.0),
                ("2026-11-20T16:31:00+00:00", "desconocida", 50.0),
            ):
                conexion.execute(
                    "INSERT INTO analisis (fecha, emocion, confianza, todas) VALUES (?, ?, ?, ?)",
                    (fecha, emocion, confianza, json.dumps({emocion: confianza})),
                )

    def tearDown(self):
        self.carpeta.cleanup()

    def test_migra_a_una_sesion_de_historial_anterior(self):
        inicializar_bd(self.ruta)

        sesiones = listar_sesiones(self.ruta)
        self.assertEqual(len(sesiones), 1)
        sesion = sesiones[0]
        self.assertEqual(sesion["curso"], CURSO_ANTERIOR)
        self.assertEqual(sesion["inicio"], "2026-11-19T15:00:00+00:00")
        self.assertEqual(sesion["fin"], "2026-11-20T16:30:00+00:00")
        self.assertEqual(sesion["detecciones"], 2)

        historial = listar_historial(self.ruta)
        self.assertEqual([r["emocion"] for r in historial], ["neutral", "felicidad"])
        self.assertTrue(all(r["fuente"] == FUENTE_ANTERIOR for r in historial))
        self.assertEqual(historial[1]["todas"]["felicidad"], 82.5)

    def test_conserva_la_tabla_original_como_respaldo(self):
        inicializar_bd(self.ruta)
        inicializar_bd(self.ruta)  # la segunda vez no vuelve a migrar
        with conexion_bd(self.ruta) as conexion:
            respaldo = conexion.execute(f"SELECT COUNT(*) FROM {TABLA_RESPALDO}").fetchone()[0]
            tablas = {fila[0] for fila in conexion.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertEqual(respaldo, 3)
        self.assertNotIn("analisis", tablas)
        self.assertEqual(len(listar_sesiones(self.ruta)), 1)

    def test_si_reaparece_la_tabla_antigua_se_suma_al_respaldo(self):
        inicializar_bd(self.ruta)
        with conexion_bd(self.ruta) as conexion:
            conexion.execute(self.ESQUEMA_V1)
            conexion.execute(
                "INSERT INTO analisis (id, fecha, emocion, confianza, todas) VALUES (10, ?, 'miedo', 55.0, '{}')",
                ("2026-11-21T10:00:00+00:00",),
            )
        inicializar_bd(self.ruta)
        with conexion_bd(self.ruta) as conexion:
            self.assertEqual(conexion.execute(f"SELECT COUNT(*) FROM {TABLA_RESPALDO}").fetchone()[0], 4)
        self.assertEqual(len(listar_sesiones(self.ruta)), 2)


class TestExportarCsv(BaseBD):

    def test_exportar_csv(self):
        sesion_id = iniciar_sesion("Arte", "3.º B", ruta=self.ruta)
        guardar_analisis(RESULTADO, self.ruta, sesion_id=sesion_id)
        ruta_csv = os.path.join(self.carpeta.name, "historial.csv")
        cantidad = exportar_csv(listar_historial(self.ruta), ruta_csv)
        self.assertEqual(cantidad, 1)
        with open(ruta_csv, newline="", encoding="utf-8-sig") as archivo:
            filas = list(csv.reader(archivo))
        fin_emociones = 4 + len(EMOCIONES)
        self.assertEqual(filas[0][:4], ["id", "fecha", "emocion", "confianza"])
        self.assertEqual(filas[0][4:fin_emociones], list(EMOCIONES))
        self.assertEqual(filas[0][fin_emociones:], ["sesion_id", "fuente"])
        self.assertEqual(filas[1][2], "felicidad")
        self.assertEqual(float(filas[1][4 + EMOCIONES.index("neutral")]), 10.0)
        self.assertEqual(float(filas[1][4 + EMOCIONES.index("asco")]), 0.0)
        self.assertEqual(filas[1][fin_emociones:], [str(sesion_id), FUENTE_IMAGEN])

    def test_exportar_csv_vacio(self):
        ruta_csv = os.path.join(self.carpeta.name, "vacio.csv")
        self.assertEqual(exportar_csv([], ruta_csv), 0)
        with open(ruta_csv, newline="", encoding="utf-8-sig") as archivo:
            self.assertEqual(len(list(csv.reader(archivo))), 1)


if __name__ == "__main__":
    unittest.main()
