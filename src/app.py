"""API Flask de EmotiContigo."""
from flask import Flask, jsonify, request
from PIL import Image, UnidentifiedImageError

from src.model import DetectorEmociones
from src.preprocess import validar_extension

CAMPO_IMAGEN = "imagen"
HTTP_SOLICITUD_INVALIDA = 400
HTTP_ENTIDAD_DEMASIADO_GRANDE = 413
TAMANO_MAXIMO_MB = 5
BYTES_POR_MB = 1024 * 1024
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


def crear_app(detector=None):
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = TAMANO_MAXIMO_MB * BYTES_POR_MB
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
        return jsonify(detector.predecir(imagen))

    return app


if __name__ == "__main__":
    crear_app().run(debug=True)
