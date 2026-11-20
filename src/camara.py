"""Captura de la cámara del aula y análisis de los rostros de cada cuadro."""
import time

import cv2
import numpy as np
from PIL import Image

try:
    from src.historial import RUTA_POR_DEFECTO, guardar_analisis, inicializar_bd
    from src.preprocess import EMOCIONES
except ImportError:  # Permite ejecutar `python src/camara.py`
    from historial import RUTA_POR_DEFECTO, guardar_analisis, inicializar_bd
    from preprocess import EMOCIONES

INDICE_CAMARA_DEFECTO = 0
INTERVALO_ANALISIS_S = 5
MARGEN_ROSTRO = 0.2
TAMANO_MINIMO_ROSTRO = (60, 60)
FACTOR_ESCALA = 1.1
VECINOS_MINIMOS = 5
DECIMALES = 2
ARCHIVO_CASCADA = "haarcascade_frontalface_default.xml"

# Dibujo de los recuadros
GROSOR_RECUADRO = 2
ESCALA_TEXTO = 0.6
GROSOR_TEXTO = 2
SEPARACION_TEXTO = 8
COLOR_TEXTO = (20, 20, 20)
TITULO_VENTANA = "EmotiContigo - Camara (q para salir)"
TECLA_SALIR = "q"
ESPERA_TECLA_MS = 1

# Colores BGR (OpenCV) para cada emoción
COLORES_EMOCION_BGR = {
    "enfado": (69, 69, 214),
    "asco": (46, 139, 110),
    "miedo": (167, 94, 123),
    "felicidad": (0, 161, 224),
    "tristeza": (216, 125, 59),
    "sorpresa": (57, 123, 224),
    "neutral": (135, 143, 125),
}
COLOR_DEFECTO_BGR = (114, 155, 35)


class ErrorCamara(RuntimeError):
    """La cámara no se pudo abrir o dejó de entregar imágenes."""


class Camara:
    """Envuelve cv2.VideoCapture para abrir, leer y cerrar la cámara.

    `fabrica` es cualquier función que reciba el índice de la cámara y
    devuelva un objeto con isOpened(), read() y release(). Por defecto es
    cv2.VideoCapture; en las pruebas se reemplaza por una cámara falsa.
    """

    def __init__(self, indice=INDICE_CAMARA_DEFECTO, fabrica=None):
        self.indice = indice
        self.fabrica = fabrica or cv2.VideoCapture
        self.captura = None

    @property
    def abierta(self):
        return self.captura is not None and self.captura.isOpened()

    def abrir(self):
        if self.abierta:
            return self
        self.captura = self.fabrica(self.indice)
        if not self.captura.isOpened():
            self.cerrar()
            raise ErrorCamara(f"No se pudo abrir la cámara {self.indice}")
        return self

    def leer(self):
        """Devuelve el cuadro actual en formato BGR (alto x ancho x 3)."""
        if not self.abierta:
            raise ErrorCamara("La cámara no está abierta")
        correcto, cuadro = self.captura.read()
        if not correcto or cuadro is None:
            raise ErrorCamara("La cámara no entregó una imagen")
        return cuadro

    def cerrar(self):
        if self.captura is not None:
            self.captura.release()
        self.captura = None

    def __enter__(self):
        return self.abrir()

    def __exit__(self, *_):
        self.cerrar()


class DetectorRostros:
    """Ubica rostros en un cuadro con el clasificador Haar de OpenCV."""

    def __init__(self, cascada=None):
        if cascada is None:
            cascada = cv2.CascadeClassifier(cv2.data.haarcascades + ARCHIVO_CASCADA)
            if cascada.empty():
                raise ErrorCamara("No se encontró el clasificador de rostros de OpenCV")
        self.cascada = cascada

    def detectar(self, cuadro):
        """Devuelve una lista de recuadros (x, y, ancho, alto)."""
        gris = cv2.cvtColor(cuadro, cv2.COLOR_BGR2GRAY)
        rostros = self.cascada.detectMultiScale(
            gris,
            scaleFactor=FACTOR_ESCALA,
            minNeighbors=VECINOS_MINIMOS,
            minSize=TAMANO_MINIMO_ROSTRO,
        )
        return [tuple(int(valor) for valor in rostro) for rostro in rostros]


def recortar_rostro(cuadro, caja, margen=MARGEN_ROSTRO):
    """Recorta el rostro con un margen extra y lo devuelve como imagen RGB."""
    x, y, ancho, alto = caja
    extra_x = int(ancho * margen)
    extra_y = int(alto * margen)
    alto_cuadro, ancho_cuadro = cuadro.shape[:2]
    izquierda = max(0, x - extra_x)
    arriba = max(0, y - extra_y)
    derecha = min(ancho_cuadro, x + ancho + extra_x)
    abajo = min(alto_cuadro, y + alto + extra_y)
    recorte = cuadro[arriba:abajo, izquierda:derecha]
    if recorte.size == 0:
        raise ValueError("El recuadro del rostro está fuera de la imagen")
    return Image.fromarray(cv2.cvtColor(recorte, cv2.COLOR_BGR2RGB))


