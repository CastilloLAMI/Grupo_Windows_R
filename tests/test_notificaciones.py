import unittest
from unittest.mock import patch

from src import notificaciones as n


class TestNotificaciones(unittest.TestCase):
    def test_notifica_emocion_de_alerta_con_alta_confianza(self):
        self.assertTrue(n.debe_notificar("tristeza", 85))

    def test_no_notifica_felicidad(self):
        self.assertFalse(n.debe_notificar("felicidad", 95))

    def test_no_notifica_con_baja_confianza(self):
        self.assertFalse(n.debe_notificar("miedo", 40))

    def test_sin_credenciales_no_envia(self):
        with patch.dict("os.environ", {}, clear=True):
            self.assertFalse(n.enviar_telegram("hola"))

    @patch("src.notificaciones.threading.Thread")
    def test_notificar_deteccion_lanza_un_hilo(self, mock_hilo):
        self.assertTrue(n.notificar_deteccion("tristeza", 90, "en clase"))
        mock_hilo.assert_called_once()
        mock_hilo.return_value.start.assert_called_once()

    @patch("src.notificaciones.threading.Thread")
    def test_notificar_deteccion_no_envia_si_no_es_alerta(self, mock_hilo):
        self.assertFalse(n.notificar_deteccion("felicidad", 95))
        mock_hilo.assert_not_called()

    @patch("src.notificaciones.notificar_deteccion", return_value=True)
    def test_notificar_rostros_envia_un_solo_aviso(self, mock_aviso):
        rostros = [
            {"emocion": "tristeza", "confianza": 80},
            {"emocion": "miedo", "confianza": 95},
            {"emocion": "felicidad", "confianza": 99},
        ]
        self.assertTrue(n.notificar_rostros(rostros))
        mock_aviso.assert_called_once_with("miedo", 95, "en 2 rostro(s)")

    @patch("src.notificaciones.notificar_deteccion")
    def test_notificar_rostros_sin_alertas(self, mock_aviso):
        resultado = n.notificar_rostros(
            [{"emocion": "neutral", "confianza": 90}]
        )
        self.assertFalse(resultado)
        mock_aviso.assert_not_called()


if __name__ == "__main__":
    unittest.main()
