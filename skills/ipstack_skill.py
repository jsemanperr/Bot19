# -*- coding: utf-8 -*-
"""Geolocalizacion aproximada de IP mediante ipstack."""

import ipaddress
import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SEGUNDOS = 8
PATRON_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")


def _ip_publica() -> str | None:
    """Obtiene la IP publica del equipo cuando no se indico una."""
    try:
        respuesta = requests.get("https://api.ipify.org", params={"format": "json"}, timeout=TIMEOUT_SEGUNDOS)
        respuesta.raise_for_status()
        return respuesta.json().get("ip")
    except (requests.RequestException, ValueError):
        return None


def geoip_ipstack(ip: str = "") -> str:
    """Consulta ipstack para una IP publica y formatea sus datos."""
    clave = os.getenv("IPSTACK_API_KEY", "").strip()
    destino = (ip or _ip_publica() or "").strip()
    if not clave:
        return "⚠️ Falta configurar IPSTACK_API_KEY en .env."
    try:
        direccion = ipaddress.ip_address(destino)
    except ValueError:
        return "⚠️ Indicame una direccion IP publica valida."
    if not direccion.is_global:
        return "⚠️ Solo puedo consultar direcciones IP publicas."
    try:
        respuesta = requests.get(f"http://api.ipstack.com/{destino}", params={"access_key": clave}, timeout=TIMEOUT_SEGUNDOS)
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        return "⚠️ No pude contactar ipstack en este momento."
    if respuesta.status_code == 429:
        return "⚠️ ipstack alcanzo el limite de solicitudes. Intenta mas tarde."
    if not respuesta.ok or datos.get("success") is False:
        return "⚠️ ipstack rechazo la consulta. Revisa IPSTACK_API_KEY."
    conexion = datos.get("connection") or {}
    zona = (datos.get("time_zone") or {}).get("id", "no informada")
    return (
        f"🌐 IP: {datos.get('ip', destino)}\n"
        f"📍 Ubicacion: {datos.get('city') or 'N/D'}, {datos.get('region_name') or 'N/D'}, {datos.get('country_name') or 'N/D'}\n"
        f"🏢 ISP: {conexion.get('isp') or 'N/D'}\n"
        f"🧭 Coordenadas: {datos.get('latitude', 'N/D')}, {datos.get('longitude', 'N/D')}\n"
        f"🕒 Zona horaria: {zona}"
    )


def skill_geoip_ipstack(comando: str, remitente: str = "") -> str:
    """Extrae una IP del texto o usa la IP publica local."""
    coincidencia = PATRON_IP.search(comando or "")
    return geoip_ipstack(coincidencia.group(0) if coincidencia else "")