# -*- coding: utf-8 -*-
"""
skills/discord_bot.py
========================
Bot de Discord para JARVIS/Kaori. Escucha mensajes en los canales donde
tenga permisos y responde usando el mismo cerebro que WhatsApp: 
command_router.procesar_comando.

Requiere:
- discord.py (ya instalado)
- DISCORD_ENABLED=true en el .env
- DISCORD_BOT_TOKEN=<token del bot creado en Discord Developer Portal> en el .env

El bot corre en su propio hilo con su propio event loop asíncrono, para
no bloquear el servidor FastAPI principal.

IMPORTANTE: en el Discord Developer Portal, dentro de "Bot", hay que
habilitar el "Message Content Intent" para que el bot pueda leer el
contenido de los mensajes de texto.
"""

import os
import logging

from dotenv import load_dotenv

try:
    import discord
    HAS_DISCORD = True
except ImportError:
    HAS_DISCORD = False

import command_router

load_dotenv()
logger = logging.getLogger("jarvis.skills.discord_bot")

DISCORD_ENABLED = os.getenv("DISCORD_ENABLED", "false").lower() == "true"
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "").strip()


def _crear_cliente():
    """Crea el cliente de Discord con los intents necesarios para leer mensajes."""
    intents = discord.Intents.default()
    intents.message_content = True  # Necesario para leer el texto de los mensajes.

    cliente = discord.Client(intents=intents)

    @cliente.event
    async def on_ready():
        logger.info("Bot de Discord conectado como %s", cliente.user)

    @cliente.event
    async def on_message(mensaje):
        # Evita que el bot se responda a sí mismo (bucle infinito).
        if mensaje.author == cliente.user:
            return

        texto = (mensaje.content or "").strip()
        if not texto:
            return

        try:
            # Se usa el ID del canal + autor como identificador de remitente,
            # para que la memoria/contexto se maneje por usuario/canal.
            remitente = f"discord:{mensaje.author.id}"

            respuesta = command_router.procesar_comando(texto, remitente)
            await mensaje.channel.send(respuesta)

        except Exception as e:
            logger.exception("Error procesando mensaje de Discord: %s", e)
            try:
                await mensaje.channel.send(
                    "Tuve un problema procesando tu mensaje, Jefe. Ya quedó registrado el error."
                )
            except Exception:
                pass

    return cliente


def iniciar_bot_discord() -> None:
    """
    Inicializa y arranca el bot de Discord.

    Esta función es bloqueante (corre su propio event loop asíncrono internamente
    mediante cliente.run), por lo que debe ejecutarse dentro de un hilo separado
    (ver server.py).
    """
    if not HAS_DISCORD:
        logger.error("La librería 'discord.py' no está instalada. No se puede iniciar el bot de Discord.")
        return

    if not DISCORD_ENABLED:
        logger.info("Discord deshabilitado (DISCORD_ENABLED=false). No se inicia el bot.")
        return

    if not DISCORD_BOT_TOKEN:
        logger.error("Falta DISCORD_BOT_TOKEN en el .env. No se puede iniciar el bot de Discord.")
        return

    try:
        cliente = _crear_cliente()
        logger.info("Bot de Discord iniciado, escuchando mensajes...")
        # cliente.run crea y gestiona su propio event loop asíncrono; al correr
        # en un hilo dedicado no interfiere con el loop de FastAPI/uvicorn.
        cliente.run(DISCORD_BOT_TOKEN, log_handler=None)

    except Exception as e:
        logger.exception("Error iniciando el bot de Discord: %s", e)
