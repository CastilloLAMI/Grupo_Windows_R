"""API Flask de EmotiContigo."""
import os

from flask import Flask, jsonify, request
from PIL import Image, UnidentifiedImageError

from src.constantes import (
    LIMITE_HISTORIAL_DEFECTO, LIMITE_HISTORIAL_MAX, LIMITE_HISTORIAL_MIN,
    TAMANO_MAXIMO_BYTES, TAMANO_MAXIMO_MB,
)
from src.historial import (
    RUTA_POR_DEFECTO,
    guardar_analisis, inicializar_bd, listar_historial, listar_sesiones, obtener_estadisticas,
    obtener_sesion, sesion_activa,
)
from src.model import DetectorEmociones
from src.preprocess import validar_extension
from src import alcance

CAMPO_IMAGEN = "imagen"
HTTP_SOLICITUD_INVALIDA = 400
HTTP_NO_ENCONTRADO = 404
HTTP_ENTIDAD_DEMASIADO_GRANDE = 413
MENSAJE_IMAGEN_INVALIDA = "El archivo no es una imagen válida"


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


def crear_app(detector=None, ruta_bd=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = TAMANO_MAXIMO_BYTES
    app.config["RUTA_BD"] = ruta_bd or os.getenv("EMOTI_BD") or RUTA_POR_DEFECTO

    violaciones = alcance.validar_rutas(app)
    if violaciones:
        raise RuntimeError("El sistema viola su alcance:\n" + "\n".join(violaciones))

    inicializar_bd(app.config["RUTA_BD"])
    detector = detector or DetectorEmociones()

    @app.errorhandler(HTTP_ENTIDAD_DEMASIADO_GRANDE)
    def archivo_demasiado_grande(_error):
        mensaje = f"La imagen supera el límite de {TAMANO_MAXIMO_MB} MB"
        return jsonify({"error": mensaje}), HTTP_ENTIDAD_DEMASIADO_GRANDE

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
