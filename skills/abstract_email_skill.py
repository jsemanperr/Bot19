# -*- coding: utf-8 -*-
"""Reputación de correos con AbstractAPI."""

import logging
import os
import re

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.abstract_email")
URL = "https://emailreputation.abstractapi.com/v1/"
PATRON = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)


def abstract_email(email: str) -> str:
    clave = os.getenv("ABSTRACT_EMAIL_API_KEY", "")
    faltante = clave_requerida("ABSTRACT_EMAIL_API_KEY", clave)
    if faltante:
        return faltante
    email = email.strip().lower()
    if not PATRON.fullmatch(email):
        return "📧 Indícame un correo electrónico válido."
    datos, error = solicitar("GET", URL, params={"api_key": clave, "email": email}, logger=logger)
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ AbstractAPI devolvió un formato inesperado."
    return (
        f"📧 Correo: {email}\n"
        f"⭐ Reputación: {valor(datos, 'reputation', 'score')}\n"
        f"✅ Válido: {valor(datos, 'is_valid', 'valid')}\n"
        f"🗑️ Desechable: {valor(datos, 'is_disposable', 'disposable')}\n"
        f"📬 Dominio: {valor(datos, 'domain')}"
    )


def skill_abstract_email(comando: str, remitente: str = "") -> str:
    coincidencia = PATRON.search(comando or "")
    return abstract_email(coincidencia.group(0) if coincidencia else "")
