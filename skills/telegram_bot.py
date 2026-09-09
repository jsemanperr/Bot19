# -*- coding: utf-8 -*-
"""
skills/telegram_bot.py
========================
Bot de Telegram para JARVIS/Kaori. Escucha mensajes de texto y responde
usando el mismo cerebro que WhatsApp: command_router.procesar_comando.

Requiere:
- python-telegram-bot (ya instalado)
- TELEGRAM_ENABLED=true en el .env
- TELEGRAM_BOT_TOKEN=<token de @BotFather> en el .env

El bot corre en su propio hilo con su propio event loop asíncrono, para
no bloquear el servidor FastAPI principal.
"""

import os
import logging
import asyncio

from dotenv import load_dotenv

try:
    from telegram import Update
    from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False

import command_router

load_dotenv()
logger = logging.getLogger("jarvis.skills.telegram_bot")

TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()


async def _manejar_mensaje(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Recibe un mensaje de texto de Telegram y lo procesa con el router central."""
    try:
        texto = update.message.text if update.message else None
        if not texto:
            return

        # Se usa el ID de chat de Telegram como identificador de remitente,
        # para que la memoria/contexto se maneje por usuario.
        remitente = f"telegram:{update.effective_chat.id}"

        respuesta = await asyncio.to_thread(command_router.procesar_comando, texto, remitente)
        await update.message.reply_text(respuesta)

    except Exception as e:
        logger.exception("Error procesando mensaje de Telegram: %s", e)
        try:
            await update.message.reply_text("Tuve un problema procesando tu mensaje, Jefe. Ya quedó registrado el error.")
        except Exception:
            pass


async def _comando_start(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Responde al comando /start de Telegram con un saludo de bienvenida."""
    await update.message.reply_text(
        "¡Hola, Jefe! Soy Kaori 💫. Ya estoy conectada por Telegram, escribime lo que necesites."
    )


def iniciar_bot_telegram() -> None:
    """
    Inicializa y arranca el bot de Telegram en modo polling.

    Esta función es bloqueante (corre su propio event loop asíncrono internamente),
    por lo que debe ejecutarse dentro de un hilo separado (ver server.py).
    """
    if not HAS_TELEGRAM:
        logger.error("La librería 'python-telegram-bot' no está instalada. No se puede iniciar el bot de Telegram.")
        return

    if not TELEGRAM_ENABLED:
        logger.info("Telegram deshabilitado (TELEGRAM_ENABLED=false). No se inicia el bot.")
        return

    if not TELEGRAM_BOT_TOKEN:
        logger.error("Falta TELEGRAM_BOT_TOKEN en el .env. No se puede iniciar el bot de Telegram.")
        return

    try:
        aplicacion = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

        aplicacion.add_handler(CommandHandler("start", _comando_start))
        aplicacion.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _manejar_mensaje))

        logger.info("Bot de Telegram iniciado, escuchando mensajes...")
        # run_polling gestiona su propio loop asíncrono; al correr en un hilo
        # dedicado no interfiere con el loop de FastAPI/uvicorn.
        aplicacion.run_polling(close_loop=False, stop_signals=None)

    except Exception as e:
        logger.exception("Error iniciando el bot de Telegram: %s", e)
