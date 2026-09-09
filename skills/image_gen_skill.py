# -*- coding: utf-8 -*-
"""Generacion con Pollinations y edicion de imagenes mediante Agnes AI."""

import base64
import mimetypes
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import quote

import requests
from dotenv import load_dotenv

import whatsapp_bridge
import telegram_bridge

load_dotenv()
TIMEOUT_SEGUNDOS = int(os.getenv("IMAGE_AI_TIMEOUT", "90"))
POLLINATIONS_URL = os.getenv("POLLINATIONS_IMAGE_URL", "https://image.pollinations.ai/prompt").rstrip("/")
POLLINATIONS_API_KEY = os.getenv("POLLINATIONS_API_KEY", "").strip()


def _guardar_temporal(contenido: bytes, sufijo: str) -> str:
    archivo = tempfile.NamedTemporaryFile(prefix="kaori_imagen_", suffix=sufijo, delete=False)
    try:
        archivo.write(contenido)
        return archivo.name
    finally:
        archivo.close()


def _descargar_archivo(origen: str) -> str:
    """Descarga una URL o valida una ruta local para procesarla."""
    if re.match(r"^https?://", origen, re.I):
        respuesta = requests.get(origen, timeout=TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
        tipo = respuesta.headers.get("Content-Type", "").split(";", 1)[0]
        return _guardar_temporal(respuesta.content, mimetypes.guess_extension(tipo) or ".png")
    ruta = Path(origen).expanduser().resolve()
    if not ruta.is_file():
        raise FileNotFoundError("No encontré el archivo de imagen indicado.")
    return str(ruta)


def generar_imagen(prompt: str) -> str:
    """Genera una imagen con Pollinations y devuelve su ruta temporal local."""
    if not (prompt := (prompt or "").strip()):
        raise ValueError("Necesito una descripción para generar la imagen.")
    url = f"{POLLINATIONS_URL}/{quote(prompt, safe='')}?width=1024&height=1024&nologo=true"
    headers = {"Authorization": f"Bearer {POLLINATIONS_API_KEY}"} if POLLINATIONS_API_KEY else {}
    respuesta = requests.get(url, headers=headers, timeout=TIMEOUT_SEGUNDOS)
    respuesta.raise_for_status()
    tipo = respuesta.headers.get("Content-Type", "").split(";", 1)[0]
    if not tipo.startswith("image/"):
        raise RuntimeError("Pollinations no devolvió una imagen válida.")
    return _guardar_temporal(respuesta.content, mimetypes.guess_extension(tipo) or ".png")


def editar_imagen_agnes(image_bytes: bytes, prompt: str) -> bytes:
    """Envía una imagen a Agnes AI y devuelve el contenido de la imagen editada.

    AGNES_API_URL debe apuntar al endpoint de edición que acepte los campos
    multipart `image` y `prompt`. Si Agnes usa otro contrato, se adapta aquí.
    """
    url = os.getenv("AGNES_API_URL", "").strip()
    clave = os.getenv("AGNES_API_KEY", "").strip()
    if not url or not clave:
        raise RuntimeError("Configurá AGNES_API_URL y AGNES_API_KEY en .env para editar imágenes.")
    respuesta = requests.post(
        url,
        headers={"Authorization": f"Bearer {clave}"},
        data={"prompt": prompt},
        files={"image": ("imagen.png", image_bytes, "image/png")},
        timeout=TIMEOUT_SEGUNDOS,
    )
    respuesta.raise_for_status()
    if respuesta.headers.get("Content-Type", "").startswith("image/"):
        return respuesta.content
    try:
        datos = respuesta.json()
        url_resultado = datos.get("url") or datos.get("image_url") or datos.get("output_url")
    except ValueError:
        url_resultado = None
    if not url_resultado:
        raise RuntimeError("Agnes no devolvió una imagen editada en un formato reconocido.")
    descarga = requests.get(url_resultado, timeout=TIMEOUT_SEGUNDOS)
    descarga.raise_for_status()
    return descarga.content


def _enviar_o_devolver(ruta: str, remitente: str, caption: str) -> str:
    if remitente:
        try:
            enviado = (
                telegram_bridge.enviar_media(ruta, "photo", caption, remitente.removeprefix("telegram:"))
                if remitente.startswith("telegram:")
                else whatsapp_bridge.enviar_media(remitente, ruta, mediatype="image", caption=caption)
            )
            if not remitente.startswith("telegram:") and os.getenv("TELEGRAM_CHAT_ID", "").strip():
                enviado = telegram_bridge.enviar_media(ruta, "photo", caption) or enviado
            return "Listo, te envié la imagen." if enviado else "La imagen se creó, pero no pude enviarla."
        finally:
            Path(ruta).unlink(missing_ok=True)
    datos_b64 = base64.b64encode(Path(ruta).read_bytes()).decode("ascii")
    return f"Imagen generada: {ruta}\nBase64: {datos_b64}"


def skill_generar_imagen(comando: str, remitente: str = "") -> str:
    prompt = re.sub(r"^\s*(?:genera(?:r)?|crea(?:r)?|haz)\s+(?:una\s+)?imagen(?:\s+ia)?\s*", "", comando or "", flags=re.I)
    try:
        return _enviar_o_devolver(generar_imagen(prompt), remitente, f"Imagen IA: {prompt}")
    except (requests.RequestException, ValueError, RuntimeError) as error:
        return f"No pude generar la imagen: {error}"


def skill_editar_imagen(comando: str, remitente: str = "") -> str:
    coincidencia = re.match(r"^\s*edita(?:r)?\s+imagen\s+(\S+)\s+(.+)$", comando or "", re.I)
    if not coincidencia:
        return "Uso: edita imagen <ruta-o-url> <instrucción de edición>."
    origen, prompt = coincidencia.groups()
    ruta_entrada = ""
    try:
        ruta_entrada = _descargar_archivo(origen)
        salida = _guardar_temporal(editar_imagen_agnes(Path(ruta_entrada).read_bytes(), prompt), ".png")
        return _enviar_o_devolver(salida, remitente, f"Imagen editada: {prompt}")
    except (OSError, requests.RequestException, RuntimeError) as error:
        return f"No pude editar la imagen: {error}"
    finally:
        if ruta_entrada.startswith(tempfile.gettempdir()):
            Path(ruta_entrada).unlink(missing_ok=True)