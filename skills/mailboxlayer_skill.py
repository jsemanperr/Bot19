# -*- coding: utf-8 -*-
"""Validacion de correos mediante mailboxlayer."""

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SEGUNDOS = 8
PATRON_CORREO = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


def validar_email(email: str) -> str:
    """Valida formato, DNS y nivel de confianza de un correo."""
    clave = os.getenv("MAILBOXLAYER_API_KEY", "").strip()
    email = (email or "").strip().lower()
    if not PATRON_CORREO.fullmatch(email):
        return "⚠️ Indicame una direccion de correo valida."
    if not clave:
        return "⚠️ Falta configurar MAILBOXLAYER_API_KEY en .env."
    try:
        respuesta = requests.get(
            "http://apilayer.net/api/check",
            params={"access_key": clave, "email": email, "smtp": 1, "format": 1}, timeout=TIMEOUT_SEGUNDOS,
        )
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        return "⚠️ No pude contactar mailboxlayer en este momento."
    if respuesta.status_code == 429:
        return "⚠️ mailboxlayer alcanzo el limite de solicitudes. Intenta mas tarde."
    if not respuesta.ok or datos.get("success") is False:
        return "⚠️ mailboxlayer rechazo la consulta. Revisa MAILBOXLAYER_API_KEY."
    puntuacion = datos.get("score")
    return (
        f"📧 Correo: {email}\n"
        f"✅ Valido: {'si' if datos.get('format_valid') and datos.get('smtp_check') else 'no'}\n"
        f"🗑️ Desechable: {'si' if datos.get('disposable') else 'no'}\n"
        f"📬 MX disponible: {'si' if datos.get('mx_found') else 'no'}\n"
        f"🧾 Formato correcto: {'si' if datos.get('format_valid') else 'no'}\n"
        f"🎯 Confianza: {puntuacion if puntuacion is not None else 'N/D'}"
    )


def skill_validar_email(comando: str, remitente: str = "") -> str:
    """Extrae y valida el primer correo presente en el comando."""
    coincidencia = PATRON_CORREO.search(comando or "")
    return validar_email(coincidencia.group(0) if coincidencia else "")