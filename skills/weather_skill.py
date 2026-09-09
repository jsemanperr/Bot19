# -*- coding: utf-8 -*-
"""
skills/weather_skill.py
========================
Skill de ejemplo: consulta el clima actual de una ciudad usando la
API publica y gratuita de Open-Meteo (no requiere API key), a modo
de referencia de como implementar una skill nueva.
"""

import logging
import os

import requests
from dotenv import load_dotenv

logger = logging.getLogger("jarvis.skills.weather")

TIMEOUT_SEGUNDOS = 10
load_dotenv()
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY", "").strip()

_CODIGOS_CLIMA = {
    0: "cielo despejado", 1: "mayormente despejado", 2: "parcialmente nublado", 3: "nublado",
    45: "niebla", 51: "llovizna leve", 53: "llovizna", 55: "llovizna intensa",
    61: "lluvia leve", 63: "lluvia", 65: "lluvia intensa", 71: "nieve leve", 73: "nieve",
    75: "nieve intensa", 80: "chaparrones leves", 81: "chaparrones", 82: "chaparrones intensos",
    95: "tormenta", 96: "tormenta con granizo", 99: "tormenta fuerte con granizo",
}


def _geocodificar(ciudad: str):
    """Convierte un nombre de ciudad en coordenadas lat/lon."""
    url = "https://geocoding-api.open-meteo.com/v1/search"
    resp = requests.get(url, params={"name": ciudad, "count": 1, "language": "es"}, timeout=TIMEOUT_SEGUNDOS)
    resp.raise_for_status()
    resultados = resp.json().get("results")
    if not resultados:
        return None
    r = resultados[0]
    return r["latitude"], r["longitude"], r.get("name", ciudad)


def _descripcion(codigo: int | None) -> str:
    return _CODIGOS_CLIMA.get(codigo, "condiciones variables")


def _consultar_openweather(ciudad: str) -> str | None:
    """Obtiene condiciones actuales de OpenWeather cuando hay una clave configurada."""
    if not OPENWEATHER_API_KEY:
        return None
    try:
        respuesta = requests.get(
            "https://api.openweathermap.org/data/2.5/weather",
            params={"q": ciudad, "appid": OPENWEATHER_API_KEY, "units": "metric", "lang": "es"},
            timeout=TIMEOUT_SEGUNDOS,
        )
        respuesta.raise_for_status()
        datos = respuesta.json()
        principal = datos.get("main", {})
        if not principal:
            return None
        descripcion = (datos.get("weather") or [{}])[0].get("description", "condiciones variables")
        viento = datos.get("wind", {}).get("speed")
        lluvia = sum((datos.get("rain") or {}).values())
        texto_lluvia = f", lluvia {lluvia} mm" if lluvia else ""
        return (
            f"En {datos.get('name', ciudad)} hay {descripcion}: {principal.get('temp')}°C, "
            f"sensación de {principal.get('feels_like')}°C, humedad {principal.get('humidity')}% "
            f"y viento de {viento} m/s{texto_lluvia}."
        )
    except requests.RequestException as error:
        logger.warning("OpenWeather no respondió para '%s'; se usa Open-Meteo: %s", ciudad, error)
        return None


