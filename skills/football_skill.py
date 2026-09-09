# -*- coding: utf-8 -*-
"""Consulta de ligas de fútbol con API-Sports."""

import logging
import os

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.football")
URL = "https://v3.football.api-sports.io/leagues"


def football_ligas(filtro: str = "") -> str:
    clave = os.getenv("FOOTBALL_API_KEY", "")
    faltante = clave_requerida("FOOTBALL_API_KEY", clave)
    if faltante:
        return faltante
    parametros = {"search": filtro.strip()} if filtro.strip() else {}
    datos, error = solicitar("GET", URL, params=parametros, headers={"x-apisports-key": clave}, logger=logger)
    if error:
        return error
    ligas = datos.get("response", []) if isinstance(datos, dict) else []
    if not ligas:
        return "⚽ No encontré ligas con ese criterio."
    lineas = []
    for item in ligas[:10]:
        liga = item.get("league", {})
        pais = item.get("country", {})
        lineas.append(f"• {valor(liga, 'name')} ({valor(pais, 'name')})")
    return "⚽ Ligas encontradas:\n" + "\n".join(lineas)


def skill_football_ligas(comando: str, remitente: str = "") -> str:
    return football_ligas(comando or "")
