# -*- coding: utf-8 -*-
"""Cliente para los endpoints de api.lempi.lat."""

import os
from typing import Any

import requests
from dotenv import load_dotenv

load_dotenv()

BASE_URL = os.getenv("LEMPI_API_URL", "https://api.lempi.lat").rstrip("/")
API_KEY = os.getenv("LEMPI_API_KEY", "")
TIMEOUT_SECONDS = int(os.getenv("LEMPI_API_TIMEOUT", "30"))


def llamar(endpoint: str, params: dict[str, Any] | None = None) -> Any:
    """Realiza una petición GET y devuelve la respuesta JSON."""
    consulta = dict(params or {})
    consulta.setdefault("apikey", API_KEY)
    respuesta = requests.get(
        f"{BASE_URL}/{endpoint.lstrip('/')}",
        params=consulta,
        headers={"Content-Type": "application/json"},
        timeout=TIMEOUT_SECONDS,
    )
    respuesta.raise_for_status()
    return respuesta.json()


def buscar_imagen(consulta: str = "") -> Any:
    return llamar("/s/aisearchimg", {"query": consulta})


def pinterest(limit: int = 20, **params: Any) -> Any:
    return llamar("/s/pin", {"limit": limit, **params})


def spotify_buscar(limit: int = 10, **params: Any) -> Any:
    return llamar("/s/sp", {"limit": limit, **params})


def stickers(consulta: str, **params: Any) -> Any:
    return llamar("/s/stickers", {"q": consulta, **params})


def tiktok_buscar(**params: Any) -> Any:
    return llamar("/s/tiktok", params)


def canvas_welcome(**params: Any) -> Any:
    return llamar("/api/canvas/welcomev1", params)


def canvas_goodbye(**params: Any) -> Any:
    return llamar("/api/canvas/goodbyev1", params)


def descargar_apple_music(**params: Any) -> Any:
    return llamar("/dl/applemusic", params)


def descargar_facebook(quality: str = "hd", **params: Any) -> Any:
    return llamar("/dl/facebook", {"quality": quality, **params})


def descargar_instagram(**params: Any) -> Any:
    return llamar("/dl/instagram", params)


def descargar_mediafire(**params: Any) -> Any:
    return llamar("/dl/mediafire", params)


def descargar_spotify(**params: Any) -> Any:
    return llamar("/dl/spotify", params)


def descargar_tiktok(**params: Any) -> Any:
    return llamar("/dl/tiktok", params)


def descargar_youtube_audio(**params: Any) -> Any:
    return llamar("/dl/yta", params)


def descargar_youtube_video(**params: Any) -> Any:
    return llamar("/dl/ytv", params)


def brat(texto: str, color: str = "verde", formato: str = "image") -> Any:
    return llamar("/tools/brat", {"text": texto, "color": color, "format": formato})


def cloudflare(**params: Any) -> Any:
    return llamar("/tools/cf", params)


def emojimix(**params: Any) -> Any:
    return llamar("/tools/emojimix", params)


def identificar_musica(**params: Any) -> Any:
    return llamar("/tools/whatmusic", params)


def transcribir(**params: Any) -> Any:
    return llamar("/tools/transcribe", params)


def claude(**params: Any) -> Any:
    return llamar("/ai/claude", params)


def gemini(**params: Any) -> Any:
    return llamar("/ai/gemini", params)


def qwen(**params: Any) -> Any:
    return llamar("/ai/qwen", params)


def generar_imagen(**params: Any) -> Any:
    return llamar("/ai/zimg", params)
