import unittest
from unittest.mock import patch

from src import notificaciones as n


class TestNotificaciones(unittest.TestCase):
    def test_notifica_emocion_de_alerta_con_alta_confianza(self):
        self.assertTrue(n.debe_notificar("tristeza", 85))

    def test_notifica_enfadado(self):
        self.assertTrue(n.debe_notificar("enfadado", 90))

    def test_no_notifica_felicidad(self):
        self.assertFalse(n.debe_notificar("felicidad", 95))

    def test_no_notifica_con_baja_confianza(self):
        self.assertFalse(n.debe_notificar("miedo", 40))

    def test_sin_credenciales_no_envia(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(n.enviar_telegram("hola"))

    @patch("src.notificaciones.threading.Thread")
    def test_notificar_deteccion_lanza_envio(self, mock_hilo):
        self.assertTrue(n.notificar_deteccion("tristeza", 90, "Matemática"))
        mock_hilo.return_value.start.assert_called_once()

    @patch("src.notificaciones.threading.Thread")
    def test_notificar_deteccion_ignora_emocion_normal(self, mock_hilo):
        self.assertFalse(n.notificar_deteccion("felicidad", 99))
        mock_hilo.assert_not_called()
