# -*- coding: utf-8 -*-
"""Validación alternativa de teléfonos con Veriphone."""

import logging
import os
import re

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.veriphone")
URL = "https://api.veriphone.io/v2/verify"
PATRON = re.compile(r"\+?\d[\d\s().-]{5,}\d")


def verificar_veriphone(numero: str) -> str:
    clave = os.getenv("VERIPHONE_API_KEY", "")
    faltante = clave_requerida("VERIPHONE_API_KEY", clave)
    if faltante:
        return faltante
    numero = re.sub(r"[^\d+]", "", numero or "")
    if not numero:
        return "📞 Indícame un número con código de país."
    datos, error = solicitar("GET", URL, params={"phone": numero, "key": clave}, logger=logger)
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ Veriphone devolvió un formato inesperado."
    return (
        f"📞 Número: {valor(datos, 'phone', defecto=numero)}\n"
        f"🌍 País: {valor(datos, 'country')}\n"
        f"📡 Operador: {valor(datos, 'carrier')}\n"
        f"☎️ Tipo de línea: {valor(datos, 'phone_type', 'type')}\n"
        f"✅ Válido: {valor(datos, 'phone_valid', 'valid')}"
    )


def skill_validar_telefono_veriphone(comando: str, remitente: str = "") -> str:
    coincidencia = PATRON.search(comando or "")
    return verificar_veriphone(coincidencia.group(0) if coincidencia else "")
