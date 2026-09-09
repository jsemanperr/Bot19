# -*- coding: utf-8 -*-
"""
whatsapp_bridge.py
===================
Encapsula toda la comunicacion con WhatsApp a traves de Evolution API
(https://github.com/EvolutionAPI/evolution-api).

IMPORTANTE: los endpoints exactos de Evolution API pueden variar levemente
entre versiones. Los usados aqui corresponden a la version "estable" mas
comun (v1/v2). Si tu instancia expone rutas distintas, ajusta las
constantes *_ENDPOINT de este archivo.

Todas las credenciales se leen desde variables de entorno (.env), nunca
se hardcodean.
"""

import os
import logging
import base64
import mimetypes
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("jarvis.whatsapp_bridge")

EVOLUTION_API_URL = os.getenv("EVOLUTION_API_URL", "http://localhost:8080").rstrip("/")
EVOLUTION_API_KEY = os.getenv("EVOLUTION_API_KEY", "")
EVOLUTION_INSTANCE = os.getenv("EVOLUTION_INSTANCE", "jarvis")
USER_WHATSAPP_NUMBER = os.getenv("USER_WHATSAPP_NUMBER", "")
WHATSAPP_DESTINATION_OVERRIDES = os.getenv("WHATSAPP_DESTINATION_OVERRIDES", "")

TIMEOUT_SEGUNDOS = 30  # Aumentado para operaciones lentas
MAX_REINTENTOS_WHATSAPP = 2  # Reintentar envíos si falla


def _headers() -> dict:
    return {
        "Content-Type": "application/json",
        "apikey": EVOLUTION_API_KEY,
    }


def _resolver_destino(numero: str) -> str:
    """Convierte contactos configurados a su JID privado cuando es necesario."""
    telefono = "".join(caracter for caracter in numero if caracter.isdigit())
    for entrada in WHATSAPP_DESTINATION_OVERRIDES.split(","):
        origen, separador, destino = entrada.strip().partition("=")
        if separador and "".join(caracter for caracter in origen if caracter.isdigit()) == telefono:
            return destino.strip()
    return numero


def _resolver_numero_lid(lid: str) -> str:
    """Obtiene el teléfono autorizado asociado a un identificador privado."""
    for entrada in WHATSAPP_DESTINATION_OVERRIDES.split(","):
        origen, separador, destino = entrada.strip().partition("=")
        if separador and destino.strip() == lid:
            return "".join(caracter for caracter in origen if caracter.isdigit())
    return ""


def enviar_mensaje_texto(numero: str, texto: str) -> bool:
    """
    Envia un mensaje de texto por WhatsApp a traves de Evolution API con reintentos.

    :param numero: numero destino en formato internacional sin '+' (ej: 5491122334455).
    :param texto: contenido del mensaje.
    :return: True si Evolution API respondio con exito, False en caso contrario.
    """
    import time
    numero = _resolver_destino(numero)
    url = f"{EVOLUTION_API_URL}/message/sendText/{EVOLUTION_INSTANCE}"
    payload = {
        "number": numero,
        "text": texto,
    }
    
    for intento in range(MAX_REINTENTOS_WHATSAPP):
        try:
            resp = requests.post(url, json=payload, headers=_headers(), timeout=TIMEOUT_SEGUNDOS)
            resp.raise_for_status()
            logger.info("Mensaje de texto enviado a %s", numero)
            return True
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if intento < MAX_REINTENTOS_WHATSAPP - 1:
                logger.warning("Timeout enviando mensaje a %s (intento %d), reintentando...", numero, intento + 1)
                time.sleep(2 ** intento)  # Exponential backoff
                continue
            logger.error("Error enviando mensaje de texto a %s (agotados reintentos): %s", numero, e)
            return False
        except requests.exceptions.RequestException as e:
            logger.error("Error enviando mensaje de texto a %s: %s", numero, e)
            return False
    
    return False


