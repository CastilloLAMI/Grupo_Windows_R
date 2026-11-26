# ============================================================
# EmotiContigo - Imagen Docker de la API con el modelo de IA
#
# Construir:  docker build -t emoticontigo .
# Ejecutar:   docker run -p 5000:5000 -v emoti-datos:/datos emoticontigo
# Abrir:      http://localhost:5000
#
# El contenedor sirve la API Flask y una página web de demostración.
# La app de escritorio (Tkinter + cámara) se ejecuta en la PC: ver README.
# ============================================================
FROM python:3.11-slim

# 1 = descarga el modelo de Hugging Face al construir la imagen, para que el
#     contenedor funcione sin internet. 0 = imagen más liviana; el modelo se
#     descarga la primera vez que se usa (o se monta en /app/modelos).
ARG DESCARGAR_MODELO=1

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface \
    EMOTI_BD=/datos/emoticontigo.db \
    EMOTI_PRECARGAR=1 \
    GUNICORN_CMD_ARGS="--bind 0.0.0.0:5000 --workers 1 --threads 4 --timeout 120"

WORKDIR /app

# Dependencias primero: Docker reutiliza esta capa mientras no cambien.
# PyTorch solo para CPU (sin CUDA): la imagen pesa unos 2 GB menos.
COPY requirements-docker.txt .
RUN pip install --index-url https://download.pytorch.org/whl/cpu "torch>=2.2,<3" \
    && pip install -r requirements-docker.txt

# Usuario sin privilegios de administrador
RUN useradd --create-home --uid 1000 emoti \
    && mkdir -p /datos /app/modelos "$HF_HOME" \
    && chown -R emoti:emoti /datos /app

USER 1000

RUN if [ "$DESCARGAR_MODELO" = "1" ]; then \
        python -c "from transformers import pipeline; pipeline('image-classification', model='abhilash88/face-emotion-detection')"; \
    fi

# Con el modelo dentro de la imagen, no se consulta internet al ejecutar
ENV HF_HUB_OFFLINE=${DESCARGAR_MODELO}

COPY --chown=emoti:emoti src/ src/
COPY --chown=emoti:emoti db/ db/

VOLUME ["/datos"]
EXPOSE 5000

HEALTHCHECK --interval=30s --timeout=5s --start-period=90s --retries=3 \
    CMD ["python", "-c", "import urllib.request; urllib.request.urlopen('http://localhost:5000/salud', timeout=4)"]

# Un proceso con varios hilos (GUNICORN_CMD_ARGS): el modelo se carga una sola vez en memoria
CMD ["gunicorn", "src.app:crear_app()"]
