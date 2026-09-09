# -*- coding: utf-8 -*-
"""Cócteles mediante TheCocktailDB."""

import logging
import re

from skills.api_helpers import solicitar, valor

logger = logging.getLogger("jarvis.skills.cocktail")
URL = "https://www.thecocktaildb.com/api/json/v1/1"


def _formatear(datos: dict) -> str:
    bebidas = datos.get("drinks") or []
    if not bebidas:
        return "🍸 No encontré ese cóctel."
    bebida = bebidas[0]
    ingredientes = []
    for numero in range(1, 16):
        ingrediente = bebida.get(f"strIngredient{numero}")
        medida = bebida.get(f"strMeasure{numero}")
        if ingrediente:
            ingredientes.append(f"• {(medida or '').strip()} {ingrediente}".strip())
    return f"🍸 {valor(bebida, 'strDrink')}\n🧾 Ingredientes:\n" + "\n".join(ingredientes)


def skill_cocktail_random(remitente: str = "") -> str:
    datos, error = solicitar("GET", f"{URL}/random.php", logger=logger)
    return error or _formatear(datos)


def skill_cocktail_search(comando: str, remitente: str = "") -> str:
    nombre = re.sub(r"(?i).*?(?:cóctel|coctel|cocktail)\s*", "", comando or "").strip()
    if not nombre:
        return "🍸 Indícame el nombre del cóctel."
    datos, error = solicitar("GET", f"{URL}/search.php", params={"s": nombre}, logger=logger)
    return error or _formatear(datos)


def skill_cocktail_by_ingredient(comando: str, remitente: str = "") -> str:
    ingrediente = re.sub(r"(?i).*?(?:ingrediente|con)\s*", "", comando or "").strip()
    if not ingrediente:
        return "🍸 Indícame un ingrediente."
    datos, error = solicitar("GET", f"{URL}/filter.php", params={"i": ingrediente}, logger=logger)
    return error or _formatear(datos)
