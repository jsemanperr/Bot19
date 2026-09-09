# -*- coding: utf-8 -*-
"""Geolocalizacion aproximada de direcciones IP publicas."""

import ipaddress
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SEGUNDOS = 5


def _ip_publica() -> str | None:
    try:
        respuesta = requests.get("https://api.ipify.org", params={"format": "json"}, timeout=TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
        return respuesta.json().get("ip")
    except (requests.RequestException, ValueError):
        return None


def _formatear(datos: dict) -> str:
    ciudad = datos.get("city") or "no informada"
    region = datos.get("regionName") or datos.get("region") or "no informada"
    pais = datos.get("country") or "no informado"
    isp = datos.get("isp") or datos.get("org") or "no informado"
    zona = datos.get("timezone") or "no informada"
    coordenadas = datos.get("loc") or f"{datos.get('lat', 'N/D')}, {datos.get('lon', 'N/D')}"
    return (
        f"Ubicacion aproximada de {datos.get('query') or datos.get('ip')}: "
        f"{ciudad}, {region}, {pais}. ISP: {isp}. Coordenadas: {coordenadas}. Zona horaria: {zona}."
    )


def geoip(ip: str = "") -> str:
    """Consulta ip-api y usa ipinfo como respaldo cuando corresponde."""
    destino = (ip or _ip_publica() or "").strip()
    if not destino:
        return "No pude determinar la IP publica para consultarla."
    try:
        direccion = ipaddress.ip_address(destino)
    except ValueError:
        return "La direccion IP indicada no es valida."
    if direccion.is_private or direccion.is_loopback or direccion.is_reserved:
        return "Solo puedo geolocalizar direcciones IP publicas."

    try:
        respuesta = requests.get(
            f"http://ip-api.com/json/{destino}",
            params={"fields": "status,message,query,country,regionName,city,isp,lat,lon,timezone"},
            timeout=TIMEOUT_SEGUNDOS,
        )
        datos = respuesta.json()
        if respuesta.ok and datos.get("status") == "success":
            return _formatear(datos)
    except (requests.RequestException, ValueError):
        pass

    clave = os.getenv("IPINFO_API_KEY", "").strip()
    try:
        parametros = {"token": clave} if clave else {}
        respuesta = requests.get(f"https://ipinfo.io/{destino}/json", params=parametros, timeout=TIMEOUT_SEGUNDOS)
        datos = respuesta.json()
        if respuesta.ok and not datos.get("error"):
            datos["ip"] = destino
            return _formatear(datos)
    except (requests.RequestException, ValueError):
        pass
    return "No pude obtener la geolocalizacion de esa IP. Configura IPINFO_API_KEY para disponer de un respaldo."


def skill_geoip(comando: str, remitente: str = "") -> str:
    """Extrae una IP del comando, o consulta la IP publica local."""
    coincidencia = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", comando or "")
    return geoip(coincidencia.group(0) if coincidencia else "")