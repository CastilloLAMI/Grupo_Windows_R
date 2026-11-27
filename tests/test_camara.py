import os
import tempfile
import time
import unittest

import numpy as np
from PIL import Image

from src.camara import (
    INTERVALO_ANALISIS_S, AnalizadorAula, Camara, DetectorRostros, ErrorCamara, MonitorCamara,
    color_emocion_bgr, COLOR_DEFECTO_BGR, dibujar_resultados, guardar_resultado_cuadro,
    recortar_rostro, resumen_grupo, toca_analizar, unir_camaras,
)
from src.historial import iniciar_sesion, inicializar_bd, listar_historial, obtener_estadisticas
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


class TestUnirCamaras(unittest.TestCase):
    """Dos cámaras del aula se guardan como una sola lectura."""

    def test_suma_los_rostros_y_marca_la_camara(self):
        camara_1 = {"rostros": [{"caja": (0, 0, 9, 9), "todas": distribucion(felicidad=80.0, neutral=20.0)}]}
        camara_2 = {"rostros": [
            {"caja": (1, 1, 9, 9), "todas": distribucion(felicidad=20.0, neutral=80.0)},
            {"caja": (2, 2, 9, 9), "todas": distribucion(felicidad=10.0, neutral=90.0)},
        ]}
        unido = unir_camaras([camara_1, camara_2])
        self.assertEqual(unido["total_rostros"], 3)
        self.assertEqual([r["camara"] for r in unido["rostros"]], [0, 1, 1])
        self.assertEqual(unido["predominante"], "neutral")
        self.assertAlmostEqual(unido["distribucion"]["neutral"], 63.33)

    def test_una_camara_sin_rostros(self):
        unido = unir_camaras([{"rostros": []}])
        self.assertEqual(unido, {"total_rostros": 0, "rostros": [], "predominante": None, "distribucion": {}})


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
        self.assertEqual(obtener_estadisticas(self.ruta)["lecturas"], 1)

    def test_guarda_en_la_sesion_indicada(self):
        sesion_id = iniciar_sesion("Matemática", "5.º A", ruta=self.ruta)
        resultado = {"rostros": [
            {"caja": (0, 0, 10, 10), "emocion": "sorpresa", "confianza": 70.0,
             "todas": distribucion(sorpresa=70.0)},
        ], "predominante": "sorpresa"}
        guardar_resultado_cuadro(resultado, self.ruta, sesion_id=sesion_id)
        registro = listar_historial(self.ruta, sesion_id=sesion_id)[0]
        self.assertEqual((registro["emocion"], registro["fuente"]), ("sorpresa", "camara"))


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


class CapturaInfinita(CapturaFalsa):
    def read(self):
        time.sleep(0.005)
        return True, cuadro_falso()


class AnalizadorFalso:
    def __init__(self, fallar=False):
        self.llamadas = 0
        self.fallar = fallar

    def analizar_cuadro(self, cuadro):
        if self.fallar:
            raise RuntimeError("fallo del modelo")
        self.llamadas += 1
        return {"total_rostros": 0, "rostros": [], "predominante": None, "distribucion": {}}


def esperar(condicion, limite=2.0):
    fin = time.monotonic() + limite
    while time.monotonic() < fin:
        if condicion():
            return True
        time.sleep(0.01)
    return False


class TestMonitorCamara(unittest.TestCase):

    def crear(self, captura=None, analizador=None, intervalo=5):
        self.guardados = []
        self.captura = captura or CapturaFalsa(cuadros=[cuadro_falso(), cuadro_falso()])
        self.analizador = analizador or AnalizadorFalso()
        camara = Camara(fabrica=lambda indice: self.captura)
        return MonitorCamara(camara, self.analizador, intervalo=intervalo, guardar=self.guardados.append)

    def test_sin_cuadro_no_analiza(self):
        monitor = self.crear()
        self.assertIsNone(monitor.paso_analisis(ahora=0.0))
        self.assertEqual(self.analizador.llamadas, 0)

    def test_respeta_el_intervalo(self):
        monitor = self.crear(intervalo=5)
        monitor.camara.abrir()
        monitor.paso_lectura()
        self.assertIsNotNone(monitor.paso_analisis(ahora=0.0))
        self.assertIsNone(monitor.paso_analisis(ahora=4.0))
        self.assertIsNotNone(monitor.paso_analisis(ahora=5.0))
        self.assertEqual(self.analizador.llamadas, 2)
        self.assertEqual(len(self.guardados), 2)

    def test_capturar_ahora_no_espera_el_intervalo(self):
        monitor = self.crear(intervalo=5)
        monitor.camara.abrir()
        monitor.paso_lectura()
        monitor.paso_analisis(ahora=0.0)
        monitor.capturar_ahora()
        self.assertIsNotNone(monitor.paso_analisis(ahora=1.0))
        self.assertIsNone(monitor.paso_analisis(ahora=2.0))

    def test_instantanea(self):
        monitor = self.crear()
        self.assertEqual(monitor.instantanea(), (None, None, 0))
        monitor.camara.abrir()
        monitor.paso_lectura()
        monitor.paso_analisis(ahora=0.0)
        cuadro, resultado, numero = monitor.instantanea()
        self.assertEqual(cuadro.shape, (ALTO, ANCHO, 3))
        self.assertEqual(resultado["total_rostros"], 0)
        self.assertEqual(numero, 1)

    def test_iniciar_analiza_y_detener_cierra_la_camara(self):
        monitor = self.crear(captura=CapturaInfinita(), intervalo=0)
        monitor.iniciar()
        monitor.iniciar()  # una segunda llamada no hace nada
        self.assertTrue(monitor.activo)
        self.assertTrue(esperar(lambda: monitor.numero_resultado > 0))
        monitor.detener()
        self.assertFalse(monitor.activo)
        self.assertTrue(self.captura.liberada)
        self.assertIsNone(monitor.error)

    def test_error_al_leer_detiene_el_monitor(self):
        monitor = self.crear(captura=CapturaFalsa(cuadros=[]))
        monitor.iniciar()
        self.assertTrue(esperar(lambda: not monitor.activo))
        self.assertIn("no entregó", monitor.error)
        monitor.detener()

    def test_error_del_modelo_detiene_el_monitor(self):
        monitor = self.crear(captura=CapturaInfinita(), analizador=AnalizadorFalso(fallar=True), intervalo=0)
        monitor.iniciar()
        self.assertTrue(esperar(lambda: not monitor.activo))
        self.assertEqual(monitor.error, "fallo del modelo")
        monitor.detener()

    def test_error_si_la_camara_no_abre(self):
        monitor = self.crear(captura=CapturaFalsa(abre=False))
        with self.assertRaises(ErrorCamara):
            monitor.iniciar()
        self.assertFalse(monitor.activo)


if __name__ == "__main__":
    unittest.main()
