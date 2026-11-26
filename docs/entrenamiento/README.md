# Resultados del ajuste fino del modelo

Notebook: `notebooks/entrenamiento_emociones.ipynb` (Google Colab, GPU T4, transformers 4).

- **Modelo base:** `abhilash88/face-emotion-detection` (ViT-Base ya entrenado con FER2013).
- **Datos:** FER2013 con su partición original (columna `usage`): 28 709 imágenes de entrenamiento (`Training`), 3 589 de validación (`PublicTest`) y 3 589 de prueba (`PrivateTest`).
- **Ajuste:** 3 épocas, tasa de aprendizaje 2e-5, lote 64, pesos por clase (asco 2.44; el resto entre 0.60 y 0.90) y aumentos de datos (encuadre, giro, brillo y contraste). Se conserva la época con mejor F1 macro en validación.

## Resultados en la parte de prueba (PrivateTest, 3 589 imágenes)

| Métrica | Modelo actual | Modelo ajustado | Diferencia |
|---|---|---|---|
| Exactitud | 71.7 % | 73.0 % | +1.3 |
| F1 macro | 0.700 | 0.718 | +0.018 |

| Emoción | Imágenes | F1 actual | F1 ajustado | Diferencia |
|---|---|---|---|---|
| Enfado | 491 | 0.629 | 0.654 | +0.025 |
| Asco | 55 | 0.685 | 0.739 | +0.054 |
| Miedo | 528 | 0.573 | 0.584 | +0.011 |
| Felicidad | 879 | 0.913 | 0.916 | +0.003 |
| Tristeza | 594 | 0.587 | 0.594 | +0.007 |
| Sorpresa | 416 | 0.810 | 0.820 | +0.010 |
| Neutral | 626 | 0.704 | 0.719 | +0.015 |

Matrices de confusión normalizadas por fila: `matriz_modelo_actual.png` y `matriz_modelo_ajustado.png`. Detalle completo (precisión, recall y F1 por emoción): `metricas.json`.

## Conclusiones

- La exactitud del modelo actual (71.7 %) coincide con la reportada por su autor (71.55 %), lo que indica que la partición de prueba no contiene imágenes de su entrenamiento.
- El modelo ajustado mejora en las 7 emociones; la mayor mejora es en **asco** (+0.054), la clase con menos imágenes, gracias a los pesos por clase.
- Confusiones que se mantienen: tristeza con neutral (0.19), asco con enfado (0.16), miedo con tristeza (0.15) y con enfado (0.12). Son expresiones parecidas entre sí y también difíciles para las personas.
- FER2013 tiene sobre todo rostros de adultos: los resultados con estudiantes pueden ser distintos. Por eso el sistema presenta las emociones como apoyo a la observación del docente y no como una medida del aprendizaje.

El modelo ajustado (~330 MB) no se sube a GitHub. Para usarlo, descomprime `modelo_emoticontigo.zip` en `modelos/` y define `EMOTI_MODELO=modelos/modelo_emoticontigo` (ver `notebooks/README.md`).
