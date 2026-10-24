==================================================
PLAN: EMOTICONTIGO
==================================================

# EmotiContigo

## Equipo: Windows + R
- Ivan Ramiro Castillo Mamani  — Desarrollador Backend
- Ruth Estefani Huaman Mamani — Desarrollador Fullstack
- Eduardo Puma Ccorimanya — Desarrollador Frontend
- Rebeca Yasbet Rocca Ramos — Ingeniero ML / IA
- Junior Jeferson Sottec  Velasque — QA / Testing
- 

## Problema
Hoy en día en la sociedad muchas de las personas entre ellas niños presentan dificultades en lo que son sus aprendizajes, tienen dificultades para expresar sus emociones o encontrar orientación cuando atraviesan momentos complicados mostrando asi dificultades de aprendizaje. 

## Solucion
Desarrollaremos un sistema de inteligencia artificial que utilizara una camara para capturar imagenes de las expresiones faciales de los estudiantes durante las clases . Mediante un modelo de reconocimiento facial de expresiones , el sistema analizara las imagenes y clasificara expresiones como alegría, tristeza, sorpresa o neutralidad. Los resultados  se mostraran en un interfaz con graficos y estadisticas para apoyar la observación del docente, sin asumir que las expresiones determinen si un niño aprendio o no.

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