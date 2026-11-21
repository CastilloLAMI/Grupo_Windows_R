import csv
import os
import tempfile
import unittest

from src.historial import (
    exportar_csv, guardar_analisis, inicializar_bd, listar_historial, obtener_estadisticas,
)
from src.preprocess import EMOCIONES

RESULTADO = {
    "emocion": "felicidad",
    "confianza": 90.0,
    "todas": {"felicidad": 90.0, "neutral": 10.0},
}


class TestHistorial(unittest.TestCase):

    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "historial.db")
        inicializar_bd(self.ruta)

    def tearDown(self):
        self.carpeta.cleanup()

    def test_estadisticas_vacias(self):
        datos = obtener_estadisticas(self.ruta)
        self.assertEqual(datos["total"], 0)
        self.assertEqual(datos["promedio_confianza"], 0.0)
        self.assertEqual(set(datos["por_emocion"]), set(EMOCIONES))
        self.assertTrue(all(valor == 0 for valor in datos["por_emocion"].values()))

    def test_guarda_y_recupera(self):
        fecha = guardar_analisis(RESULTADO, self.ruta)
        self.assertIsInstance(fecha, str)

        historial = listar_historial(self.ruta)
        self.assertEqual(len(historial), 1)
        self.assertEqual(historial[0]["emocion"], "felicidad")
        self.assertEqual(historial[0]["confianza"], 90.0)
        self.assertEqual(historial[0]["todas"], RESULTADO["todas"])

    def test_estadisticas_con_datos(self):
        guardar_analisis(RESULTADO, self.ruta)
        guardar_analisis({**RESULTADO, "confianza": 80.0}, self.ruta)

        datos = obtener_estadisticas(self.ruta)
        self.assertEqual(datos["total"], 2)
        self.assertEqual(datos["por_emocion"]["felicidad"], 2)
        self.assertEqual(datos["promedio_confianza"], 85.0)

    def test_historial_mas_reciente_primero(self):
        guardar_analisis({**RESULTADO, "emocion": "enfado"}, self.ruta)
        guardar_analisis(RESULTADO, self.ruta)

        emociones = [fila["emocion"] for fila in listar_historial(self.ruta)]
        self.assertEqual(emociones, ["felicidad", "enfado"])

    def test_historial_respeta_limite(self):
        for _ in range(3):
            guardar_analisis(RESULTADO, self.ruta)

        self.assertEqual(len(listar_historial(self.ruta, limite=2)), 2)

    def test_exportar_csv(self):
        guardar_analisis(RESULTADO, self.ruta)
        ruta_csv = os.path.join(self.carpeta.name, "historial.csv")
        cantidad = exportar_csv(listar_historial(self.ruta), ruta_csv)
        self.assertEqual(cantidad, 1)
        with open(ruta_csv, newline="", encoding="utf-8-sig") as archivo:
            filas = list(csv.reader(archivo))
        self.assertEqual(filas[0][:4], ["id", "fecha", "emocion", "confianza"])
        self.assertEqual(filas[0][4:], list(EMOCIONES))
        self.assertEqual(filas[1][2], "felicidad")
        self.assertEqual(float(filas[1][4 + EMOCIONES.index("neutral")]), 10.0)
        self.assertEqual(float(filas[1][4 + EMOCIONES.index("asco")]), 0.0)

    def test_exportar_csv_vacio(self):
        ruta_csv = os.path.join(self.carpeta.name, "vacio.csv")
        self.assertEqual(exportar_csv([], ruta_csv), 0)
        with open(ruta_csv, newline="", encoding="utf-8-sig") as archivo:
            self.assertEqual(len(list(csv.reader(archivo))), 1)


if __name__ == "__main__":
    unittest.main()
