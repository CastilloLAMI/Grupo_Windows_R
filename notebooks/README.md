# Entrenamiento del modelo de emociones

[![Abrir en Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/CastilloLAMI/Grupo_Windows_R/blob/main/notebooks/entrenamiento_emociones.ipynb)

El notebook `entrenamiento_emociones.ipynb`:

1. Evalúa el modelo actual (`abhilash88/face-emotion-detection`, ViT-Base ya entrenado con FER2013) sobre la parte de prueba de FER2013.
2. Lo ajusta (fine-tuning) unas épocas más, con pesos por clase (para *asco*, *miedo* y *enfado*, que tienen pocas imágenes) y aumentos de datos.
3. Compara los dos modelos (exactitud, F1 macro, F1 por emoción y matrices de confusión) y guarda el modelo nuevo.

Datos: [`abhilash88/fer2013-enhanced`](https://huggingface.co/datasets/abhilash88/fer2013-enhanced) en Hugging Face (FER2013 con partes de entrenamiento, validación y prueba). No hace falta cuenta de Kaggle.

## Pasos

1. Abre el notebook en Google Colab con el botón de arriba (o en Colab: *Archivo → Abrir notebook → GitHub* y pega la URL del repositorio).
2. Activa la GPU: *Entorno de ejecución → Cambiar tipo de entorno de ejecución → T4 GPU*.
3. **Corrida de prueba:** en la celda de configuración pon `MODO_PRUEBA = True` y ejecuta todo (*Entorno de ejecución → Ejecutar todo*). Usa 300 imágenes por parte y tarda unos minutos; sirve para comprobar que nada falla.
4. **Corrida real:** pon `MODO_PRUEBA = False`, reinicia el entorno y vuelve a ejecutar todo. Con una T4 tarda aproximadamente 20–40 minutos. No cierres la pestaña mientras entrena.
5. Al final se descargan dos archivos:
   - `resultados.zip`: `metricas.json` y las matrices de confusión (`.png`).
   - `modelo_emoticontigo.zip`: el modelo ajustado (~330 MB).

## Usar el modelo nuevo en la aplicación

Solo si el modelo ajustado sale **mejor** que el actual (sobre todo en F1 macro):

1. Descomprime `modelo_emoticontigo.zip` en la carpeta `modelos/` del proyecto, para que quede `modelos/modelo_emoticontigo/config.json`.
2. Indica la ruta con la variable `EMOTI_MODELO` (ya la lee `src/model.py`):

   ```bash
   # Windows (PowerShell)
   $env:EMOTI_MODELO = "modelos/modelo_emoticontigo"
   # Linux / macOS
   export EMOTI_MODELO=modelos/modelo_emoticontigo
   ```

3. Ejecuta la app como siempre. El modelo guarda sus etiquetas como `LABEL_0` … `LABEL_6`, que `src/model.py` traduce al español.

La carpeta `modelos/` está en `.gitignore`: el modelo pesa demasiado para GitHub. Lo que sí se sube son los resultados: copia el contenido de `resultados.zip` en `docs/entrenamiento/` y haz commit.

## Qué esperar

- FER2013 tiene un techo conocido: los mejores modelos rondan el 73–76 % de exactitud, porque el dataset tiene imágenes mal etiquetadas. El modelo actual reporta 71.55 %.
- La mejora esperable está en las emociones con pocas imágenes (*asco*, *miedo*, *enfado*), que el modelo actual suele confundir con *neutral*. Por eso la métrica principal es el **F1 macro**, que pesa igual a las 7 emociones.
- FER2013 tiene sobre todo rostros de adultos; los resultados con niños pueden ser distintos.
