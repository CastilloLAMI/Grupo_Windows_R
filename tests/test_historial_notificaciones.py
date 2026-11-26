import os
import tempfile
import unittest
from unittest.mock import patch

from src import historial


class TestHistorialNotifica(unittest.TestCase):
    def setUp(self):
        self.carpeta = tempfile.TemporaryDirectory()
        self.ruta = os.path.join(self.carpeta.name, "prueba.db")
        historial.inicializar_bd(self.ruta)

    def tearDown(self):
        self.carpeta.cleanup()

    @patch("src.notificaciones.notificar_deteccion")
    def test_guardar_lectura_notifica_emocion_de_alerta(self, mock_aviso):
        rostro = {"emocion": "tristeza", "confianza": 90, "todas": {}}
        historial.guardar_lectura(
            {"rostros": [rostro], "predominante": "tristeza"},
            historial.FUENTE_CAMARA, None, self.ruta,
        )
        mock_aviso.assert_called_once()

    @patch("src.notificaciones.notificar_deteccion")
    def test_guardar_lectura_no_notifica_felicidad(self, mock_aviso):
        rostro = {"emocion": "felicidad", "confianza": 95, "todas": {}}
        historial.guardar_lectura(
            {"rostros": [rostro], "predominante": "felicidad"},
            historial.FUENTE_CAMARA, None, self.ruta,
        )
        mock_aviso.assert_not_called()

    @patch("src.notificaciones.notificar_deteccion")
    def test_guardar_analisis_notifica_emocion_de_alerta(self, mock_aviso):
        resultado = {"emocion": "miedo", "confianza": 88, "todas": {}}
        historial.guardar_analisis(resultado, self.ruta)
        mock_aviso.assert_called_once()
