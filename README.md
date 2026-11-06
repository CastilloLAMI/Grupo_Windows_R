==================================================
PLAN: EMOTICONTIGO
==================================================

# EmotiContigo

## Equipo: Windows + R
- Ivan Ramiro Castillo Mamani  — Desarrollador Backend
- Ruth Estefani Huaman Mamani — Desarrollador Fullstack
- Eduardo Puma Ccorimanya — Desarrollador Frontend
- Rebeca Yasbet Rocca Ramos — Ingeniero ML / IA
- Avance: Implementación del modelo Face-Emotion-Detection para clasificación de expresiones.
- Junior Jeferson Sottec Velasque — QA / Testing
- Ayde Mirian Condori Valencia — QA / Testing

## Problema
Hoy en día en la sociedad muchas de las personas entre ellas niños presentan dificultades en lo que son sus aprendizajes, tienen dificultades para expresar sus emociones o encontrar orientación cuando atraviesan momentos complicados mostrando asi dificultades de aprendizaje. 

## Solucion
Desarrollaremos un sistema de inteligencia artificial que utilizara una camara para capturar imagenes de las expresiones faciales de los estudiantes durante las clases . Mediante un modelo de reconocimiento facial de expresiones , el sistema analizara las imagenes y clasificara expresiones como alegría, tristeza, sorpresa o neutralidad. Los resultados se mostraran en un interfaz con graficos y estadisticas para apoyar la observación del docente, sin asumir que las expresiones determinen si un niño aprendio o no.

## Alcance del Proyecto

EmotiContigo es una herramienta de **apoyo a la observación docente**. Su alcance está delimitado de forma explícita para garantizar un uso ético y responsable de la inteligencia artificial en el aula.

### Lo que el sistema SÍ hace

- Captura imágenes de expresiones faciales de los estudiantes durante la clase.
- Clasifica las expresiones en 7 emociones (enfadado, asco, miedo, felicidad, tristeza, sorpresa, neutral) con su porcentaje de confianza.
- Muestra gráficos y estadísticas al docente para apoyar su observación del aula.
- Guarda un historial de análisis (emoción y confianza) en SQLite para consulta posterior.
- Actúa como **intermediario** entre el estudiante y el docente, facilitando la identificación de estados emocionales.

### Lo que el sistema NO hace (restricciones del alcance)

- **No se involucra en el desarrollo del estudiante.** No interviene en su proceso formativo ni emite juicios sobre su evolución personal.
- **No es parte del proceso ni del rendimiento académico.** No evalúa, califica ni condiciona la nota del estudiante.
- **No determina si un niño aprendió o no.** Las expresiones faciales no se interpretan como indicadores de aprendizaje.
- **No sustituye el criterio del docente.** El sistema solo presenta información; la interpretación y la acción pedagógica son responsabilidad del docente.
- **No almacena imágenes de los rostros.** El historial guarda únicamente la emoción detectada y el nivel de confianza, no la fotografía.

### Criterios de calidad del alcance

El alcance incluye criterios no funcionales verificables mediante pruebas automatizadas:

- **Cobertura de pruebas mínima:** 60% (`fail_under = 60` en `.coveragerc`).
- **Integración continua:** GitHub Actions ejecuta las pruebas en cada push a `main` y `develop`, y en pull requests a `main`.
- **Compatibilidad:** Python 3.10 y 3.11.
- **Calidad de código:** lint con `flake8` (max-line-length = 120).
- **Enfoque TDD:** el alcance ético se traduce en pruebas unitarias que protegen las restricciones anteriores.

### Trazabilidad del alcance

| Restricción del alcance | Prueba que la protege |
|---|---|
| No se involucra en el desarrollo del estudiante | `test_la_pagina_web_no_se_involucrara_en_el_desarrollo_del_estudiante` |
| Solo es un intermediario entre estudiante y docente | `test_solo_ser_un_intermediario_entre_el_estudiante_y_el_docente` |
| No es parte del proceso ni rendimiento académico | `test_la_pagina_web_no_ser_parte_del_proceso_o_rendimiento_academico_del_estudiante` |
| El sistema produce un resultado válido | `test_resultado_esperado` |

> **Nota:** estas pruebas se encuentran en `tests/` y se ejecutan con `python -m unittest discover -s tests -v`.

## Modelo de IA
- **Categoria:** image-classification
- **Modelo:** [Face-emotion-detection](https://huggingface.co/abhilash88/face-emotion-detection)
- **Input:** foto del rostro del niño de jpg o png
- **Output:** emocion detectado de las 7 clases con porcentaje
- **Justificacion:** Elegimos este modelo porque porque ya viene entrenado para reconocer rostros lo cual nos va ayudar a capturar las emociones de la población que elegimos en este caso los niños y tambien podemos reentrenarlo.

## Dataset
- **Nombre:** FER2013
- **Registros:** 35877
- **Columnas:** Imgen (pixels): Matriz de 48 *48 pixeles en escala de grises que capturan el rostro del alumno. Etiqueta(label): Valor entero del 0 al 6 que clasifica el estado emocional facial 0:enfadado 1: asco 2: miedo 3:Felicidad 4: tristeza 5: sorpresa 6 : Neutral

## Stack
- **Lenguaje:** python
- **Framework:** flask
- **ML:** Hugging Face Transformers
- **Testing:** unittest + TDD
- **CI/CD:** GitHub Actions

## Instalacion
```bash
git clone https://github.com/CastilloLAMI/Grupo_Windows_R.git
cd emoticontigo
python -m venv venv
venv\\Scripts\\activate
pip install -r requirements.txt
```

## Tests
```bash
python -m unittest discover -s tests -v
```

## API
- `GET /salud` → estado del servicio.
- `POST /predecir` → recibe una imagen en el campo `imagen` (jpg/png, máximo 5 MB).
- `GET /estadisticas` → total de análisis, conteo por emoción y confianza promedio.
- `GET /historial?limite=50` → últimos análisis (límite entre 1 y 100).

El historial se guarda en SQLite (`emoticontigo.db`). La ruta se puede cambiar con la variable `EMOTI_BD`.

## Interfaz de escritorio
```bash
python -m src.interfaz
```
La interfaz reutiliza `DetectorEmociones`. Si tienes una copia local del modelo, define `EMOTI_MODELO` con la ruta de la carpeta que contiene `config.json` y `model.safetensors`.

---
*Proyecto Final — Construccion de Software — Universidad Continental*

--- ESTRUCTURA ---
Selecciona componentes arriba.

--- CI/CD ---
name: CI - EmotiContigo

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ["3.10", "3.11"]

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install -r requirements.txt

    - name: Run tests
      run: |
        python -m unittest discover -s tests -v

    - name: Lint
      run: |
        pip install flake8
        flake8 src/ --max-line-length=120

--- REQUIREMENTS ---
transformers>=4.35.0
torch>=2.0.0
datasets>=2.14.0
scikit-learn>=1.3.0
numpy>=1.24.0
flask>=3.0.0
Pillow>=10.0.0
matplotlib>=3.7.0
coverage>=7.0.0
flake8>=7.0.0
