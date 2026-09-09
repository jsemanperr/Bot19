# -*- coding: utf-8 -*-
"""Búsqueda de recetas con RecipeAPI."""

import logging
import os

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.recipeapi")
URL = "https://recipeapi.io/api/v1/recipes"


def recipeapi(consulta: str) -> str:
    clave = os.getenv("RECIPEAPI_API_KEY", "")
    faltante = clave_requerida("RECIPEAPI_API_KEY", clave)
    if faltante:
        return faltante
    if not consulta.strip():
        return "🍽️ Indícame una receta o ingrediente."
    datos, error = solicitar("GET", URL, params={"search": consulta.strip()}, headers={"Authorization": f"Bearer {clave}"}, logger=logger)
    if error:
        return error
    resultados = datos.get("recipes", datos.get("data", [])) if isinstance(datos, dict) else datos
    if not resultados:
        return f"🍽️ No encontré recetas para «{consulta}»."
    lineas = []
    for receta in resultados[:5]:
        if isinstance(receta, dict):
            lineas.append(f"• {valor(receta, 'title', 'name', defecto='Receta sin nombre')}")
    return "🍽️ Recetas encontradas:\n" + "\n".join(lineas)


def skill_recipeapi(comando: str, remitente: str = "") -> str:
    return recipeapi(comando or "")
