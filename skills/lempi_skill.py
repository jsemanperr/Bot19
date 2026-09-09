# -*- coding: utf-8 -*-
"""Comandos de WhatsApp para el cliente de Lempi API."""

import json
import re

import lempi_api
import whatsapp_bridge


AYUDA = (
    "Comandos Lempi: imagen <tema>, sticker <tema>, pinterest <tema>, "
    "spotify busca <tema>, brat <texto>, emojimix <emoji1> <emoji2>, "
    "genera imagen <prompt>, youtub audio <url>, youtube video <url>, "
    "descarga tiktok <url>, descarga instagram <url>."
)


def _texto_resultado(resultado) -> str:
    if isinstance(resultado, (dict, list)):
        return json.dumps(resultado, ensure_ascii=False)[:3500]
    return str(resultado)


def _url(texto: str) -> str:
    encontrado = re.search(r"https?://\S+", texto)
    return encontrado.group(0).rstrip(".,)") if encontrado else ""


def _primer_url(resultado, claves: tuple[str, ...] = ("thumbnail", "image", "media", "download", "url")) -> str | None:
    """Encuentra la primera URL de archivo dentro de una respuesta Lempi."""
    if isinstance(resultado, dict):
        for clave in claves:
            valor = resultado.get(clave)
            if isinstance(valor, str) and valor.startswith("http"):
                return valor
        for valor in resultado.values():
            url = _primer_url(valor, claves)
            if url:
                return url
    elif isinstance(resultado, list):
        for valor in resultado:
            url = _primer_url(valor, claves)
            if url:
                return url
    return None


def usar_lempi(comando: str, remitente: str = "") -> str:
    """Ejecuta una acción de Lempi a partir de una frase en lenguaje natural."""
    texto = (comando or "").strip()
    bajo = texto.lower()
    try:
        if bajo.startswith(("imagen ", "busca imagen ", "buscar imagen ")):
            consulta = re.sub(r"^(busca|buscar)?\s*imagen\s+", "", texto, flags=re.I)
            resultado = lempi_api.buscar_imagen(consulta)
            imagen = _primer_url(resultado)
            if imagen and whatsapp_bridge.descargar_y_enviar_media(remitente, imagen, caption=f"Imagen: {consulta}"):
                return f"Te envié una imagen de {consulta}."
            return "No pude descargar la imagen solicitada."
        if bajo.startswith(("sticker ", "stickers ")):
            consulta = re.sub(r"^stickers?\s+", "", texto, flags=re.I)
            resultado = lempi_api.stickers(consulta)
            url_sticker = _primer_url(resultado, ("stickers", "image", "media", "url"))
            if url_sticker and whatsapp_bridge.descargar_y_enviar_media(remitente, url_sticker, mediatype="sticker"):
                return f"Te envié un sticker de {consulta}."
            return "No pude descargar el sticker solicitado."
        if bajo.startswith("pinterest "):
            return _texto_resultado(lempi_api.pinterest(q=texto[10:].strip()))
        if bajo.startswith(("spotify busca ", "busca spotify ")):
            consulta = re.sub(r"^(spotify busca|busca spotify)\s+", "", texto, flags=re.I)
            return _texto_resultado(lempi_api.spotify_buscar(q=consulta))
        if bajo.startswith("brat "):
            return _texto_resultado(lempi_api.brat(texto[5:].strip()))
        if bajo.startswith(("genera imagen ", "generar imagen ")):
            consulta = re.sub(r"^genera?r?\s+imagen\s+", "", texto, flags=re.I)
            if not consulta:
                return "Decime que imagen queres generar, por ejemplo: genera imagen un atardecer en Oaxaca."
            resultado = lempi_api.generar_imagen(prompt=consulta, size="1024x1024")
            imagen = _primer_url(resultado, ("image", "url", "media", "download"))
            if imagen and whatsapp_bridge.descargar_y_enviar_media(remitente, imagen, caption=f"Imagen IA: {consulta}"):
                return "Listo, te envié la imagen generada."
            return "La imagen se generó, pero no pude descargarla para enviártela."
        if bajo.startswith("emojimix "):
            partes = texto.split(maxsplit=2)
            if len(partes) < 3:
                return "Uso: emojimix 😄 😎"
            return _texto_resultado(lempi_api.emojimix(emoji1=partes[1], emoji2=partes[2]))
        if bajo.startswith(("youtube audio ", "youtube música ", "youtube musica ")):
            url = _url(texto)
            return _texto_resultado(lempi_api.descargar_youtube_audio(url=url)) if url else "Necesito la URL de YouTube."
        if bajo.startswith("youtube video "):
            url = _url(texto)
            return _texto_resultado(lempi_api.descargar_youtube_video(url=url)) if url else "Necesito la URL de YouTube."
        if bajo.startswith("descarga tiktok "):
            url = _url(texto)
            return _texto_resultado(lempi_api.descargar_tiktok(url=url)) if url else "Necesito la URL de TikTok."
        if bajo.startswith("descarga instagram "):
            url = _url(texto)
            return _texto_resultado(lempi_api.descargar_instagram(url=url)) if url else "Necesito la URL de Instagram."
        return AYUDA
    except Exception as error:
        return f"No pude usar Lempi: {error}"
