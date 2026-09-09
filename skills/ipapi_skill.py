# -*- coding: utf-8 -*-
"""Geolocalizacion aproximada de IP mediante ipapi."""

import ipaddress
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SEGUNDOS = 8
PATRON_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def geoip_ipapi(ip: str) -> str:
    """Consulta ipapi para una IP publica indicada explicitamente."""
    clave = os.getenv("IPAPI_API_KEY", "").strip()
    destino = (ip or "").strip()
    if not clave:
        return "⚠️ Falta configurar IPAPI_API_KEY en .env."
    try:
        direccion = ipaddress.ip_address(destino)
    except ValueError:
        return "⚠️ Indicame una direccion IP publica valida."
    if not direccion.is_global:
        return "⚠️ Solo puedo consultar direcciones IP publicas."
    try:
        respuesta = requests.get(f"https://api.ipapi.com/api/{destino}", params={"access_key": clave}, timeout=TIMEOUT_SEGUNDOS)
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        return "⚠️ No pude contactar ipapi en este momento."
    if respuesta.status_code == 429:
        return "⚠️ ipapi alcanzo el limite de solicitudes. Intenta mas tarde."
    if not respuesta.ok or datos.get("success") is False:
        return "⚠️ ipapi rechazo la consulta. Revisa IPAPI_API_KEY."
    conexion = datos.get("connection") or {}
    return (
        f"🌐 IP: {datos.get('ip', destino)}\n"
        f"📍 Ubicacion: {datos.get('city') or 'N/D'}, {datos.get('region_name') or 'N/D'}, {datos.get('country_name') or 'N/D'}\n"
        f"🏢 ISP: {conexion.get('isp') or 'N/D'}\n"
        f"🧭 Coordenadas: {datos.get('latitude', 'N/D')}, {datos.get('longitude', 'N/D')}"
    )


def skill_geoip_ipapi(comando: str, remitente: str = "") -> str:
    """Extrae la IP para la consulta ipapi."""
    coincidencia = PATRON_IP.search(comando or "")
    return geoip_ipapi(coincidencia.group(0) if coincidencia else "")