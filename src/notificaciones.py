import json
import os
import threading
import urllib.parse
import urllib.request

EMOCIONES_ALERTA = {"tristeza", "miedo", "enfadado"}
UMBRAL_CONFIANZA = 70.0


def debe_notificar(emocion, confianza):
    return emocion in EMOCIONES_ALERTA and confianza >= UMBRAL_CONFIANZA


def enviar_telegram(mensaje, token=None, chat_id=None):
    token = token or os.environ.get("EMOTI_TELEGRAM_TOKEN")
    chat_id = chat_id or os.environ.get("EMOTI_TELEGRAM_CHAT")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    datos = urllib.parse.urlencode(
        {"chat_id": chat_id, "text": mensaje}
    ).encode()
    try:
        with urllib.request.urlopen(url, datos, timeout=10) as r:
            return json.load(r).get("ok", False)
    except OSError:
        return False


def notificar_deteccion(emocion, confianza, curso=""):
    if not debe_notificar(emocion, confianza):
        return False
    texto = (
        f"EmotiContigo: se detectó {emocion} ({confianza:.0f}%) {curso}. "
        "Es solo una observación de apoyo para el docente."
    )
    hilo = threading.Thread(target=enviar_telegram, args=(texto,), daemon=True)
    hilo.start()
    return True


def notificar_rostros(rostros):
    """Envía un solo aviso por lectura (el rostro de mayor confianza)."""
    alertas = [
        r for r in rostros
        if debe_notificar(r["emocion"], r["confianza"])
    ]
    if not alertas:
        return False
    mayor = max(alertas, key=lambda r: r["confianza"])
    return notificar_deteccion(
        mayor["emocion"], mayor["confianza"], f"en {len(alertas)} rostro(s)"
    )
