"""
alcance.py — Definición ejecutable del alcance del proyecto EmotiContigo.

Este módulo codifica las restricciones éticas y funcionales del sistema
para que puedan ser verificadas por pruebas automatizadas y respetadas
por la API. La prosa del README debe reflejar lo que aquí se declara.
"""

# ============================================================
# 1. PROPÓSITO Y ALCANCE FUNCIONAL
# ============================================================

PROPOSITO = (
    "Apoyar la observación del docente mediante la detección de "
    "emociones faciales, sin asumir que las expresiones determinen "
    "si un niño aprendió o no."
)

# Emociones que el sistema PUEDE clasificar (7 clases del modelo)
EMOCIONES_PERMITIDAS = (
    "enfadado",
    "asco",
    "miedo",
    "felicidad",
    "tristeza",
    "sorpresa",
    "neutral",
)

# Endpoints que el sistema EXPONE (alcance funcional)
ENDPOINTS_PERMITIDOS = (
    "/salud",
    "/predecir",
    "/estadisticas",
    "/historial",
)

# ============================================================
# 2. RESTRICCIONES DEL ALCANCE (lo que el sistema NO hace)
# ============================================================

# Rutas prohibidas: el sistema no evalúa, califica ni mide rendimiento
RUTAS_PROHIBIDAS = (
    "/calificar",
    "/evaluar",
    "/nota",
    "/notas",
    "/rendimiento",
    "/diagnostico",
    "/diagnosticar",
    "/recomendar",
    "/intervenir",
)

# Palabras prohibidas en respuestas: el sistema no infiere aprendizaje
PALABRAS_PROHIBIDAS_EN_RESPUESTA = (
    "aprendio",
    "aprendió",
    "no aprendio",
    "aprobo",
    "aprobó",
    "desaprobo",
    "desaprobó",
    "rendimiento",
    "calificacion",
    "calificación",
    "nota final",
    "diagnostico",
    "diagnóstico",
    "trastorno",
)

# Campos que el historial NO debe guardar (privacidad)
CAMPOS_PROHIBIDOS_EN_HISTORIAL = (
    "imagen",
    "foto",
    "rostro",
    "cara",
    "pixel",
    "pixeles",
)

# ============================================================
# 3. VALIDADORES EJECUTABLES
# ============================================================

def validar_rutas(app) -> list[str]:
    """
    Verifica que la app Flask no exponga rutas prohibidas.
    Devuelve la lista de violaciones encontradas (vacía = OK).
    """
    violaciones = []
    for regla in app.url_map.iter_rules():
        ruta = str(regla)
        for prohibida in RUTAS_PROHIBIDAS:
            if prohibida in ruta.lower():
                violaciones.append(
                    f"Ruta prohibida por alcance: {ruta} contiene '{prohibida}'"
                )
    return violaciones


def validar_respuesta(texto: str) -> list[str]:
    """
    Verifica que una respuesta del sistema no infiera aprendizaje
    ni emita diagnósticos. Devuelve violaciones encontradas.
    """
    violaciones = []
    texto_lower = str(texto).lower()
    for palabra in PALABRAS_PROHIBIDAS_EN_RESPUESTA:
        if palabra in texto_lower:
            violaciones.append(
                f"Palabra prohibida por alcance: '{palabra}' en respuesta."
            )
    return violaciones


def validar_historial(registro: dict) -> list[str]:
    """
    Verifica que un registro de historial no guarde imágenes ni datos
    del rostro. Solo se permite emoción y confianza.
    """
    violaciones = []
    for campo in registro.keys():
        if campo.lower() in CAMPOS_PROHIBIDOS_EN_HISTORIAL:
            violaciones.append(
                f"Campo prohibido por privacidad: '{campo}' en historial."
            )
    return violaciones


def validar_emocion(emocion: str) -> bool:
    """Verifica que la emoción esté dentro de las 7 clases permitidas."""
    return emocion.lower() in EMOCIONES_PERMITIDAS


def validar_endpoint(ruta: str) -> bool:
    """Verifica que el endpoint pertenezca al alcance funcional."""
    return any(ruta.startswith(e) for e in ENDPOINTS_PERMITIDOS)


# ============================================================
# 4. METADATOS DEL ALCANCE (para documentación y exposición)
# ============================================================

ALCANCE = {
    "hace": [
        "Captura expresiones faciales durante la clase.",
        "Clasifica 7 emociones con porcentaje de confianza.",
        "Muestra gráficos y estadísticas al docente.",
        "Guarda historial (emoción + confianza) en SQLite.",
        "Actúa como intermediario entre estudiante y docente.",
    ],
    "no_hace": [
        "No se involucra en el desarrollo del estudiante.",
        "No forma parte del proceso ni del rendimiento académico.",
        "No determina si un niño aprendió o no.",
        "No sustituye el criterio del docente.",
        "No almacena imágenes de los rostros.",
        "No emite diagnósticos clínicos ni psicológicos.",
    ],
    "criterios_calidad": {
        "cobertura_minima": 60,
        "python_versions": ["3.10", "3.11"],
        "lint": "flake8 (max-line-length=120)",
        "ci": "GitHub Actions en push a main/develop y PR a main",
    },
}