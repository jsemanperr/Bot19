# -*- coding: utf-8 -*-
"""Consulta de códigos postales con Postali."""

import logging
import os
import re

from skills.api_helpers import solicitar, valor

logger = logging.getLogger("jarvis.skills.postali")
URL = "https://postali.app/api/v1"
PATRON = re.compile(r"(?i)(mx|mexico|méxico|co|colombia|es|españa|spain)?\s*(?:cp|código postal|codigo postal)?\s*(\d{4,6})")


def postali(pais: str, codigo: str) -> str:
    paises = {"mexico": "mx", "méxico": "mx", "colombia": "co", "españa": "es", "spain": "es"}
    pais = (pais or "mx").strip().lower()
    pais = paises.get(pais, pais)
    if pais not in {"mx", "co", "es"}:
        return "📮 Indícame el país (MX, CO o ES) y el código postal."
    datos, error = solicitar("GET", f"{URL}/{pais}/cp/{codigo}", logger=logger)
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ Postali devolvió un formato inesperado."
    asentamientos = datos.get("asentamientos", [])
    lineas = [
        f"• {valor(item, 'nombre')} ({valor(item, 'tipo')})"
        for item in asentamientos[:10]
        if isinstance(item, dict)
    ]
    detalle = "\n".join(lineas) if lineas else "N/D"
    return (
        f"📮 Código postal: {codigo}\n"
        f"🗺️ Estado/Provincia: {valor(datos, 'estado', 'state', 'province')}\n"
        f"🏙️ Municipio: {valor(datos, 'municipio', 'city', 'municipality')}\n"
        f"🏘️ Asentamientos:\n{detalle}"
    )


def skill_postali(comando: str, remitente: str = "") -> str:
    coincidencia = PATRON.search(comando or "")
    if not coincidencia:
        return "📮 Indícame país y código postal, por ejemplo: Postali MX 01000."
    pais = coincidencia.group(1) or os.getenv("POSTALI_PAIS", "mx")
    return postali(pais, coincidencia.group(2))