def enviar_audio(numero: str, ruta_audio: str) -> bool:
    """
    Envia un archivo de audio (nota de voz) por WhatsApp con reintentos.

    :param numero: numero destino.
    :param ruta_audio: ruta local al archivo de audio (mp3/ogg/wav).
    :return: True si se envio correctamente.
    """
    import time
    numero = _resolver_destino(numero)
    if not os.path.isfile(ruta_audio):
        logger.error("No se encontro el archivo de audio a enviar: %s", ruta_audio)
        return False
    
    if os.path.getsize(ruta_audio) < 1000:
        logger.error("Archivo de audio muy pequeño: %s", ruta_audio)
        return False

    url = f"{EVOLUTION_API_URL}/message/sendWhatsAppAudio/{EVOLUTION_INSTANCE}"
    
    for intento in range(MAX_REINTENTOS_WHATSAPP):
        try:
            with open(ruta_audio, "rb") as archivo:
                audio_b64 = base64.b64encode(archivo.read()).decode("ascii")

            payload = {
                "number": numero,
                "audio": audio_b64,
            }
            resp = requests.post(url, json=payload, headers=_headers(), timeout=TIMEOUT_SEGUNDOS)
            resp.raise_for_status()
            logger.info("Audio enviado a %s (%s)", numero, ruta_audio)
            return True
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if intento < MAX_REINTENTOS_WHATSAPP - 1:
                logger.warning("Timeout enviando audio a %s (intento %d), reintentando...", numero, intento + 1)
                time.sleep(2 ** intento)  # Exponential backoff
                continue
            logger.error("Error enviando audio a %s (agotados reintentos): %s", numero, e)
            return False
        except requests.exceptions.RequestException as e:
            logger.warning(
                "Evolution rechazó la nota de voz para %s; se envía como audio estándar: %s",
                numero,
                e,
            )
            return enviar_media(
                numero,
                ruta_audio,
                mediatype="audio",
                caption="Respuesta de voz",
            )
        except Exception as e:
            logger.error("Error inesperado enviando audio: %s", e)
            return False
    
    return False


def enviar_media(numero: str, ruta_media: str, mediatype: str = "image", caption: str = "") -> bool:
    """Envía una imagen, sticker o archivo local dentro del chat."""
    numero = _resolver_destino(numero)
    if not os.path.isfile(ruta_media):
        logger.error("No se encontró el archivo multimedia: %s", ruta_media)
        return False

    mimetype = mimetypes.guess_type(ruta_media)[0] or "application/octet-stream"
    with open(ruta_media, "rb") as archivo:
        contenido = base64.b64encode(archivo.read()).decode("ascii")

    payload = {
        "number": numero,
        "mediatype": mediatype,
        "mimetype": mimetype,
        "caption": caption,
        "media": contenido,
        "fileName": os.path.basename(ruta_media),
    }
    url = f"{EVOLUTION_API_URL}/message/sendMedia/{EVOLUTION_INSTANCE}"
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        logger.info("Media enviada a %s (%s)", numero, ruta_media)
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Error enviando media a %s: %s", numero, e)
        return False


