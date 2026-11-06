"""Constantes compartidas de EmotiContigo."""


TAMANO_MAXIMO_MB = 5
TAMANO_MAXIMO_BYTES = TAMANO_MAXIMO_MB * 1024 * 1024
EXTENSIONES_PERMITIDAS = ("jpg", "jpeg", "png")


LIMITE_HISTORIAL_MIN = 1
LIMITE_HISTORIAL_MAX = 100
LIMITE_HISTORIAL_DEFECTO = 50


NOMBRE_BD_DEFECTO = "emoticontigo.db"
VARIABLE_ENTORNO_BD = "EMOTI_BD"
VARIABLE_ENTORNO_MODELO = "EMOTI_MODELO"


TITULO_APP = "EmotiContigo"
CANTIDAD_EMOCIONES = 7
ETIQUETAS_FER2013 = {
    0: "enfadado",
    1: "asco",
    2: "miedo",
    3: "felicidad",
    4: "tristeza",
    5: "sorpresa",
    6: "neutral",
}
