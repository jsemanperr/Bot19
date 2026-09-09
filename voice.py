# -*- coding: utf-8 -*-
"""Síntesis de voz local para Kaori."""

import os
import tempfile
import uuid
import logging
import re

import requests
import pyttsx3
from dotenv import load_dotenv


load_dotenv()
logger = logging.getLogger("jarvis.voice")


def _preparar_texto_para_voz(texto: str) -> str:
    """Convierte una respuesta escrita en un guion breve y natural para TTS."""
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
    api_key = os.getenv("FISH_AUDIO_API_KEY", "")
    voice_id = os.getenv("FISH_AUDIO_VOICE_ID", "")
    if not api_key or not voice_id:
        return None

    url = "https://api.fish.audio/v1/tts"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "model": os.getenv("FISH_AUDIO_MODEL", "s2.1-pro"),
    }
    payload = {
        "text": texto,
        "reference_id": voice_id,
        "format": os.getenv("FISH_AUDIO_FORMAT", "mp3"),
        "latency": os.getenv("FISH_AUDIO_LATENCY", "low"),
    }
    respuesta = requests.post(url, headers=headers, json=payload, timeout=10)
    respuesta.raise_for_status()
    extension = payload["format"]
    ruta = os.path.join(tempfile.gettempdir(), f"kaori_{uuid.uuid4().hex}.{extension}")
    with open(ruta, "wb") as archivo:
        archivo.write(respuesta.content)
    if os.path.getsize(ruta) < 1024:
        os.remove(ruta)
        raise requests.RequestException("Fish Audio devolvio un archivo vacio")
    return ruta


def sintetizar_texto(texto: str) -> str | None:
    """Genera audio con Fish Audio y usa la voz local como respaldo."""
    texto = _preparar_texto_para_voz(texto)
    if not texto:
        return None

    load_dotenv(override=True)
    try:
        audio_fish = _sintetizar_fish_audio(texto)
        if audio_fish:
            return audio_fish
    except requests.RequestException as error:
        logger.warning("Fish Audio no disponible; se usa voz local: %s", error)

    voice_name = os.getenv("VOICE_NAME", "Zira")
    voice_rate = int(os.getenv("VOICE_RATE", "175"))
    ruta = os.path.join(tempfile.gettempdir(), f"kaori_{uuid.uuid4().hex}.wav")
    motor = pyttsx3.init()
    motor.setProperty("rate", voice_rate)

    if voice_name:
        voces = motor.getProperty("voices")
        voz = next((v for v in voces if voice_name.lower() in v.name.lower()), None)
        if voz is None and voice_name.lower() != "zira":
            voz = next((v for v in voces if "zira" in v.name.lower()), None)
        if voz:
            motor.setProperty("voice", voz.id)

    motor.save_to_file(texto, ruta)
    motor.runAndWait()
    motor.stop()
    return ruta if os.path.isfile(ruta) else None
