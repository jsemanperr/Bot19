# -*- coding: utf-8 -*-
"""Generacion asincrona de video IA mediante la cola de fal.ai."""

import logging
import os
import re
import threading
import time
from typing import Any

import requests
from dotenv import load_dotenv

import whatsapp_bridge
import telegram_bridge

load_dotenv()
logger = logging.getLogger("jarvis.skills.video_ai")

TIMEOUT_SEGUNDOS = 20
INTERVALO_CONSULTA_SEGUNDOS = 5
TIEMPO_MAXIMO_SEGUNDOS = 180


def _primer_valor(datos: Any, claves: tuple[str, ...]) -> str | None:
    """Busca una URL de video en respuestas anidadas de distintos proveedores."""
    if isinstance(datos, dict):
        for clave in claves:
            valor = datos.get(clave)
            if isinstance(valor, str) and valor.startswith("http"):
                return valor
        for valor in datos.values():
            encontrado = _primer_valor(valor, claves)
            if encontrado:
                return encontrado
    elif isinstance(datos, list):
        for valor in datos:
            encontrado = _primer_valor(valor, claves)
            if encontrado:
                return encontrado
    return None


def _headers() -> dict[str, str]:
    """Arma la autenticacion requerida por la API de fal.ai."""
    clave = os.getenv("VIDEO_AI_API_KEY", "").strip()
    return {"Authorization": f"Key {clave}", "Content-Type": "application/json"}


def _esperar_video(url_estado: str, url_respuesta: str) -> str | None:
    """Consulta la cola de fal.ai y recupera el resultado al completarse."""
    limite = time.monotonic() + TIEMPO_MAXIMO_SEGUNDOS
    while time.monotonic() < limite:
        try:
            respuesta = requests.get(url_estado, headers=_headers(), timeout=TIMEOUT_SEGUNDOS)
            respuesta.raise_for_status()
            datos = respuesta.json()
        except (requests.RequestException, ValueError):
            return None
        estado = str(datos.get("status") or "").upper()
        if estado == "COMPLETED":
            try:
                respuesta = requests.get(url_respuesta, headers=_headers(), timeout=TIMEOUT_SEGUNDOS)
                respuesta.raise_for_status()
                return _primer_valor(respuesta.json(), ("video_url", "video", "output", "url"))
            except (requests.RequestException, ValueError):
                return None
        if estado in {"FAILED", "ERROR", "CANCELED", "CANCELLED"}:
            return None
        time.sleep(INTERVALO_CONSULTA_SEGUNDOS)
    return None


def _generar_y_enviar(prompt: str, remitente: str) -> None:
    """Ejecuta el trabajo fuera del flujo del chat y envia el MP4 al finalizar."""
    modelo = os.getenv("VIDEO_AI_MODEL", "fal-ai/wan/v2.2-a14b/text-to-video").strip()
    url_api = f"https://queue.fal.run/{modelo}"
    try:
        respuesta = requests.post(url_api, headers=_headers(), json={"prompt": prompt}, timeout=TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
        datos = respuesta.json()
        url_estado = datos.get("status_url")
        url_respuesta = datos.get("response_url")
        video = _esperar_video(url_estado, url_respuesta) if url_estado and url_respuesta else None
        if video and remitente.startswith("telegram:"):
            enviado = telegram_bridge.enviar_media(
                video, "video", f"Video IA: {prompt}", remitente.removeprefix("telegram:")
            )
        elif video:
            enviado = whatsapp_bridge.descargar_y_enviar_media(
                remitente, video, mediatype="video", caption=f"Video IA: {prompt}"
            )
            if os.getenv("TELEGRAM_CHAT_ID", "").strip():
                enviado = telegram_bridge.enviar_media(video, "video", f"Video IA: {prompt}") or enviado
        else:
            enviado = False
        if enviado:
            return
        if remitente.startswith("telegram:"):
            telegram_bridge.enviar_texto(
                "No pude completar el video IA. Revisá el estado o formato de respuesta del proveedor.",
                remitente.removeprefix("telegram:"),
            )
        else:
            whatsapp_bridge.enviar_mensaje_texto(remitente, "No pude completar el video IA. Revisá el estado o formato de respuesta del proveedor.")
            telegram_bridge.enviar_texto("No pude completar el video IA. Revisá el estado o formato de respuesta del proveedor.")
    except requests.HTTPError as error:
        codigo = error.response.status_code if error.response is not None else 0
        logger.warning("Error HTTP generando video IA: %s", error)
        if codigo in {401, 403}:
            mensaje = "fal.ai rechazó la clave o el acceso al modelo. Revisá VIDEO_AI_API_KEY, permisos y saldo de la cuenta."
        elif codigo == 429:
            mensaje = "fal.ai alcanzó el límite de solicitudes. Esperá unos minutos e intentá de nuevo."
        else:
            mensaje = "El proveedor de video IA no pudo procesar el pedido. Intentá de nuevo más tarde."
        whatsapp_bridge.enviar_mensaje_texto(remitente, mensaje)
    except requests.RequestException as error:
        logger.warning("Error generando video IA: %s", error)
        whatsapp_bridge.enviar_mensaje_texto(remitente, "El proveedor de video IA no respondió. Intentá de nuevo más tarde.")


def generar_video(prompt: str, remitente: str = "") -> str:
    """Inicia una generacion de video con una API compatible y responde de inmediato."""
    prompt = (prompt or "").strip()
    if not prompt:
        return "Decime que video queres generar, por ejemplo: genera video un colibrí volando entre flores."
    if not os.getenv("VIDEO_AI_API_KEY", "").strip():
        return "Para generar videos IA configurá VIDEO_AI_API_KEY en .env con tu clave de fal.ai."
    if not remitente:
        return "La generacion de video requiere un chat de destino para poder enviarte el MP4."
    threading.Thread(target=_generar_y_enviar, args=(prompt, remitente), daemon=True, name="kaori-video-ai").start()
    return "Estoy generando tu video IA. Puede tardar unos minutos; te lo envío apenas esté listo."


def skill_generar_video(comando: str, remitente: str = "") -> str:
    """Extrae el prompt de una orden de generacion de video."""
    prompt = re.sub(r"^\s*(?:genera(?:r)?|crea(?:r)?|haz)\s+(?:un\s+)?video(?:\s+ia)?\s*", "", comando or "", flags=re.I)
    return generar_video(prompt, remitente)