def consultar_clima(ciudad: str, remitente: str = "") -> str:
    """
    Devuelve un resumen en texto del clima actual de la ciudad indicada.
    """
    if not ciudad or not ciudad.strip():
        return "Decime de que ciudad queres saber el clima."

    try:
        clima_openweather = _consultar_openweather(ciudad.strip())
        if clima_openweather:
            return clima_openweather

        coords = _geocodificar(ciudad.strip())
        if not coords:
            return f"No encontre la ciudad '{ciudad}'."
        lat, lon, nombre_normalizado = coords

        url = "https://api.open-meteo.com/v1/forecast"
        params = {
            "latitude": lat,
            "longitude": lon,
            "current": "temperature_2m,apparent_temperature,relative_humidity_2m,precipitation,weather_code,wind_speed_10m",
            "timezone": "auto",
        }
        resp = requests.get(url, params=params, timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        clima = resp.json().get("current", {})

        if not clima:
            return f"No pude obtener el clima de {nombre_normalizado}."

        lluvia = clima.get("precipitation", 0)
        texto_lluvia = f", lluvia {lluvia} mm" if lluvia else ""
        return (
            f"En {nombre_normalizado} hay {_descripcion(clima.get('weather_code'))}: "
            f"{clima.get('temperature_2m')}°C, sensación de {clima.get('apparent_temperature')}°C, "
            f"humedad {clima.get('relative_humidity_2m')}% y viento de {clima.get('wind_speed_10m')} km/h{texto_lluvia}."
        )

    except requests.exceptions.RequestException as e:
        logger.error("Error consultando clima para '%s': %s", ciudad, e)
        return f"No pude consultar el clima de {ciudad} en este momento."
    except Exception as e:
        logger.exception("Error inesperado consultando clima: %s", e)
        return "Ocurrio un error inesperado consultando el clima."


def consultar_pronostico(ciudad: str, remitente: str = "") -> str:
    """Devuelve el pronóstico de hoy y mañana."""
    if not ciudad or not ciudad.strip():
        return "Decime la ciudad, por ejemplo: pronóstico en Buenos Aires."
    try:
        coords = _geocodificar(ciudad.strip())
        if not coords:
            return f"No encontré la ciudad '{ciudad}'."
        lat, lon, nombre = coords
        respuesta = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": lat, "longitude": lon,
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,uv_index_max",
                "forecast_days": 2, "timezone": "auto",
            }, timeout=TIMEOUT_SEGUNDOS,
        )
        respuesta.raise_for_status()
        diario = respuesta.json().get("daily", {})
        if not diario.get("time"):
            return f"No pude obtener el pronóstico de {nombre}."

        def resumen(indice: int, etiqueta: str) -> str:
            return (
                f"{etiqueta}: {_descripcion(diario['weather_code'][indice])}, "
                f"mínima {diario['temperature_2m_min'][indice]}°C, máxima {diario['temperature_2m_max'][indice]}°C, "
                f"lluvia {diario['precipitation_probability_max'][indice]}% y UV {diario['uv_index_max'][indice]}."
            )

        return f"Pronóstico para {nombre}. {resumen(0, 'Hoy')} {resumen(1, 'Mañana')}"
    except requests.RequestException as e:
        logger.error("Error consultando pronóstico para '%s': %s", ciudad, e)
        return f"No pude consultar el pronóstico de {ciudad} en este momento."


def consultar_calidad_aire(ciudad: str, remitente: str = "") -> str:
    """Devuelve los indicadores actuales de calidad del aire."""
    if not ciudad or not ciudad.strip():
        return "Decime la ciudad, por ejemplo: calidad del aire en Buenos Aires."
    try:
        coords = _geocodificar(ciudad.strip())
        if not coords:
            return f"No encontré la ciudad '{ciudad}'."
        lat, lon, nombre = coords
        respuesta = requests.get(
            "https://air-quality-api.open-meteo.com/v1/air-quality",
            params={"latitude": lat, "longitude": lon, "current": "us_aqi,pm2_5,pm10"},
            timeout=TIMEOUT_SEGUNDOS,
        )
        respuesta.raise_for_status()
        actual = respuesta.json().get("current", {})
        aqi = actual.get("us_aqi")
        if aqi is None:
            return f"No pude obtener la calidad del aire de {nombre}."
        estado = "buena" if aqi <= 50 else "moderada" if aqi <= 100 else "poco saludable"
        return f"En {nombre} la calidad del aire es {estado} (AQI {aqi}, PM2.5 {actual.get('pm2_5')} µg/m³, PM10 {actual.get('pm10')} µg/m³)."
    except requests.RequestException as e:
        logger.error("Error consultando calidad de aire para '%s': %s", ciudad, e)
        return f"No pude consultar la calidad del aire de {ciudad} en este momento."
