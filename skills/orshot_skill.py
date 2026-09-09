# -*- coding: utf-8 -*-
"""Generación de imágenes desde plantillas con Orshot."""

import json
import logging
import os
import re

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.orshot")
URL = "https://api.orshot.com/v1/studio/render"


def generar_orshot(plantilla: str, modificaciones: dict | None = None) -> str:
    clave = os.getenv("ORSHOT_API_KEY", "")
    faltante = clave_requerida("ORSHOT_API_KEY", clave)
    if faltante:
        return faltante
    if not plantilla.strip():
        return "🖼️ Indícame el templateId de Orshot."
    cuerpo = {"templateId": plantilla.strip(), "modifications": modificaciones or {}}
    datos, error = solicitar("POST", URL, json=cuerpo, headers={"Authorization": f"Bearer {clave}"}, logger=logger)
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ Orshot devolvió un formato inesperado."
    return f"🖼️ Imagen generada:\n{valor(datos, 'url', 'imageUrl', 'data.url', defecto=json.dumps(datos, ensure_ascii=False))}"


def skill_generar_imagen_orshot(comando: str, remitente: str = "") -> str:
    texto = (comando or "").strip()
    coincidencia = re.search(r"(?i)(?:templateId|plantilla)\s*[:=]?\s*([A-Za-z0-9_-]+)", texto)
    if not coincidencia:
        return "🖼️ Indícame una plantilla, por ejemplo: Orshot templateId 123 título: Hola."
    modificaciones = {}
    for campo in ("título", "titulo", "subtítulo", "subtitulo", "logo"):
        encontrado = re.search(rf"(?i){campo}\s*[:=]\s*([^,;]+)", texto)
        if encontrado:
            modificaciones[campo.replace("í", "i")] = encontrado.group(1).strip()
    return generar_orshot(coincidencia.group(1), modificaciones)
