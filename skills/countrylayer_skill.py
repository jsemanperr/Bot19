# -*- coding: utf-8 -*-
"""Informacion de paises mediante countrylayer."""

import os
import re
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SEGUNDOS = 8


def _lista(valor: object) -> str:
    """Convierte listas de campos de la API en texto legible."""
    if isinstance(valor, list):
        return ", ".join(str(item.get("name") or item.get("code") or item) if isinstance(item, dict) else str(item) for item in valor) or "N/D"
    return str(valor or "N/D")


def info_pais(pais: str) -> str:
    """Consulta countrylayer y muestra datos generales del pais indicado."""
    clave = os.getenv("COUNTRYLAYER_API_KEY", "").strip()
    pais = (pais or "").strip()
    if not pais:
        return "⚠️ Decime que pais queres consultar, por ejemplo: info pais Argentina."
    if not clave:
        return "⚠️ Falta configurar COUNTRYLAYER_API_KEY en .env."
    try:
        respuesta = requests.get(
            f"https://api.countrylayer.com/v2/name/{quote(pais)}",
            params={"access_key": clave}, timeout=TIMEOUT_SEGUNDOS,
        )
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        return "⚠️ No pude contactar countrylayer en este momento."
    if respuesta.status_code == 429:
        return "⚠️ countrylayer alcanzo el limite de solicitudes. Intenta mas tarde."
    if not respuesta.ok or (isinstance(datos, dict) and datos.get("success") is False):
        return "⚠️ countrylayer rechazo la consulta. Revisa COUNTRYLAYER_API_KEY."
    resultado = datos[0] if isinstance(datos, list) and datos else None
    if not resultado:
        return f"⚠️ No encontre informacion para {pais}."
    moneda = _lista(resultado.get("currencies"))
    idiomas = _lista(resultado.get("languages"))
    prefijos = _lista(resultado.get("callingCodes"))
    bandera = resultado.get("flag") or "N/D"
    return (
        f"🌍 {resultado.get('name', pais)}\n"
        f"🏛️ Capital: {resultado.get('capital') or 'N/D'}\n"
        f"👥 Poblacion: {resultado.get('population') or 'N/D'}\n"
        f"🗣️ Idiomas: {idiomas}\n"
        f"💱 Moneda: {moneda}\n"
        f"🧭 Region: {resultado.get('region') or 'N/D'}\n"
        f"📞 Codigo telefonico: +{prefijos}\n"
        f"🏳️ Bandera: {bandera}"
    )


def skill_info_pais(comando: str, remitente: str = "") -> str:
    """Extrae el nombre del pais de una orden de Kaori."""
    coincidencia = re.search(r"(?:countrylayer|info(?:rmacion)?(?:\s+del)?\s+pais)\s+(?:de\s+)?(.+)", comando or "", re.I)
    return info_pais(coincidencia.group(1).strip(" .?!") if coincidencia else "")