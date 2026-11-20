import os
import tempfile
import unittest

import numpy as np
from PIL import Image

from src.camara import (
    INTERVALO_ANALISIS_S, AnalizadorAula, Camara, DetectorRostros, ErrorCamara,
    color_emocion_bgr, COLOR_DEFECTO_BGR, dibujar_resultados, guardar_resultado_cuadro,
    recortar_rostro, resumen_grupo, toca_analizar,
)
from src.historial import inicializar_bd, listar_historial
from src.preprocess import EMOCIONES

ALTO = 240
ANCHO = 320


def cuadro_falso():
    return np.zeros((ALTO, ANCHO, 3), dtype=np.uint8)


def distribucion(**valores):
    todas = {emocion: 0.0 for emocion in EMOCIONES}
    todas.update(valores)
    return todas


class CapturaFalsa:
    def __init__(self, abre=True, cuadros=None):
        self.abre = abre
        self.cuadros = list(cuadros or [])
        self.liberada = False

    def isOpened(self):
        return self.abre and not self.liberada

    def read(self):
        if not self.cuadros:
            return False, None
        return True, self.cuadros.pop(0)

    def release(self):
        self.liberada = True


class CascadaFalsa:
    def __init__(self, rostros):
        self.rostros = rostros
        self.argumentos = None

    def detectMultiScale(self, gris, **argumentos):
        self.gris = gris
        self.argumentos = argumentos
        return self.rostros


class DetectorEmocionesFalso:
    def __init__(self, respuestas):
        self.respuestas = list(respuestas)
        self.imagenes = []

    def predecir(self, imagen):
        self.imagenes.append(imagen)
        return self.respuestas.pop(0)


class TestCamara(unittest.TestCase):

    def test_abre_lee_y_cierra(self):
        captura = CapturaFalsa(cuadros=[cuadro_falso()])
        camara = Camara(indice=1, fabrica=lambda indice: captura)
        with camara:
            self.assertTrue(camara.abierta)
            self.assertEqual(camara.leer().shape, (ALTO, ANCHO, 3))
        self.assertTrue(captura.liberada)
        self.assertFalse(camara.abierta)

    def test_pasa_el_indice_a_la_fabrica(self):
        indices = []

        def fabrica(indice):
            indices.append(indice)
            return CapturaFalsa()

        Camara(indice=2, fabrica=fabrica).abrir()
        self.assertEqual(indices, [2])

    def test_abrir_dos_veces_no_crea_otra_captura(self):
        creadas = []

        def fabrica(indice):
            creadas.append(indice)
            return CapturaFalsa()

        camara = Camara(fabrica=fabrica)
        camara.abrir()
        camara.abrir()
        self.assertEqual(len(creadas), 1)

    def test_error_si_no_se_puede_abrir(self):
        captura = CapturaFalsa(abre=False)
        camara = Camara(fabrica=lambda indice: captura)
        with self.assertRaises(ErrorCamara):
            camara.abrir()
        self.assertTrue(captura.liberada)

    def test_error_si_lee_sin_abrir(self):
        with self.assertRaises(ErrorCamara):
            Camara(fabrica=lambda indice: CapturaFalsa()).leer()

    def test_error_si_no_entrega_imagen(self):
        camara = Camara(fabrica=lambda indice: CapturaFalsa(cuadros=[])).abrir()
        with self.assertRaises(ErrorCamara):
            camara.leer()


class TestDetectorRostros(unittest.TestCase):

    def test_devuelve_recuadros_como_tuplas_de_enteros(self):
        cascada = CascadaFalsa(np.array([[10, 20, 60, 60]], dtype=np.int32))
        rostros = DetectorRostros(cascada).detectar(cuadro_falso())
        self.assertEqual(rostros, [(10, 20, 60, 60)])
        self.assertIsInstance(rostros[0][0], int)

    def test_trabaja_en_escala_de_grises(self):
        cascada = CascadaFalsa([])
        DetectorRostros(cascada).detectar(cuadro_falso())
        self.assertEqual(cascada.gris.shape, (ALTO, ANCHO))
        self.assertIn("minSize", cascada.argumentos)

    def test_sin_rostros(self):
        self.assertEqual(DetectorRostros(CascadaFalsa(())).detectar(cuadro_falso()), [])

    def test_carga_el_clasificador_de_opencv(self):
        self.assertFalse(DetectorRostros().cascada.empty())


class TestRecorte(unittest.TestCase):

    def test_devuelve_imagen_rgb_con_margen(self):
        recorte = recortar_rostro(cuadro_falso(), (100, 100, 50, 50), margen=0.2)
        self.assertIsInstance(recorte, Image.Image)
        self.assertEqual(recorte.mode, "RGB")
        self.assertEqual(recorte.size, (70, 70))

    def test_no_se_sale_del_borde(self):
        recorte = recortar_rostro(cuadro_falso(), (0, 0, 50, 50), margen=0.5)
        self.assertEqual(recorte.size, (75, 75))

    def test_convierte_bgr_a_rgb(self):
        cuadro = cuadro_falso()
        cuadro[:, :] = (255, 0, 0)  # azul en BGR
        recorte = recortar_rostro(cuadro, (0, 0, 10, 10), margen=0)
        self.assertEqual(recorte.getpixel((0, 0)), (0, 0, 255))

    def test_error_si_el_recuadro_esta_fuera(self):
        with self.assertRaises(ValueError):
            recortar_rostro(cuadro_falso(), (ANCHO + 10, ALTO + 10, 20, 20), margen=0)


