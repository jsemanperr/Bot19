# -*- coding: utf-8 -*-
"""Geolocalización IP y geocodificación inversa con Geoapify."""

import logging
import os
import re

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.geoapify")
URL_IP = "https://api.geoapify.com/v1/ipinfo"
URL_REVERSE = "https://api.geoapify.com/v1/geocode/reverse"
PATRON_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
PATRON_COORDENADAS = re.compile(r"(-?\d+(?:[.,]\d+)?)\s*[, ]\s*(-?\d+(?:[.,]\d+)?)")


def geoapify_ip(ip: str = "") -> str:
    clave = os.getenv("GEOAPIFY_API_KEY", "")
    faltante = clave_requerida("GEOAPIFY_API_KEY", clave)
    if faltante:
        return faltante
    parametros = {"apiKey": clave}
    if ip:
        parametros["ip"] = ip
    datos, error = solicitar("GET", URL_IP, params=parametros, logger=logger)
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ Geoapify devolvió un formato inesperado."
    return (
        f"🌐 IP: {valor(datos, 'ip', defecto=ip or 'actual')}\n"
        f"📍 Ubicación: {valor(datos, 'city.name', 'city')}, {valor(datos, 'state.name', 'state')}, {valor(datos, 'country.name', 'country')}\n"
        f"🏢 ISP: {valor(datos, 'as.name', 'isp')}\n"
        f"🧭 Coordenadas: {valor(datos, 'location.latitude')}, {valor(datos, 'location.longitude')}"
    )


def geoapify_reverse(latitud: str, longitud: str) -> str:
    clave = os.getenv("GEOAPIFY_API_KEY", "")
    faltante = clave_requerida("GEOAPIFY_API_KEY", clave)
    if faltante:
        return faltante
    datos, error = solicitar("GET", URL_REVERSE, params={"lat": latitud, "lon": longitud, "apiKey": clave}, logger=logger)
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ Geoapify devolvió un formato inesperado."
    resultados = datos.get("features") or []
    propiedades = resultados[0].get("properties", {}) if resultados else {}
    return f"📍 Dirección: {valor(propiedades, 'formatted', defecto='No encontrada')}\n🧭 Coordenadas: {latitud}, {longitud}"


def skill_geoapify_ip(comando: str, remitente: str = "") -> str:
    coincidencia = PATRON_IP.search(comando or "")
    return geoapify_ip(coincidencia.group(0) if coincidencia else "")


def skill_geoapify_reverse(comando: str, remitente: str = "") -> str:
    coincidencia = PATRON_COORDENADAS.search(comando or "")
    if not coincidencia:
        return "🧭 Indícame las coordenadas como latitud, longitud."
    return geoapify_reverse(coincidencia.group(1).replace(",", "."), coincidencia.group(2).replace(",", "."))
