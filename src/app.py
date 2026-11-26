"""API Flask de EmotiContigo."""
import os
from pathlib import Path

import numpy as np
from flask import Flask, jsonify, request, send_from_directory
from PIL import Image, UnidentifiedImageError

from src.constantes import (
    LIMITE_HISTORIAL_DEFECTO, LIMITE_HISTORIAL_MAX, LIMITE_HISTORIAL_MIN,
    TAMANO_MAXIMO_BYTES, TAMANO_MAXIMO_MB,
)
from src.camara import AnalizadorAula, DetectorRostros, guardar_resultado_cuadro
from src.historial import (
    RUTA_POR_DEFECTO,
    cerrar_sesion, guardar_analisis, iniciar_sesion, inicializar_bd, listar_historial, listar_sesiones,
    obtener_estadisticas, obtener_sesion, sesion_activa,
)
from src.model import DetectorEmociones
from src.preprocess import validar_extension
from src import alcance

CAMPO_IMAGEN = "imagen"
HTTP_SOLICITUD_INVALIDA = 400
HTTP_CREADO = 201
HTTP_NO_ENCONTRADO = 404
HTTP_CONFLICTO = 409
HTTP_ENTIDAD_DEMASIADO_GRANDE = 413
MENSAJE_IMAGEN_INVALIDA = "El archivo no es una imagen válida"
CARPETA_WEB = Path(__file__).resolve().parent / "web"
PAGINA_INICIO = "index.html"
VARIABLE_PRECARGA = "EMOTI_PRECARGAR"


def validar_archivo(archivos):
    """Devuelve el archivo subido o lanza ValueError con el motivo."""
    if CAMPO_IMAGEN not in archivos:
        raise ValueError(f"Falta el archivo '{CAMPO_IMAGEN}'")
    archivo = archivos[CAMPO_IMAGEN]
    if archivo.filename == "":
        raise ValueError("No se seleccionó ningún archivo")
    validar_extension(archivo.filename)
    return archivo


def abrir_imagen(archivo):
    """Decodifica la imagen subida o lanza ValueError si está corrupta."""
    try:
        imagen = Image.open(archivo.stream)
        imagen.load()
        return imagen.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError) as error:
        raise ValueError(MENSAJE_IMAGEN_INVALIDA) from error


def leer_sesion_id(argumentos, ruta_bd):
    """Lee `sesion_id` de la consulta: None si no viene; ValueError o LookupError si no sirve."""
    texto = argumentos.get("sesion_id")
    if texto is None:
        return None
    try:
        sesion_id = int(texto)
    except ValueError as error:
        raise ValueError("sesion_id debe ser un número entero") from error
    if obtener_sesion(sesion_id, ruta_bd) is None:
        raise LookupError(f"No existe la sesión {sesion_id}")
    return sesion_id


def a_bgr(imagen):
    """Convierte una imagen RGB de Pillow al formato BGR que usa OpenCV."""
    return np.ascontiguousarray(np.asarray(imagen)[:, :, ::-1])


def leer_datos_sesion(cuerpo):
    """Extrae curso, grado y sección, y docente de un JSON; ValueError si no es un objeto."""
    if not isinstance(cuerpo, dict):
        raise ValueError("Envía los datos de la sesión en formato JSON")
    return cuerpo.get("curso"), cuerpo.get("grado_seccion"), cuerpo.get("docente")


