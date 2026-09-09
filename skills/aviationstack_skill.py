# -*- coding: utf-8 -*-
"""Consulta de vuelos mediante aviationstack."""

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SEGUNDOS = 10


def info_vuelo(vuelo: str) -> str:
    """Obtiene el estado del primer vuelo que coincida con el codigo IATA."""
    clave = os.getenv("AVIATIONSTACK_API_KEY", "").strip()
    vuelo = (vuelo or "").upper().replace(" ", "")
    if not re.fullmatch(r"[A-Z0-9]{2,3}\d{1,4}", vuelo):
        return "⚠️ Indicame un vuelo valido, por ejemplo: vuelo AM123."
    if not clave:
        return "⚠️ Falta configurar AVIATIONSTACK_API_KEY en .env."
    try:
        respuesta = requests.get(
            "http://api.aviationstack.com/v1/flights",
            params={"access_key": clave, "flight_iata": vuelo, "limit": 1}, timeout=TIMEOUT_SEGUNDOS,
        )
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        return "⚠️ No pude contactar aviationstack en este momento."
    if respuesta.status_code == 429:
        return "⚠️ aviationstack alcanzo el limite de solicitudes. Intenta mas tarde."
    if not respuesta.ok or datos.get("error"):
        return "⚠️ aviationstack rechazo la consulta. Revisa AVIATIONSTACK_API_KEY."
    resultados = datos.get("data") or []
    if not resultados:
        return f"⚠️ No encontre informacion actual para el vuelo {vuelo}."
    resultado = resultados[0]
    salida = resultado.get("departure") or {}
    llegada = resultado.get("arrival") or {}
    aerolinea = resultado.get("airline") or {}
    numero = resultado.get("flight") or {}
    return (
        f"✈️ Vuelo {numero.get('iata', vuelo)} - {aerolinea.get('name', 'N/D')}\n"
        f"📊 Estado: {resultado.get('flight_status') or 'N/D'}\n"
        f"🛫 Origen: {salida.get('airport') or 'N/D'} | Sale: {salida.get('scheduled') or 'N/D'}\n"
        f"🛬 Destino: {llegada.get('airport') or 'N/D'} | Llega: {llegada.get('scheduled') or 'N/D'}\n"
        f"⏱️ Retraso: salida {salida.get('delay') or 0} min, llegada {llegada.get('delay') or 0} min"
    )


def skill_info_vuelo(comando: str, remitente: str = "") -> str:
    """Extrae un identificador de vuelo de la orden recibida."""
    coincidencia = re.search(r"\b[A-Z0-9]{2,3}\s?\d{1,4}\b", comando or "", re.I)
    return info_vuelo(coincidencia.group(0) if coincidencia else "")