# -*- coding: utf-8 -*-
"""Datos curiosos mediante World Fun Facts en RapidAPI."""

import logging
import os

from skills.api_helpers import clave_requerida, solicitar, valor

logger = logging.getLogger("jarvis.skills.fun_fact")
URL = "https://world-fun-facts-all-languages-support.p.rapidapi.com/fact.php"


def fun_fact() -> str:
    clave = os.getenv("RAPIDAPI_KEY", "")
    faltante = clave_requerida("RAPIDAPI_KEY", clave)
    if faltante:
        return faltante
    datos, error = solicitar(
        "GET", URL,
        headers={"x-rapidapi-key": clave, "x-rapidapi-host": "world-fun-facts-all-languages-support.p.rapidapi.com"},
        logger=logger,
    )
    if error:
        return error
    if not isinstance(datos, dict):
        return "⚠️ World Fun Facts devolvió un formato inesperado."
    return f"💡 Dato curioso:\n{valor(datos, 'fact', 'data', 'text', defecto='No se recibió ningún dato.')}"


def skill_fun_fact(remitente: str = "") -> str:
    return fun_fact()