def crear_app(detector=None, ruta_bd=None, detector_rostros=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = TAMANO_MAXIMO_BYTES
    app.config["RUTA_BD"] = ruta_bd or os.getenv("EMOTI_BD") or RUTA_POR_DEFECTO

    violaciones = alcance.validar_rutas(app)
    if violaciones:
        raise RuntimeError("El sistema viola su alcance:\n" + "\n".join(violaciones))

    inicializar_bd(app.config["RUTA_BD"])
    detector = detector or DetectorEmociones()
    analizador = {}

    def analizador_aula():
        """El clasificador de rostros de OpenCV se carga la primera vez que se usa."""
        if "aula" not in analizador:
            analizador["aula"] = AnalizadorAula(detector, detector_rostros or DetectorRostros())
        return analizador["aula"]
    if os.getenv(VARIABLE_PRECARGA) == "1" and hasattr(detector, "cargar"):
        # En Docker el modelo se carga al arrancar: la primera foto no espera
        detector.cargar()

    @app.errorhandler(HTTP_ENTIDAD_DEMASIADO_GRANDE)
    def archivo_demasiado_grande(_error):
        mensaje = f"La imagen supera el límite de {TAMANO_MAXIMO_MB} MB"
        return jsonify({"error": mensaje}), HTTP_ENTIDAD_DEMASIADO_GRANDE

    @app.get("/")
    def inicio():
        """Página web de demostración (la usa el contenedor Docker)."""
        return send_from_directory(CARPETA_WEB, PAGINA_INICIO)

    @app.get("/salud")
    def salud():
        return jsonify({"estado": "ok"})

    @app.post("/predecir")
    def predecir():
        try:
            archivo = validar_archivo(request.files)
            imagen = abrir_imagen(archivo)
        except ValueError as error:
            return jsonify({"error": str(error)}), HTTP_SOLICITUD_INVALIDA
        resultado = detector.predecir(imagen)

        violaciones_resp = alcance.validar_respuesta(str(resultado))
        if violaciones_resp:
            return jsonify({"error": "Respuesta fuera de alcance", "detalle": violaciones_resp}), 500

        activa = sesion_activa(app.config["RUTA_BD"])
        guardar_analisis(resultado, app.config["RUTA_BD"], sesion_id=activa["id"] if activa else None)
        return jsonify(resultado)

    def sesion_de_la_consulta():
        """Devuelve (sesion_id, None) o (None, respuesta de error)."""
        try:
            return leer_sesion_id(request.args, app.config["RUTA_BD"]), None
        except ValueError as error:
            return None, (jsonify({"error": str(error)}), HTTP_SOLICITUD_INVALIDA)
        except LookupError as error:
            return None, (jsonify({"error": str(error)}), HTTP_NO_ENCONTRADO)

    @app.get("/estadisticas")
    def estadisticas():
        sesion_id, error = sesion_de_la_consulta()
        if error:
            return error
        return jsonify(obtener_estadisticas(app.config["RUTA_BD"], sesion_id=sesion_id))

    @app.get("/sesiones")
    def sesiones():
        return jsonify(listar_sesiones(app.config["RUTA_BD"]))

    @app.post("/sesiones")
    def abrir_sesion():
        """Abre una sesión de clase (cierra la que estuviera abierta)."""
        try:
            curso, grado, docente = leer_datos_sesion(request.get_json(silent=True))
            sesion_id = iniciar_sesion(curso, grado, docente, app.config["RUTA_BD"])
        except ValueError as error:
            return jsonify({"error": str(error)}), HTTP_SOLICITUD_INVALIDA
        return jsonify(obtener_sesion(sesion_id, app.config["RUTA_BD"])), HTTP_CREADO

    @app.post("/sesiones/<int:sesion_id>/cerrar")
    def terminar_sesion(sesion_id):
        ruta = app.config["RUTA_BD"]
        if obtener_sesion(sesion_id, ruta) is None:
            return jsonify({"error": f"No existe la sesión {sesion_id}"}), HTTP_NO_ENCONTRADO
        if not cerrar_sesion(sesion_id, ruta):
            return jsonify({"error": f"La sesión {sesion_id} ya estaba cerrada"}), HTTP_CONFLICTO
        return jsonify(obtener_sesion(sesion_id, ruta))

    @app.post("/analizar-cuadro")
    def analizar_cuadro():
        """Analiza un cuadro de la cámara del navegador: todos sus rostros y el resumen del grupo."""
        activa = sesion_activa(app.config["RUTA_BD"])
        if activa is None:
            mensaje = "Inicia una sesión de clase para usar la cámara"
            return jsonify({"error": mensaje}), HTTP_CONFLICTO
        try:
            imagen = abrir_imagen(validar_archivo(request.files))
        except ValueError as error:
            return jsonify({"error": str(error)}), HTTP_SOLICITUD_INVALIDA
        resultado = analizador_aula().analizar_cuadro(a_bgr(imagen))

        violaciones_resp = alcance.validar_respuesta(str(resultado))
        if violaciones_resp:
            return jsonify({"error": "Respuesta fuera de alcance", "detalle": violaciones_resp}), 500

        guardar_resultado_cuadro(resultado, app.config["RUTA_BD"], sesion_id=activa["id"])
        return jsonify({
            **resultado,
            "rostros": [{**rostro, "caja": list(rostro["caja"])} for rostro in resultado["rostros"]],
            "ancho": imagen.width,
            "alto": imagen.height,
            "sesion_id": activa["id"],
        })

    @app.get("/historial")
    def historial():
        texto = request.args.get("limite")
        limite = LIMITE_HISTORIAL_DEFECTO
        if texto is not None:
            try:
                limite = int(texto)
            except ValueError:
                mensaje = "El límite debe ser un número entero"
                return jsonify({"error": mensaje}), HTTP_SOLICITUD_INVALIDA
        if limite < LIMITE_HISTORIAL_MIN or limite > LIMITE_HISTORIAL_MAX:
            mensaje = (
                f"El límite debe estar entre {LIMITE_HISTORIAL_MIN} y {LIMITE_HISTORIAL_MAX}"
            )
            return jsonify({"error": mensaje}), HTTP_SOLICITUD_INVALIDA
        sesion_id, error = sesion_de_la_consulta()
        if error:
            return error
        return jsonify(listar_historial(app.config["RUTA_BD"], limite, sesion_id=sesion_id))

    return app


if __name__ == "__main__":
    crear_app().run(debug=True)
