# -*- coding: utf-8 -*-
"""Consulta de titulares recientes mediante GNews."""

import os

import requests
from dotenv import load_dotenv


load_dotenv()
GNEWS_URL = "https://gnews.io/api/v4/search"


def consultar_noticias(consulta: str, remitente: str = "") -> str:
    """Devuelve titulares actuales relacionados con una consulta en español."""
    tema = (consulta or "").strip()
    clave = os.getenv("GNEWS_API_KEY", "")
    if not tema:
        return "Decime de qué lugar o tema querés las noticias, Jefe."
    if not clave:
        return "La búsqueda de noticias todavía no está configurada."

    try:
        respuesta = requests.get(
            GNEWS_URL,
            params={
                "q": tema,
                "lang": "es",
                "max": 3,
                "apikey": clave,
            },
            timeout=15,
        )
        respuesta.raise_for_status()
        articulos = respuesta.json().get("articles", [])
    except requests.RequestException:
        return "No pude consultar las noticias ahora mismo. Probemos de nuevo en un momento."
    except ValueError:
        return "La fuente de noticias devolvió una respuesta inválida."

    if not articulos:
        return f"No encontré noticias recientes sobre {tema}. ¿Querés que busque un tema más amplio?"

    lineas = [f"Estas son las noticias recientes sobre {tema}:"]
    for articulo in articulos:
        titulo = articulo.get("title", "Sin título")
        medio = articulo.get("source", {}).get("name", "Fuente desconocida")
        enlace = articulo.get("url", "")
        lineas.append(f"- {titulo} ({medio})\n  {enlace}")
    return "\n".join(lineas)