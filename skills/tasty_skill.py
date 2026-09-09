# -*- coding: utf-8 -*-
"""Recetas de Tasty mediante RapidAPI."""

import logging
import os

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.tasty")
URL = "https://tasty.p.rapidapi.com/recipes/list"


def tasty_recipes(consulta: str) -> str:
    clave = os.getenv("RAPIDAPI_KEY", "")
    faltante = clave_requerida("RAPIDAPI_KEY", clave)
    if faltante:
        return faltante
    datos, error = solicitar(
        "GET", URL,
        params={"from": "0", "size": "10", "q": consulta.strip()},
        headers={"x-rapidapi-key": clave, "x-rapidapi-host": "tasty.p.rapidapi.com"},
        logger=logger,
    )
    if error:
        return error
    recetas = datos.get("results", []) if isinstance(datos, dict) else []
    if not recetas:
        return "🍳 No encontré recetas con ese criterio."
    return "🍳 Recetas Tasty:\n" + "\n".join(
        f"• {valor(receta, 'name', 'slug', defecto='Receta sin nombre')}" for receta in recetas[:10] if isinstance(receta, dict)
    )


def skill_tasty_recipes(comando: str, remitente: str = "") -> str:
    return tasty_recipes(comando or "")
