# -*- coding: utf-8 -*-
"""Inteligencia de IP con AbstractAPI."""

import ipaddress
import logging
import os
import re

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.abstract_ip")
URL = "https://ip-intelligence.abstractapi.com/v1/"
PATRON = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def abstract_ip(ip: str) -> str:
    clave = os.getenv("ABSTRACT_IP_API_KEY", "")
    faltante = clave_requerida("ABSTRACT_IP_API_KEY", clave)
    if faltante:
        return faltante
    try:
        ipaddress.ip_address(ip)
    except ValueError:
        return "🌐 Indícame una dirección IP válida."
    datos, error = solicitar("GET", URL, params={"api_key": clave, "ip_address": ip}, logger=logger)
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ AbstractAPI devolvió un formato inesperado."
    return (
        f"🌐 IP: {valor(datos, 'ip_address', defecto=ip)}\n"
        f"📍 Ubicación: {valor(datos, 'city')}, {valor(datos, 'region')}, {valor(datos, 'country')}\n"
        f"🏢 ISP: {valor(datos, 'connection.organization', 'isp')}\n"
        f"🧭 Coordenadas: {valor(datos, 'location.latitude')}, {valor(datos, 'location.longitude')}"
    )


def skill_abstract_ip(comando: str, remitente: str = "") -> str:
    coincidencia = PATRON.search(comando or "")
    return abstract_ip(coincidencia.group(0) if coincidencia else "")
