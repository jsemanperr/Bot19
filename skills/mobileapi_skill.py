# -*- coding: utf-8 -*-
"""Búsqueda de especificaciones de teléfonos con MobileAPI.dev."""

import logging
import os
import re

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.mobileapi")
URL = "https://api.mobileapi.dev/devices/search/"


def buscar_celular(nombre: str) -> str:
    clave = os.getenv("MOBILEAPI_API_KEY", "")
    faltante = clave_requerida("MOBILEAPI_API_KEY", clave)
    if faltante:
        return faltante
    nombre = nombre.strip()
    if not nombre:
        return "📱 Indícame el nombre del celular que quieres buscar."
    datos, error = solicitar(
        "GET",
        URL,
        params={"name": nombre},
        headers={"Authorization": f"Token {clave}"},
        logger=logger,
    )
    if error:
        return error
    resultados = datos.get("devices", datos.get("data", datos)) if isinstance(datos, dict) else datos
    if not resultados:
        return f"📱 No encontré dispositivos para «{nombre}»."
    dispositivo = resultados[0] if isinstance(resultados, list) else resultados
    if not isinstance(dispositivo, dict):
        return "⚠️ MobileAPI devolvió un formato inesperado."
    return (
        f"📱 {valor(dispositivo, 'name', 'model', 'device_name')}\n"
        f"🖥️ Pantalla: {valor(dispositivo, 'screen_resolution', 'display', 'screen', 'specs.display')}\n"
        f"🧠 RAM: {valor(dispositivo, 'hardware', 'ram', 'memory.ram', 'specs.ram')}\n"
        f"🔋 Batería: {valor(dispositivo, 'battery_capacity', 'battery', 'specs.battery')}\n"
        f"📷 Cámara: {valor(dispositivo, 'camera', 'camera.main', 'specs.camera')}"
    )


def skill_buscar_celular(comando: str, remitente: str = "") -> str:
    texto = re.sub(r"(?i).*?(?:celular|teléfono|telefono|móvil|movil)\s*", "", comando or "").strip()
    return buscar_celular(texto)
