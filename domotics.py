# -*- coding: utf-8 -*-
"""
domotics.py
============
Integracion generica con un hub de domotica (por defecto pensado para
Home Assistant, via su API REST: https://developers.home-assistant.io/docs/api/rest/).

Este modulo es un PLACEHOLDER FUNCIONAL: implementa el flujo real de
llamadas HTTP contra la API configurada en DOMOTICS_API_URL, pero los
nombres de "entity_id" (ej: 'light.living_room') dependen 100% de la
configuracion del hogar del usuario y deben ajustarse en config.json
o pasarse directamente como parametro.

Listo para extender: para sumar otro proveedor (Tuya, Zigbee2MQTT,
SmartThings, etc.) alcanza con reemplazar las funciones internas
_llamar_servicio / _obtener_estado por las de la API correspondiente.
"""

import os
import logging
from typing import Optional

import requests
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("jarvis.domotics")

DOMOTICS_API_URL = os.getenv("DOMOTICS_API_URL", "http://localhost:8123/api").rstrip("/")
DOMOTICS_API_TOKEN = os.getenv("DOMOTICS_API_TOKEN", "")

TIMEOUT_SEGUNDOS = 10


def _headers() -> dict:
    return {
        "Authorization": f"Bearer {DOMOTICS_API_TOKEN}",
        "Content-Type": "application/json",
    }


def _llamar_servicio(dominio: str, servicio: str, entity_id: str) -> bool:
    """Llama a un 'service' generico de Home Assistant sobre una entidad."""
    url = f"{DOMOTICS_API_URL}/services/{dominio}/{servicio}"
    try:
        resp = requests.post(url, json={"entity_id": entity_id}, headers=_headers(), timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        logger.error("Error llamando servicio %s.%s sobre %s: %s", dominio, servicio, entity_id, e)
        return False


def encender_luz(entity_id: str) -> str:
    """Enciende una luz. Ej: entity_id='light.living_room'."""
    ok = _llamar_servicio("light", "turn_on", entity_id)
    return f"Luz '{entity_id}' encendida." if ok else f"No pude encender la luz '{entity_id}'."


def apagar_luz(entity_id: str) -> str:
    """Apaga una luz."""
    ok = _llamar_servicio("light", "turn_off", entity_id)
    return f"Luz '{entity_id}' apagada." if ok else f"No pude apagar la luz '{entity_id}'."


def encender_dispositivo(entity_id: str) -> str:
    """Enciende un enchufe/dispositivo generico (dominio 'switch')."""
    ok = _llamar_servicio("switch", "turn_on", entity_id)
    return f"Dispositivo '{entity_id}' encendido." if ok else f"No pude encender '{entity_id}'."


def apagar_dispositivo(entity_id: str) -> str:
    """Apaga un enchufe/dispositivo generico (dominio 'switch')."""
    ok = _llamar_servicio("switch", "turn_off", entity_id)
    return f"Dispositivo '{entity_id}' apagado." if ok else f"No pude apagar '{entity_id}'."


def ajustar_temperatura(entity_id: str, temperatura: float) -> str:
    """Ajusta la temperatura de un termostato (dominio 'climate')."""
    url = f"{DOMOTICS_API_URL}/services/climate/set_temperature"
    try:
        resp = requests.post(
            url,
            json={"entity_id": entity_id, "temperature": temperatura},
            headers=_headers(),
            timeout=TIMEOUT_SEGUNDOS,
        )
        resp.raise_for_status()
        return f"Temperatura de '{entity_id}' ajustada a {temperatura} grados."
    except requests.exceptions.RequestException as e:
        logger.error("Error ajustando temperatura de %s: %s", entity_id, e)
        return f"No pude ajustar la temperatura de '{entity_id}'."


def obtener_estado_dispositivos(entity_id: Optional[str] = None) -> dict:
    """
    Devuelve el estado de un dispositivo puntual, o de todos los
    dispositivos si no se especifica entity_id.
    """
    url = f"{DOMOTICS_API_URL}/states"
    if entity_id:
        url += f"/{entity_id}"
    try:
        resp = requests.get(url, headers=_headers(), timeout=TIMEOUT_SEGUNDOS)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.RequestException as e:
        logger.error("Error obteniendo estado de domotica (%s): %s", entity_id, e)
        return {"error": str(e)}
