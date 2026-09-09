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
from contextlib import suppress

from dotenv import load_dotenv

try:
    from telegram import Update
    from telegram.error import Conflict
    from telegram.ext import Application, MessageHandler, CommandHandler, ContextTypes, filters
    HAS_TELEGRAM = True
except ImportError:
    HAS_TELEGRAM = False
    Conflict = Exception

import command_router
import voice

load_dotenv()
logger = logging.getLogger("jarvis.skills.telegram_bot")

TELEGRAM_ENABLED = os.getenv("TELEGRAM_ENABLED", "false").lower() == "true"
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
TELEGRAM_AUDIO_ENABLED = os.getenv("TELEGRAM_AUDIO_ENABLED", "false").lower() == "true"
TELEGRAM_AUDIO_MAX_CHARS = int(os.getenv("TELEGRAM_AUDIO_MAX_CHARS", "700"))
_TELEGRAM_THREAD_STARTED = False


def _limpiar_markdown(texto: str) -> str:
    """Telegram muestra Markdown, pero el texto enviado a TTS debe ser limpio."""
    return texto.replace("*", "").replace("`", "").replace("_", "")


async def _enviar_respuesta(update: "Update", respuesta: str) -> None:
    if not update.message:
        return
    # Las respuestas de APIs pueden contener caracteres reservados de Markdown.
    await update.message.reply_text(respuesta)
    if not TELEGRAM_AUDIO_ENABLED:
        logger.info("Audio de Telegram desactivado: establece TELEGRAM_AUDIO_ENABLED=true.")
        return

    texto_audio = _limpiar_markdown(respuesta)
    if len(texto_audio) > TELEGRAM_AUDIO_MAX_CHARS:
        texto_audio = texto_audio[:TELEGRAM_AUDIO_MAX_CHARS].rsplit(" ", 1)[0] + "."
    try:
        ruta_audio = await asyncio.to_thread(voice.sintetizar_texto, texto_audio)
        if ruta_audio:
            try:
                with open(ruta_audio, "rb") as archivo:
                    # Fish Audio entrega MP3; Telegram debe recibirlo como audio.
                    await update.message.reply_audio(audio=archivo, caption="🔊 También te lo dejo en audio.")
            finally:
                with suppress(OSError):
                    os.remove(ruta_audio)
        else:
            logger.warning("No se generó audio. Revisa FISH_AUDIO_API_KEY y FISH_AUDIO_VOICE_ID en Railway.")
    except Exception:
        logger.exception("No se pudo generar o enviar el audio de Telegram")


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
        await _enviar_respuesta(update, respuesta)

    except Exception as e:
        logger.exception("Error procesando mensaje de Telegram: %s", e)
        try:
            await update.message.reply_text("Tuve un problema procesando tu mensaje, Jefe. Ya quedó registrado el error.")
        except Exception:
            pass


async def _comando_start(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Responde al comando /start de Telegram con un saludo de bienvenida."""
    await _enviar_respuesta(
        update,
        "¡Hola, Jefe! Soy Kaori 💫\n\n"
        "Estoy lista. Escribime lo que quieras en lenguaje normal o usa /menu para ver ejemplos.",
    )


async def _comando_menu(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    await _enviar_respuesta(update, command_router.MENU_AYUDA)


async def _comando_clima(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    ciudad = " ".join(context.args).strip()
    await _enviar_respuesta(update, command_router.procesar_comando(f"clima en {ciudad}" if ciudad else "clima", f"telegram:{update.effective_chat.id}"))


async def _comando_receta(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    consulta = " ".join(context.args).strip()
    comando = f"receta de {consulta}" if consulta else "receta aleatoria"
    await _enviar_respuesta(update, command_router.procesar_comando(comando, f"telegram:{update.effective_chat.id}"))


async def _comando_voz(update: "Update", context: "ContextTypes.DEFAULT_TYPE") -> None:
    estado = "activado" if TELEGRAM_AUDIO_ENABLED else "desactivado en este despliegue"
    await update.message.reply_text(f"🔊 El audio está {estado}. Usa texto normal para ejecutar cualquier comando.")


async def _manejar_error(update: object, context: "ContextTypes.DEFAULT_TYPE") -> None:
    """Registra errores de handlers sin exponer tokens ni trazas innecesarias."""
    error = context.error
    if isinstance(error, Conflict):
        logger.error(
            "Telegram 409 Conflict: hay otra instancia usando este bot. "
            "Detén el bot local/otro Railway antes de volver a desplegar."
        )
        return
    logger.error("Error no controlado del bot de Telegram: %s", error)


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

    global _TELEGRAM_THREAD_STARTED
    if _TELEGRAM_THREAD_STARTED:
        logger.warning("El bot de Telegram ya fue iniciado en este proceso; se evita una segunda instancia.")
        return
    _TELEGRAM_THREAD_STARTED = True

    try:
        async def configurar_menu() -> None:
            await aplicacion.bot.set_my_commands([
                ("start", "Iniciar Kaori"),
                ("menu", "Ver todo lo que puedo hacer"),
                ("clima", "Consultar el clima"),
                ("receta", "Receta aleatoria o por ingrediente"),
                ("voz", "Consultar el estado del audio"),
                ("help", "Ayuda rápida"),
            ])

        aplicacion = Application.builder().token(TELEGRAM_BOT_TOKEN).post_init(configurar_menu).build()
        aplicacion.add_handler(CommandHandler("start", _comando_start))
        aplicacion.add_handler(CommandHandler(["help", "ayuda", "menu"], _comando_menu))
        aplicacion.add_handler(CommandHandler("clima", _comando_clima))
        aplicacion.add_handler(CommandHandler(["receta", "cocina"], _comando_receta))
        aplicacion.add_handler(CommandHandler("voz", _comando_voz))
        aplicacion.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, _manejar_mensaje))
        aplicacion.add_error_handler(_manejar_error)

        logger.info("Bot de Telegram iniciado, escuchando mensajes...")
        # run_polling gestiona su propio loop asíncrono; al correr en un hilo
        # dedicado no interfiere con el loop de FastAPI/uvicorn.
        aplicacion.run_polling(close_loop=False, stop_signals=None)

    except Conflict:
        logger.error(
            "Telegram rechazó el polling (409 Conflict). "
            "Solo una instancia puede usar getUpdates; se detiene este bot."
        )
    except Exception:
        logger.exception("Error iniciando el bot de Telegram")
