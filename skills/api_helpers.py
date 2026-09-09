# -*- coding: utf-8 -*-
"""Utilidades compartidas para las skills HTTP externas."""

import logging
from typing import Any

import requests


TIMEOUT_SEGUNDOS = 15


def solicitar(
    metodo: str,
    url: str,
    *,
    params: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
    json: dict[str, Any] | None = None,
    logger: logging.Logger,
) -> tuple[dict[str, Any] | list[Any] | None, str | None]:
    """Ejecuta una solicitud JSON y devuelve datos o un mensaje de error."""
    try:
        respuesta = requests.request(
            metodo,
            url,
            params=params,
            headers=headers,
            json=json,
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.Timeout:
        return None, "⏱️ La API tardó demasiado en responder."
    except requests.RequestException as error:
        logger.warning("Error de red consultando %s: %s", url, error)
        return None, "🌐 No pude contactar el servicio en este momento."

    try:
        datos = respuesta.json()
    except ValueError:
        datos = None

    if respuesta.status_code == 429:
        return None, "🚦 Se alcanzó el límite de solicitudes. Intenta más tarde."
    if respuesta.status_code in (401, 403):
        return None, "🔐 La API rechazó la credencial configurada."
    if not respuesta.ok:
        logger.warning("Respuesta HTTP %s de %s: %s", respuesta.status_code, url, datos)
        return None, f"⚠️ El servicio respondió con un error ({respuesta.status_code})."
    if datos is None:
        return None, "⚠️ El servicio devolvió una respuesta no válida."
    return datos, None


def clave_requerida(nombre: str, valor: str) -> str | None:
    """Devuelve un mensaje uniforme cuando falta una clave."""
    if not valor.strip():
        return f"⚠️ Falta configurar {nombre} en el archivo .env."
    return None


def valor(datos: dict[str, Any], *rutas: str, defecto: str = "N/D") -> Any:
    """Busca el primer campo disponible en un diccionario."""
    for ruta in rutas:
        actual: Any = datos
        for parte in ruta.split("."):
            if not isinstance(actual, dict) or parte not in actual:
                actual = None
                break
            actual = actual[parte]
        if actual not in (None, ""):
            return actual
    return defecto
