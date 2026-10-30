"""API Flask de EmotiContigo."""
from flask import Flask, jsonify, request
from PIL import Image

from src.model import DetectorEmociones
from src.preprocess import validar_extension


def crear_app(detector=None):
    app = Flask(__name__)
    detector = detector or DetectorEmociones()

    @app.get("/salud")
    def salud():
        return jsonify({"estado": "ok"})

    @app.post("/predecir")
    def predecir():
        if "imagen" not in request.files:
            return jsonify({"error": "Falta el archivo 'imagen'"}), 400
        archivo = request.files["imagen"]
        if archivo.filename == "":
            return jsonify({"error": "No se seleccionó ningún archivo"}), 400
        try:
            validar_extension(archivo.filename)
        except ValueError as e:
            return jsonify({"error": str(e)}), 400
        imagen = Image.open(archivo.stream).convert("RGB")
        return jsonify(detector.predecir(imagen))

    return app


if __name__ == "__main__":
    crear_app().run(debug=True)
