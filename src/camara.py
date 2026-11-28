"""Captura de la cámara del aula y análisis de los rostros de cada cuadro."""
import sys
import threading
import time

import cv2
import numpy as np
from PIL import Image

try:
    from src.historial import FUENTE_CAMARA, RUTA_POR_DEFECTO, guardar_lectura, inicializar_bd
    from src.preprocess import EMOCIONES
except ImportError:  # Permite ejecutar `python src/camara.py`
    from historial import FUENTE_CAMARA, RUTA_POR_DEFECTO, guardar_lectura, inicializar_bd
    from preprocess import EMOCIONES

INDICE_CAMARA_DEFECTO = 0
INTERVALO_ANALISIS_S = 5
MARGEN_ROSTRO = 0.2
# El modelo se entrenó con rostros de 48x48 (FER2013): 30 px le alcanzan y así se
# captan estudiantes a varios metros de la cámara (con 60 px, solo a ~1 m)
TAMANO_MINIMO_ROSTRO = (30, 30)
# Resolución que se pide a la cámara: con más píxeles, los rostros lejanos se ven más grandes
RESOLUCION_CAMARA = (1280, 720)
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

# Monitor en segundo plano
ESPERA_ANALISIS_S = 0.1
ESPERA_DETENER_S = 2

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


def abrir_captura(indice):
    """Abre la cámara; en Windows usa DirectShow, que abre mucho más rápido."""
    if sys.platform.startswith("win"):  # pragma: no cover
        return cv2.VideoCapture(indice, cv2.CAP_DSHOW)
    return cv2.VideoCapture(indice)


class Camara:
    """Envuelve cv2.VideoCapture para abrir, leer y cerrar la cámara.

    `fabrica` es cualquier función que reciba el índice de la cámara y
    devuelva un objeto con isOpened(), read() y release(). Por defecto es
    cv2.VideoCapture; en las pruebas se reemplaza por una cámara falsa.
    """

    def __init__(self, indice=INDICE_CAMARA_DEFECTO, fabrica=None):
        self.indice = indice
        self.fabrica = fabrica or abrir_captura
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
        # Si la cámara no llega a esa resolución, OpenCV usa la más cercana que tenga
        ancho, alto = RESOLUCION_CAMARA
        self.captura.set(cv2.CAP_PROP_FRAME_WIDTH, ancho)
        self.captura.set(cv2.CAP_PROP_FRAME_HEIGHT, alto)
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


def unir_camaras(resultados):
    """Une las lecturas de varias cámaras del aula en una sola.

    Cada rostro conserva el número de cámara (0, 1, ...) para dibujar su
    recuadro en el video correcto; el resumen del grupo se calcula con los
    rostros de todas las cámaras juntas.
    """
    rostros = [
        {**rostro, "camara": numero}
        for numero, resultado in enumerate(resultados)
        for rostro in resultado["rostros"]
    ]
    return {"total_rostros": len(rostros), "rostros": rostros, **resumen_grupo(rostros)}


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


def guardar_resultado_cuadro(resultado, ruta=RUTA_POR_DEFECTO, sesion_id=None):
    """Guarda la lectura (y una detección por rostro) y devuelve cuántos rostros guardó."""
    guardar_lectura(resultado, FUENTE_CAMARA, sesion_id, ruta)
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


class MonitorCamara:
    """Lee la cámara y analiza los rostros en segundo plano.

    Un hilo lee cuadros sin parar (para mostrar el video fluido) y otro
    analiza el último cuadro cada `intervalo` segundos, o al momento si se
    pide con capturar_ahora(). La interfaz consulta instantanea() para
    dibujar, sin quedarse congelada mientras el modelo trabaja.
    """

    def __init__(self, camara, analizador, intervalo=INTERVALO_ANALISIS_S,
                 guardar=guardar_resultado_cuadro, reloj=time.monotonic):
        self.camara = camara
        self.analizador = analizador
        self.intervalo = intervalo
        self.guardar = guardar
        self.reloj = reloj
        self.error = None
        self.numero_resultado = 0
        self._cuadro = None
        self._resultado = None
        self._ultimo_analisis = None
        self._bloqueo = threading.Lock()
        self._activo = threading.Event()
        self._captura_pedida = threading.Event()
        self._hilos = []

    @property
    def activo(self):
        return self._activo.is_set()

    def iniciar(self):
        """Abre la cámara y arranca los hilos. Lanza ErrorCamara si no abre."""
        if self.activo:
            return
        self.error = None
        self._ultimo_analisis = None
        self.camara.abrir()
        self._activo.set()
        self._hilos = [
            threading.Thread(target=self._bucle_lectura, daemon=True),
            threading.Thread(target=self._bucle_analisis, daemon=True),
        ]
        for hilo in self._hilos:
            hilo.start()

    def detener(self):
        """Detiene los hilos y cierra la cámara."""
        self._activo.clear()
        for hilo in self._hilos:
            if hilo is not threading.current_thread():
                hilo.join(timeout=ESPERA_DETENER_S)
        self._hilos = []
        self._captura_pedida.clear()
        self.camara.cerrar()

    def capturar_ahora(self):
        """Pide analizar el próximo cuadro sin esperar el intervalo."""
        self._captura_pedida.set()

    def instantanea(self):
        """Devuelve (último cuadro, último resultado, número de resultado)."""
        with self._bloqueo:
            return self._cuadro, self._resultado, self.numero_resultado

    def paso_lectura(self):
        cuadro = self.camara.leer()
        with self._bloqueo:
            self._cuadro = cuadro
        return cuadro

    def paso_analisis(self, ahora=None):
        """Analiza el último cuadro si toca; devuelve el resultado o None."""
        ahora = self.reloj() if ahora is None else ahora
        pedida = self._captura_pedida.is_set()
        if not pedida and not toca_analizar(self._ultimo_analisis, ahora, self.intervalo):
            return None
        with self._bloqueo:
            cuadro = self._cuadro
        if cuadro is None:
            return None
        self._captura_pedida.clear()
        resultado = self.analizador.analizar_cuadro(cuadro)
        self.guardar(resultado)
        with self._bloqueo:
            self._resultado = resultado
            self.numero_resultado += 1
        self._ultimo_analisis = ahora
        return resultado

    def _fallar(self, error):
        self.error = str(error)
        self._activo.clear()

    def _bucle_lectura(self):
        while self.activo:
            try:
                self.paso_lectura()
            except Exception as error:  # noqa: BLE001
                self._fallar(error)

    def _bucle_analisis(self):
        while self.activo:
            try:
                self.paso_analisis()
            except Exception as error:  # noqa: BLE001
                self._fallar(error)
            time.sleep(ESPERA_ANALISIS_S)


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
