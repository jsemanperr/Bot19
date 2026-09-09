# -*- coding: utf-8 -*-
"""Validacion de numeros telefonicos mediante NumVerify."""

import os
import re

import requests
from dotenv import load_dotenv

load_dotenv()

URL_NUMVERIFY = "http://apilayer.net/api/validate"
TIMEOUT_SEGUNDOS = 10


def validar_telefono(numero: str) -> str:
    """Valida un telefono y devuelve sus datos publicos de red."""
    clave = os.getenv("NUMVERIFY_API_KEY", "").strip()
    numero = re.sub(r"[^0-9+]", "", numero or "")
    if not numero:
        return "Indicame un numero telefonico, preferentemente con codigo de pais."
    if not clave:
        return "La validacion telefonica requiere configurar NUMVERIFY_API_KEY en .env."

    try:
        respuesta = requests.get(
            URL_NUMVERIFY,
            params={"access_key": clave, "number": numero},
            timeout=TIMEOUT_SEGUNDOS,
        )
        datos = respuesta.json()
    except (requests.RequestException, ValueError):
        return "No pude contactar NumVerify en este momento."

    if respuesta.status_code == 429 or datos.get("error", {}).get("code") in {104, 429}:
        return "NumVerify alcanzo su limite de consultas. Espera al proximo ciclo de cuota."
    if not respuesta.ok or datos.get("success") is False:
        return "NumVerify rechazo la consulta. Revisa que NUMVERIFY_API_KEY sea valida."
    if not datos.get("valid"):
        return f"El numero {numero} no parece valido."

    tipo = datos.get("line_type") or "no informado"
    pais = datos.get("country_name") or "no informado"
    operador = datos.get("carrier") or "no informado"
    internacional = datos.get("international_format") or numero
    return (
        f"Numero valido: {internacional}. Pais: {pais}. "
        f"Operador: {operador}. Tipo de linea: {tipo}."
    )


def skill_validar_telefono(comando: str, remitente: str = "") -> str:
    """Extrae y valida el primer telefono incluido en un comando."""
    coincidencia = re.search(r"(?:\+?\d[\d\s().-]{5,}\d)", comando or "")
    if not coincidencia:
        return "Decime el numero a validar, por ejemplo: valida telefono +5491112345678."
    return validar_telefono(coincidencia.group(0))