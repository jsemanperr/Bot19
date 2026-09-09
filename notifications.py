# -*- coding: utf-8 -*-
"""Canales de notificación de Kaori."""

import os
import logging

import requests
from dotenv import load_dotenv

import whatsapp_bridge
import telegram_bridge

load_dotenv()
logger = logging.getLogger("jarvis.notifications")


def enviar_whatsapp(mensaje: str) -> bool:
    numero = os.getenv("USER_WHATSAPP_NUMBER", "")
    return bool(numero and whatsapp_bridge.enviar_mensaje_texto(numero, mensaje))


def enviar_telegram(mensaje: str) -> bool:
    return telegram_bridge.enviar_texto(mensaje)


def enviar_discord(mensaje: str) -> bool:
    webhook = os.getenv("DISCORD_WEBHOOK_URL", "")
    if not webhook:
        return False
    try:
        response = requests.post(webhook, json={"content": mensaje}, timeout=15)
        response.raise_for_status()
        return True
    except requests.RequestException as error:
        logger.warning("Discord no disponible: %s", error)
        return False


def enviar_todos(mensaje: str) -> dict[str, bool]:
    """Envía por canales configurados; WhatsApp es el canal principal."""
    return {
        "whatsapp": enviar_whatsapp(mensaje),
        "telegram": enviar_telegram(mensaje),
        "discord": enviar_discord(mensaje),
    }
