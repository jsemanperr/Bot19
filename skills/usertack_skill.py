# -*- coding: utf-8 -*-
"""Analisis de un User-Agent mediante la API Userstack."""

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SEGUNDOS = 8


def track_usuario(user_agent: str = "") -> str:
    """Identifica dispositivo y navegador de un User-Agent proporcionado por el usuario."""
    clave = os.getenv("USERSTACK_API_KEY", os.getenv("USERTACK_API_KEY", "")).strip()
    user_agent = (user_agent or "").strip()
    if not clave:
        return "⚠️ Falta configurar USERSTACK_API_KEY en .env."
    if not user_agent:
        return "⚠️ Para analizar un dispositivo, envia el User-Agent despues de 'userstack'."
    try:
        respuesta = requests.get(
            "https://api.userstack.com/api/detect",
            params={"access_key": clave, "ua": user_agent}, timeout=TIMEOUT_SEGUNDOS,
        )
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        return "⚠️ No pude contactar Userstack en este momento."
    if respuesta.status_code == 429:
        return "⚠️ Userstack alcanzo el limite de solicitudes. Intenta mas tarde."
    if not respuesta.ok or datos.get("success") is False:
        return "⚠️ Userstack rechazo la consulta. Revisa USERSTACK_API_KEY."
    dispositivo = datos.get("device") or {}
    navegador = datos.get("browser") or {}
    sistema = datos.get("os") or {}
    return (
        "🖥️ Analisis de User-Agent\n"
        f"📱 Dispositivo: {dispositivo.get('brand') or ''} {dispositivo.get('name') or 'N/D'}\n"
        f"🌐 Navegador: {navegador.get('name') or 'N/D'} {navegador.get('version') or ''}\n"
        f"⚙️ Sistema operativo: {sistema.get('name') or 'N/D'} {sistema.get('version') or ''}\n"
        f"🗣️ Idioma: {datos.get('language') or 'no informado'}\n"
        "📍 Ubicacion: Userstack analiza el agente; la ubicacion requiere una consulta GeoIP separada."
    )


def skill_track_usuario(comando: str, remitente: str = "") -> str:
    """Toma el User-Agent que siga a la palabra userstack o usertack."""
    coincidencia = re.search(r"(?:userstack|usertack)\s*[:=-]?\s*(.+)$", comando or "", re.I)
    return track_usuario(coincidencia.group(1) if coincidencia else "")