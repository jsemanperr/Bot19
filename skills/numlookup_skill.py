# -*- coding: utf-8 -*-
"""Validación de teléfonos con NumLookupAPI."""

import logging
import os
import re

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.numlookup")
URL = "https://api.numlookupapi.com/v1/validate/"
PATRON = re.compile(r"\+?\d[\d\s().-]{5,}\d")


def validar_numlookup(numero: str) -> str:
    clave = os.getenv("NUMLOOKUP_API_KEY", "")
    faltante = clave_requerida("NUMLOOKUP_API_KEY", clave)
    if faltante:
        return faltante
    numero = re.sub(r"[^\d+]", "", numero or "")
    if not numero:
        return "📞 Indícame un número con código de país."
    datos, error = solicitar("GET", f"{URL}{numero}", params={"apikey": clave}, logger=logger)
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ NumLookup devolvió un formato inesperado."
    return (
        f"📞 Número: {valor(datos, 'international_format', 'number', defecto=numero)}\n"
        f"🌍 País: {valor(datos, 'country_name', 'country')}\n"
        f"📡 Operador: {valor(datos, 'carrier', 'operator')}\n"
        f"☎️ Tipo de línea: {valor(datos, 'line_type', 'type')}\n"
        f"✅ Válido: {valor(datos, 'valid', defecto='N/D')}"
    )


def skill_validar_telefono_numlookup(comando: str, remitente: str = "") -> str:
    coincidencia = PATRON.search(comando or "")
    return validar_numlookup(coincidencia.group(0) if coincidencia else "")
