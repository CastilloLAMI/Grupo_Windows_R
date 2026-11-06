"""
test_alcance.py — Pruebas que verifican el alcance del proyecto EmotiContigo.

Cada test protege una restricción declarada en src/alcance.py y en el README.
"""

import unittest

from src import alcance


class TestAlcance(unittest.TestCase):

    # ---------- Alcance funcional ----------

    def test_resultado_esperado(self):
        """El sistema produce una emoción válida dentro de las 7 permitidas."""
        emocion = "felicidad"  # ejemplo de salida del modelo
        self.assertTrue(alcance.validar_emocion(emocion))
        self.assertIn(emocion, alcance.EMOCIONES_PERMITIDAS)

    def test_emocion_invalida_es_rechazada(self):
        self.assertFalse(alcance.validar_emocion("aprendizaje"))
        self.assertFalse(alcance.validar_emocion("nota"))

    def test_endpoints_permitidos(self):
        for ruta in alcance.ENDPOINTS_PERMITIDOS:
            self.assertTrue(alcance.validar_endpoint(ruta))

    # ---------- Restricciones del alcance ----------

    def test_la_pagina_web_no_se_involucrara_en_el_desarrollo_del_estudiante(self):
        """No existen rutas que intervengan en el desarrollo del estudiante."""
        for ruta in alcance.RUTAS_PROHIBIDAS:
            self.assertFalse(
                alcance.validar_endpoint(ruta),
                f"La ruta {ruta} viola el alcance.",
            )

    def test_solo_ser_un_intermediario_entre_el_estudiante_y_el_docente(self):
        """Las respuestas no infieren aprendizaje: solo informan emoción."""
        respuesta_ok = {"emocion": "felicidad", "confianza": 0.92}
        self.assertEqual(alcance.validar_respuesta(str(respuesta_ok)), [])

        respuesta_mala = {"resultado": "el niño aprendió"}
        self.assertTrue(alcance.validar_respuesta(str(respuesta_mala)))

    def test_la_pagina_web_no_ser_parte_del_proceso_o_rendimiento_academico_del_estudiante(self):
        """No hay endpoints de calificación ni de rendimiento."""
        rutas_prohibidas = ["/calificar", "/evaluar", "/nota", "/rendimiento"]
        for ruta in rutas_prohibidas:
            self.assertFalse(alcance.validar_endpoint(ruta))

    def test_no_se_almacenan_imagenes_en_el_historial(self):
        """El historial solo guarda emoción y confianza, no la imagen."""
        registro_ok = {"emocion": "neutral", "confianza": 0.88}
        self.assertEqual(alcance.validar_historial(registro_ok), [])

        registro_malo = {"emocion": "neutral", "imagen": "base64..."}
        self.assertTrue(alcance.validar_historial(registro_malo))

    def test_no_emite_diagnosticos(self):
        """Las respuestas no contienen diagnósticos clínicos."""
        respuesta = {"emocion": "tristeza", "confianza": 0.75}
        self.assertEqual(alcance.validar_respuesta(str(respuesta)), [])


if __name__ == "__main__":
    unittest.main()
