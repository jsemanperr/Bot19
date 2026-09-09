# -*- coding: utf-8 -*-
"""Búsqueda nutricional con Dietly."""

import logging
import os

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.dietly")
URL = "https://api.getdietly.com/search"


def dietly_alimento(consulta: str) -> str:
    clave = os.getenv("DIETLY_API_KEY", "")
    faltante = clave_requerida("DIETLY_API_KEY", clave)
    if faltante:
        return faltante
    if not consulta.strip():
        return "🥗 Indícame un alimento para consultar."
    datos, error = solicitar(
        "GET",
        URL,
        params={"q": consulta.strip()},
        headers={"Authorization": f"Bearer {clave}"},
        logger=logger,
    )
    if error:
        return error
    resultados = datos.get("results", datos) if isinstance(datos, dict) else datos
    if not resultados:
        return f"🥗 No encontré información nutricional para «{consulta}»."
    alimento = resultados[0] if isinstance(resultados, list) else resultados
    if not isinstance(alimento, dict):
        return "⚠️ Dietly devolvió un formato inesperado."
    return (
        f"🥗 {valor(alimento, 'name', 'food_name', defecto=consulta)}\n"
        f"🔥 Calorías: {valor(alimento, 'calories_kcal', 'calories', 'nutrients.calories')}\n"
        f"💪 Proteínas: {valor(alimento, 'protein_g', 'protein', 'nutrients.protein')}\n"
        f"🍞 Carbohidratos: {valor(alimento, 'carbs_g', 'carbohydrates', 'nutrients.carbohydrates')}\n"
        f"🧈 Grasas: {valor(alimento, 'fat_g', 'fat', 'nutrients.fat')}"
    )


def skill_dietly(comando: str, remitente: str = "") -> str:
    return dietly_alimento(comando or "")
