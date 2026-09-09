# -*- coding: utf-8 -*-
"""Síntesis de voz Fish Audio con respaldo local."""

import logging
import os
import re
import tempfile
import uuid

import pyttsx3
import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("jarvis.voice")


def _preparar_texto_para_voz(texto: str) -> str:
    limite = max(80, int(os.getenv("VOICE_MAX_CHARS", "500")))
    texto = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", texto)
    texto = re.sub(r"https?://\S+", "", texto)
    texto = re.sub(r"[*_`#>|]", "", texto)
    texto = re.sub(r"\s+", " ", texto).strip()
    if len(texto) <= limite:
        return texto
    corte = texto.rfind(". ", 0, limite)
    corte = corte if corte >= limite // 2 else limite
    return texto[:corte].rstrip(" ,;:") + "."


def _sintetizar_fish_audio(texto: str) -> str | None:
    api_key = os.getenv("FISH_AUDIO_API_KEY", "").strip()
    voice_id = os.getenv("FISH_AUDIO_VOICE_ID", "").strip()
    if not api_key or not voice_id:
        logger.warning("Faltan FISH_AUDIO_API_KEY o FISH_AUDIO_VOICE_ID.")
        return None

    formato = os.getenv("FISH_AUDIO_FORMAT", "mp3").lower()
    respuesta = requests.post(
        "https://api.fish.audio/v1/tts",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "model": os.getenv("FISH_AUDIO_MODEL", "s2.1-pro"),
        },
        json={
            "text": texto,
            "reference_id": voice_id,
            "format": formato,
            "latency": os.getenv("FISH_AUDIO_LATENCY", "low"),
        },
        timeout=20,
    )
    respuesta.raise_for_status()
    ruta = os.path.join(tempfile.gettempdir(), f"kaori_{uuid.uuid4().hex}.{formato}")
    with open(ruta, "wb") as archivo:
        archivo.write(respuesta.content)
    if os.path.getsize(ruta) < 1024:
        os.remove(ruta)
        raise requests.RequestException("Fish Audio devolvio un archivo vacio")
    return ruta


def sintetizar_texto(texto: str) -> str | None:
    """Genera audio remoto y usa pyttsx3 solo como respaldo local."""
    texto = _preparar_texto_para_voz(texto)
    if not texto:
        return None

    load_dotenv(override=True)
    try:
        audio_fish = _sintetizar_fish_audio(texto)
        if audio_fish:
            return audio_fish
    except requests.RequestException as error:
        logger.warning("Fish Audio no disponible; se intenta voz local: %s", error)

    try:
        motor = pyttsx3.init()
        motor.setProperty("rate", int(os.getenv("VOICE_RATE", "175")))
        voz_nombre = os.getenv("VOICE_NAME", "Zira").lower()
        voz = next((v for v in motor.getProperty("voices") if voz_nombre in v.name.lower()), None)
        if voz:
            motor.setProperty("voice", voz.id)
        ruta = os.path.join(tempfile.gettempdir(), f"kaori_{uuid.uuid4().hex}.wav")
        motor.save_to_file(texto, ruta)
        motor.runAndWait()
        motor.stop()
        return ruta if os.path.isfile(ruta) else None
    except (OSError, RuntimeError) as error:
        logger.error("No hay sintetizador local disponible: %s", error)
        return None
