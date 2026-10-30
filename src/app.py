"""API Flask de EmotiContigo."""
from flask import Flask, jsonify, request
from PIL import Image

from src.model import DetectorEmociones
from src.preprocess import validar_extension

CAMPO_IMAGEN = "imagen"
HTTP_SOLICITUD_INVALIDA = 400


def validar_archivo(archivos):
    """Devuelve el archivo subido o lanza ValueError con el motivo."""
    if CAMPO_IMAGEN not in archivos:
        raise ValueError(f"Falta el archivo '{CAMPO_IMAGEN}'")
    archivo = archivos[CAMPO_IMAGEN]
    if archivo.filename == "":
        raise ValueError("No se seleccionó ningún archivo")
    validar_extension(archivo.filename)
    return archivo


def crear_app(detector=None):
    app = Flask(__name__)
    detector = detector or DetectorEmociones()

    @app.get("/salud")
    def salud():
        return jsonify({"estado": "ok"})

    @app.post("/predecir")
    def predecir():
        try:
            archivo = validar_archivo(request.files)
        except ValueError as e:
            return jsonify({"error": str(e)}), HTTP_SOLICITUD_INVALIDA
        imagen = Image.open(archivo.stream).convert("RGB")
        return jsonify(detector.predecir(imagen))

    return app


if __name__ == "__main__":
    crear_app().run(debug=True)
