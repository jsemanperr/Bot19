# -*- coding: utf-8 -*-
"""Clima actual mediante weatherstack."""

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SEGUNDOS = 8


def clima_actual(ciudad: str) -> str:
    """Consulta condiciones actuales de una ciudad en weatherstack."""
    clave = os.getenv("WEATHERSTACK_API_KEY", "").strip()
    ciudad = (ciudad or "").strip()
    if not ciudad:
        return "⚠️ Decime la ciudad, por ejemplo: weatherstack clima en Oaxaca."
    if not clave:
        return "⚠️ Falta configurar WEATHERSTACK_API_KEY en .env."
    try:
        respuesta = requests.get(
            "http://api.weatherstack.com/current",
            params={"access_key": clave, "query": ciudad, "units": "m", "language": "es"},
            timeout=TIMEOUT_SEGUNDOS,
        )
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        return "⚠️ No pude contactar weatherstack en este momento."
    if respuesta.status_code == 429:
        return "⚠️ weatherstack alcanzo el limite de solicitudes. Intenta mas tarde."
    if not respuesta.ok or datos.get("success") is False:
        return "⚠️ weatherstack rechazo la consulta. Revisa WEATHERSTACK_API_KEY o la ciudad indicada."
    actual = datos.get("current") or {}
    ubicacion = datos.get("location") or {}
    descripcion = ", ".join(actual.get("weather_descriptions") or ["N/D"])
    astro = actual.get("astro") or {}
    return (
        f"☀️ Clima en {ubicacion.get('name', ciudad)}, {ubicacion.get('country', '')}\n"
        f"🌡️ Temperatura: {actual.get('temperature', 'N/D')} °C | {descripcion}\n"
        f"💧 Humedad: {actual.get('humidity', 'N/D')}%\n"
        f"💨 Viento: {actual.get('wind_speed', 'N/D')} km/h\n"
        f"📈 Presion: {actual.get('pressure', 'N/D')} hPa\n"
        f"🌅 Salida del sol: {astro.get('sunrise', 'N/D')} | 🌇 Puesta: {astro.get('sunset', 'N/D')}"
    )


def skill_clima_weatherstack(comando: str, remitente: str = "") -> str:
    """Extrae la ciudad de una orden que mencione weatherstack."""
    coincidencia = re.search(r"(?:weatherstack\s+)?clima\s+(?:actual\s+)?(?:en|de|para)\s+(.+)", comando or "", re.I)
    if not coincidencia:
        coincidencia = re.search(r"weatherstack\s+(.+)", comando or "", re.I)
    return clima_actual(coincidencia.group(1).strip(" .?!") if coincidencia else "")