class TestResumenGrupo(unittest.TestCase):

    def test_sin_rostros(self):
        self.assertEqual(resumen_grupo([]), {"predominante": None, "distribucion": {}})

    def test_promedia_la_distribucion(self):
        rostros = [
            {"todas": distribucion(felicidad=80.0, neutral=20.0)},
            {"todas": distribucion(felicidad=40.0, neutral=60.0)},
        ]
        resumen = resumen_grupo(rostros)
        self.assertEqual(resumen["predominante"], "felicidad")
        self.assertEqual(resumen["distribucion"]["felicidad"], 60.0)
        self.assertEqual(resumen["distribucion"]["neutral"], 40.0)
        self.assertEqual(set(resumen["distribucion"]), set(EMOCIONES))


class TestAnalizadorAula(unittest.TestCase):

    def test_analiza_cada_rostro(self):
        cascada = CascadaFalsa([(10, 10, 60, 60), (150, 50, 60, 60)])
        emociones = DetectorEmocionesFalso([
            {"emocion": "felicidad", "confianza": 82.0, "todas": distribucion(felicidad=82.0, neutral=18.0)},
            {"emocion": "neutral", "confianza": 64.0, "todas": distribucion(felicidad=36.0, neutral=64.0)},
        ])
        analizador = AnalizadorAula(emociones, DetectorRostros(cascada))
        resultado = analizador.analizar_cuadro(cuadro_falso())

        self.assertEqual(resultado["total_rostros"], 2)
        self.assertEqual(resultado["rostros"][0]["caja"], (10, 10, 60, 60))
        self.assertEqual(resultado["rostros"][1]["emocion"], "neutral")
        self.assertEqual(resultado["predominante"], "felicidad")
        self.assertEqual(len(emociones.imagenes), 2)
        self.assertTrue(all(isinstance(imagen, Image.Image) for imagen in emociones.imagenes))

    def test_cuadro_sin_rostros_no_llama_al_modelo(self):
        emociones = DetectorEmocionesFalso([])
        analizador = AnalizadorAula(emociones, DetectorRostros(CascadaFalsa([])))
        resultado = analizador.analizar_cuadro(cuadro_falso())
        self.assertEqual(resultado["total_rostros"], 0)
        self.assertIsNone(resultado["predominante"])
        self.assertEqual(emociones.imagenes, [])

    def test_el_resultado_no_incluye_imagenes(self):
        emociones = DetectorEmocionesFalso([
            {"emocion": "sorpresa", "confianza": 70.0, "todas": distribucion(sorpresa=70.0)},
        ])
        analizador = AnalizadorAula(emociones, DetectorRostros(CascadaFalsa([(10, 10, 50, 50)])))
        rostro = analizador.analizar_cuadro(cuadro_falso())["rostros"][0]
        self.assertEqual(set(rostro), {"caja", "emocion", "confianza", "todas"})


class TestGuardarResultado(unittest.TestCase):

    def setUp(self):
        descriptor, self.ruta = tempfile.mkstemp(suffix=".db")
        os.close(descriptor)
        inicializar_bd(self.ruta)

    def tearDown(self):
        os.remove(self.ruta)

    def test_guarda_un_registro_por_rostro(self):
        resultado = {"rostros": [
            {"caja": (0, 0, 10, 10), "emocion": "felicidad", "confianza": 80.0,
             "todas": distribucion(felicidad=80.0)},
            {"caja": (20, 0, 10, 10), "emocion": "neutral", "confianza": 60.0,
             "todas": distribucion(neutral=60.0)},
        ]}
        self.assertEqual(guardar_resultado_cuadro(resultado, self.ruta), 2)
        emociones = [registro["emocion"] for registro in listar_historial(self.ruta)]
        self.assertEqual(sorted(emociones), ["felicidad", "neutral"])

    def test_sin_rostros_no_guarda_nada(self):
        self.assertEqual(guardar_resultado_cuadro({"rostros": []}, self.ruta), 0)
        self.assertEqual(listar_historial(self.ruta), [])


class TestDibujo(unittest.TestCase):

    def test_dibuja_sin_modificar_el_original(self):
        cuadro = cuadro_falso()
        rostros = [{"caja": (50, 60, 80, 80), "emocion": "felicidad", "confianza": 82.0}]
        salida = dibujar_resultados(cuadro, rostros)
        self.assertEqual(salida.shape, cuadro.shape)
        self.assertEqual(int(cuadro.sum()), 0)
        self.assertGreater(int(salida.sum()), 0)

    def test_colores(self):
        self.assertEqual(len(color_emocion_bgr("felicidad")), 3)
        self.assertEqual(color_emocion_bgr("desconocida"), COLOR_DEFECTO_BGR)


class TestIntervalo(unittest.TestCase):

    def test_primer_analisis(self):
        self.assertTrue(toca_analizar(None, 0.0))

    def test_respeta_el_intervalo(self):
        self.assertFalse(toca_analizar(10.0, 10.0 + INTERVALO_ANALISIS_S - 1))
        self.assertTrue(toca_analizar(10.0, 10.0 + INTERVALO_ANALISIS_S))


if __name__ == "__main__":
    unittest.main()
