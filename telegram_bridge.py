"""Envio de texto y multimedia por Telegram usando Bot API."""

import logging
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("jarvis.telegram_bridge")


def _configuracion() -> tuple[str, str]:
    return os.getenv("TELEGRAM_BOT_TOKEN", "").strip(), os.getenv("TELEGRAM_CHAT_ID", "").strip()


def enviar_texto(texto: str, chat_id: str = "") -> bool:
    token, configurado = _configuracion()
    destino = chat_id or configurado
    if not token or not destino:
        return False
    try:
        respuesta = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": destino, "text": texto},
            timeout=20,
        )
        respuesta.raise_for_status()
        return True
    except requests.RequestException as error:
        logger.warning("Telegram no pudo recibir el texto: %s", error)
        return False


def enviar_media(origen: str, tipo: str = "photo", caption: str = "", chat_id: str = "") -> bool:
    """Envía una URL o archivo local como foto, video, audio o documento."""
    token, configurado = _configuracion()
    destino = chat_id or configurado
    if not token or not destino:
        return False
    metodo = {"image": "sendPhoto", "photo": "sendPhoto", "video": "sendVideo", "audio": "sendAudio"}.get(tipo, "sendDocument")
    campo = {"sendPhoto": "photo", "sendVideo": "video", "sendAudio": "audio"}.get(metodo, "document")
    url = f"https://api.telegram.org/bot{token}/{metodo}"
    try:
        if origen.startswith(("http://", "https://")):
            respuesta = requests.post(url, data={"chat_id": destino, campo: origen, "caption": caption}, timeout=30)
        else:
            ruta = Path(origen)
            with ruta.open("rb") as archivo:
                respuesta = requests.post(
                    url,
                    data={"chat_id": destino, "caption": caption},
                    files={campo: (ruta.name, archivo)},
                    timeout=60,
                )
        respuesta.raise_for_status()
        return True
    except (OSError, requests.RequestException) as error:
        logger.warning("Telegram no pudo recibir el archivo: %s", error)
        return False
