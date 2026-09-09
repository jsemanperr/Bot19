# -*- coding: utf-8 -*-
"""Phone Intelligence de AbstractAPI."""

import logging
import os
import re

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.abstract_phone")
URL = "https://phoneintelligence.abstractapi.com/v1/"
PATRON = re.compile(r"\+?\d[\d\s().-]{5,}\d")


def abstract_phone(numero: str) -> str:
    clave = os.getenv("ABSTRACT_PHONE_API_KEY", "")
    faltante = clave_requerida("ABSTRACT_PHONE_API_KEY", clave)
    if faltante:
        return faltante
    numero = re.sub(r"[^\d+]", "", numero or "")
    if not numero:
        return "📞 Indícame un número con código de país."
    datos, error = solicitar("GET", URL, params={"api_key": clave, "phone": numero}, logger=logger)
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ AbstractAPI devolvió un formato inesperado."
    return (
        f"📞 Número: {valor(datos, 'phone', defecto=numero)}\n"
        f"🌍 País: {valor(datos, 'country.name', 'country')}\n"
        f"📡 Operador: {valor(datos, 'carrier')}\n"
        f"☎️ Tipo de línea: {valor(datos, 'line_type', 'type')}\n"
        f"✅ Válido: {valor(datos, 'valid')}"
    )


def skill_abstract_phone(comando: str, remitente: str = "") -> str:
    coincidencia = PATRON.search(comando or "")
    return abstract_phone(coincidencia.group(0) if coincidencia else "")
