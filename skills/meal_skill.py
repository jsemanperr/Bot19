# -*- coding: utf-8 -*-
"""Recetas de comidas mediante TheMealDB."""

import logging
import re

from skills.api_helpers import solicitar, valor

logger = logging.getLogger("jarvis.skills.meal")
URL = "https://www.themealdb.com/api/json/v1/1"


def _formatear(datos: dict) -> str:
    comidas = datos.get("meals") or []
    if not comidas:
        return "🍽️ No encontré esa comida."
    comida = comidas[0]
    return f"🍽️ {valor(comida, 'strMeal')}\n🌍 Categoría: {valor(comida, 'strCategory')}\n🗺️ Origen: {valor(comida, 'strArea')}\n🔗 {valor(comida, 'strSource', defecto='Sin enlace')}"


def skill_meal_random(remitente: str = "") -> str:
    datos, error = solicitar("GET", f"{URL}/random.php", logger=logger)
    return error or _formatear(datos)


def skill_meal_search(comando: str, remitente: str = "") -> str:
    nombre = re.sub(r"(?i).*?(?:comida|receta|plato)\s*", "", comando or "").strip()
    if not nombre:
        return "🍽️ Indícame el nombre de la comida."
    datos, error = solicitar("GET", f"{URL}/search.php", params={"s": nombre}, logger=logger)
    return error or _formatear(datos)


def skill_meal_by_category(comando: str, remitente: str = "") -> str:
    categoria = re.sub(r"(?i).*?(?:categoría|categoria)\s*", "", comando or "").strip()
    if not categoria:
        return "🍽️ Indícame una categoría."
    datos, error = solicitar("GET", f"{URL}/filter.php", params={"c": categoria}, logger=logger)
    return error or _formatear(datos)