def resumen_grupo(rostros):
    """Promedia la distribución de todos los rostros del cuadro.

    Devuelve la emoción predominante y el porcentaje promedio de cada una.
    Sin rostros, la predominante es None y la distribución queda vacía.
    """
    if not rostros:
        return {"predominante": None, "distribucion": {}}
    distribucion = {}
    for emocion in EMOCIONES:
        suma = sum(rostro["todas"].get(emocion, 0.0) for rostro in rostros)
        distribucion[emocion] = round(suma / len(rostros), DECIMALES)
    predominante = max(EMOCIONES, key=lambda emocion: distribucion[emocion])
    return {"predominante": predominante, "distribucion": distribucion}


class AnalizadorAula:
    """Une la detección de rostros con el detector de emociones."""

    def __init__(self, detector_emociones, detector_rostros=None):
        self.detector_emociones = detector_emociones
        self.detector_rostros = detector_rostros or DetectorRostros()

    def analizar_cuadro(self, cuadro):
        """Analiza cada rostro del cuadro y resume el grupo.

        No guarda la imagen: solo devuelve recuadros, emociones y confianza.
        """
        rostros = []
        for caja in self.detector_rostros.detectar(cuadro):
            resultado = self.detector_emociones.predecir(recortar_rostro(cuadro, caja))
            rostros.append({"caja": caja, **resultado})
        resumen = resumen_grupo(rostros)
        return {
            "total_rostros": len(rostros),
            "rostros": rostros,
            "predominante": resumen["predominante"],
            "distribucion": resumen["distribucion"],
        }


def guardar_resultado_cuadro(resultado, ruta=RUTA_POR_DEFECTO):
    """Guarda en el historial un registro por rostro y devuelve cuántos guardó."""
    for rostro in resultado["rostros"]:
        guardar_analisis(rostro, ruta)
    return len(resultado["rostros"])


def color_emocion_bgr(emocion):
    return COLORES_EMOCION_BGR.get(emocion, COLOR_DEFECTO_BGR)


def dibujar_resultados(cuadro, rostros):
    """Devuelve una copia del cuadro con un recuadro y etiqueta por rostro."""
    salida = np.copy(cuadro)
    for rostro in rostros:
        x, y, ancho, alto = rostro["caja"]
        color = color_emocion_bgr(rostro["emocion"])
        cv2.rectangle(salida, (x, y), (x + ancho, y + alto), color, GROSOR_RECUADRO)
        texto = f"{rostro['emocion'].capitalize()} {rostro['confianza']:.0f}%"
        (ancho_texto, alto_texto), base = cv2.getTextSize(
            texto, cv2.FONT_HERSHEY_SIMPLEX, ESCALA_TEXTO, GROSOR_TEXTO,
        )
        arriba = max(0, y - alto_texto - base - SEPARACION_TEXTO)
        cv2.rectangle(salida, (x, arriba), (x + ancho_texto + SEPARACION_TEXTO, y), color, cv2.FILLED)
        cv2.putText(
            salida, texto, (x + SEPARACION_TEXTO // 2, y - base - SEPARACION_TEXTO // 2),
            cv2.FONT_HERSHEY_SIMPLEX, ESCALA_TEXTO, COLOR_TEXTO, GROSOR_TEXTO,
        )
    return salida


def toca_analizar(ultimo_analisis, ahora, intervalo=INTERVALO_ANALISIS_S):
    """Indica si ya pasó el intervalo desde el último análisis."""
    return ultimo_analisis is None or ahora - ultimo_analisis >= intervalo


def main(indice=INDICE_CAMARA_DEFECTO, intervalo=INTERVALO_ANALISIS_S):  # pragma: no cover
    """Prueba rápida: muestra la cámara y analiza los rostros cada `intervalo` segundos."""
    from src.model import DetectorEmociones

    inicializar_bd()
    analizador = AnalizadorAula(DetectorEmociones())
    rostros = []
    ultimo = None
    with Camara(indice) as camara:
        while True:
            cuadro = camara.leer()
            ahora = time.monotonic()
            if toca_analizar(ultimo, ahora, intervalo):
                resultado = analizador.analizar_cuadro(cuadro)
                guardar_resultado_cuadro(resultado)
                rostros = resultado["rostros"]
                ultimo = ahora
                print(f"Rostros: {resultado['total_rostros']} - Predominante: {resultado['predominante']}")
            cv2.imshow(TITULO_VENTANA, dibujar_resultados(cuadro, rostros))
            if cv2.waitKey(ESPERA_TECLA_MS) & 0xFF == ord(TECLA_SALIR):
                break
    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