def enviar_sticker(numero: str, ruta_sticker: str) -> bool:
    """Envía un sticker mediante el endpoint específico de Evolution API."""
    numero = _resolver_destino(numero)
    if not os.path.isfile(ruta_sticker):
        return False
    with open(ruta_sticker, "rb") as archivo:
        contenido = base64.b64encode(archivo.read()).decode("ascii")
    payload = {"number": numero, "sticker": contenido}
    url = f"{EVOLUTION_API_URL}/message/sendSticker/{EVOLUTION_INSTANCE}"
    try:
        resp = requests.post(url, json=payload, headers=_headers(), timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        logger.info("Sticker enviado a %s", numero)
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Error enviando sticker a %s: %s", numero, e)
        return False


def descargar_y_enviar_media(numero: str, url_media: str, mediatype: str = "image", caption: str = "") -> bool:
    """Descarga una URL y la envía como multimedia por WhatsApp."""
    try:
        resp = requests.get(url_media, timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        extension = mimetypes.guess_extension(resp.headers.get("Content-Type", "").split(";")[0]) or ".bin"
        ruta = os.path.join("data", "media_saliente", f"media_{os.urandom(8).hex()}{extension}")
        os.makedirs(os.path.dirname(ruta), exist_ok=True)
        with open(ruta, "wb") as archivo:
            archivo.write(resp.content)
        if mediatype == "sticker":
            return enviar_sticker(numero, ruta)
        return enviar_media(numero, ruta, mediatype=mediatype, caption=caption)
    except requests.exceptions.RequestException as e:
        logger.error("Error descargando media desde %s: %s", url_media, e)
        return False

def descargar_audio(url_audio: str, destino: str) -> Optional[str]:
    """
    Descarga un archivo de audio entrante (URL provista por Evolution API
    en el payload del webhook) y lo guarda localmente.

    :param url_audio: URL publica/privada del audio.
    :param destino: ruta local donde guardarlo.
    :return: la ruta 'destino' si tuvo exito, None si fallo.
    """
    try:
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        headers = {"apikey": EVOLUTION_API_KEY} if EVOLUTION_API_KEY else {}
        resp = requests.get(url_audio, headers=headers, timeout=TIMEOUT_SEGUNDOS, stream=True)
        resp.raise_for_status()
        with open(destino, "wb") as f:
            for chunk in resp.iter_content(chunk_size=8192):
                f.write(chunk)
        logger.info("Audio descargado en %s", destino)
        return destino
    except requests.exceptions.RequestException as e:
        logger.error("Error descargando audio desde %s: %s", url_audio, e)
        return None


def guardar_audio_base64(audio_base64: str, destino: str) -> Optional[str]:
    """Guarda una nota de voz incluida en Base64 por Evolution API."""
    if not audio_base64:
        return None
    try:
        contenido = audio_base64.split(",", 1)[-1]
        os.makedirs(os.path.dirname(destino), exist_ok=True)
        with open(destino, "wb") as archivo:
            archivo.write(base64.b64decode(contenido, validate=True))
        logger.info("Audio Base64 guardado en %s", destino)
        return destino
    except (ValueError, OSError) as e:
        logger.error("No se pudo guardar el audio Base64: %s", e)
        return None
    except Exception as e:
        logger.exception("Error inesperado descargando audio: %s", e)
        return None


def extraer_texto_y_remitente(payload_webhook: dict) -> Optional[dict]:
    """
    Normaliza el payload que envia Evolution API al webhook, extrayendo
    los campos que a JARVIS le interesan. Devuelve None si el payload
    no corresponde a un mensaje entrante util (ej: eventos de estado,
    mensajes propios, etc).

    Estructura esperada (aproximada, Evolution API v2):
    {
      "event": "messages.upsert",
      "data": {
          "key": {"remoteJid": "5491122334455@s.whatsapp.net", "fromMe": false},
          "message": {"conversation": "hola"},
          ...
      }
    }
    """
    try:
        if payload_webhook.get("event") not in ("messages.upsert", "message.upsert"):
            return None

        data = payload_webhook.get("data", {})
        key = data.get("key", {})

        if key.get("fromMe"):
            # Ignoramos mensajes enviados por el propio bot para evitar loops.
            return None

        remote_jid = key.get("remoteJid", "")
        numero = remote_jid.split("@")[0] if "@" in remote_jid else remote_jid
        destino = remote_jid
        if remote_jid.endswith("@g.us"):
            # En grupos, remoteJid identifica al grupo; el remitente real
            # llega normalmente en participant o participantAlt.
            participantes = (
                key.get("participant"),
                key.get("participantAlt"),
                data.get("participant"),
                data.get("participantAlt"),
                data.get("senderPn"),
            )
            participante = next(
                (str(valor) for valor in participantes if valor and not str(valor).endswith("@lid")),
                "",
            )
            if participante:
                numero = participante.split("@", 1)[0]
            else:
                logger.warning("Mensaje de grupo ignorado: Evolution no incluyó al participante.")
                return None
        elif remote_jid.endswith("@lid"):
            # Las versiones recientes de WhatsApp pueden ocultar el teléfono
            # en remoteJid y entregar el JID numérico en un campo alternativo.
            # Nunca se debe reasignar un @lid al dueño: mezclaría usuarios.
            candidatos = (
                key.get("remoteJidAlt"),
                key.get("participant"),
                key.get("participantAlt"),
                data.get("remoteJidAlt"),
                data.get("senderPn"),
                data.get("participant"),
            )
            jid_numerico = next(
                (str(candidato) for candidato in candidatos if candidato and not str(candidato).endswith("@lid")),
                "",
            )
            if jid_numerico:
                numero = jid_numerico.split("@", 1)[0]
            else:
                numero = _resolver_numero_lid(remote_jid)
                if not numero:
                    logger.warning("Mensaje @lid ignorado: Evolution no incluyó el número del remitente.")
                    return None

        mensaje = data.get("message", {})
        texto = mensaje.get("conversation") or mensaje.get("extendedTextMessage", {}).get("text")

        audio_msg = mensaje.get("audioMessage") or mensaje.get("audio_message")
        url_audio = None
        audio_base64 = None
        if audio_msg:
            # Evolution suele exponer una URL descargable en 'url' o mediaUrl segun version.
            url_audio = audio_msg.get("url") or data.get("mediaUrl")
            audio_base64 = audio_msg.get("base64") or audio_msg.get("data") or data.get("base64")

        if not texto and not url_audio:
            return None

        return {
            "numero": numero,
            "destino": destino,
            "texto": texto,
            "url_audio": url_audio,
            "audio_base64": audio_base64,
            "mensaje_id": key.get("id", ""),
        }
    except Exception as e:
        logger.exception("Error interpretando payload del webhook: %s", e)
        return None
