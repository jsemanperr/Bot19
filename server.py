"""Servidor FastAPI mínimo de JARVIS-LITE."""

import asyncio
import logging
import os
import threading
from datetime import datetime

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse

import command_router
import heartbeat
import memory
from neurochemistry import estado_global
from skills import spotify_skill
from skills.discord_bot import iniciar_bot_discord
from skills.telegram_bot import iniciar_bot_telegram

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("jarvis-lite.server")
app = FastAPI(title="JARVIS-LITE")
inicio = datetime.utcnow()


@app.get("/health")
async def health():
    return {"ok": True, "status": "JARVIS-LITE listo"}


@app.get("/status")
async def status():
    ultima = memory.obtener_ultima_interaccion()
    return {
        "ok": True,
        "estado_animo": estado_global.to_dict(),
        "ultima_interaccion": ultima.isoformat() if ultima else None,
        "uptime_segundos": (datetime.utcnow() - inicio).total_seconds(),
    }


@app.post("/command")
async def command(texto: str = Form(...), remitente: str = Form("local")):
    try:
        respuesta = await asyncio.to_thread(command_router.procesar_comando, texto, remitente)
        return {"ok": True, "respuesta": respuesta}
    except Exception as error:
        logger.exception("Error procesando comando")
        raise HTTPException(status_code=500, detail="Error interno procesando el comando.") from error


@app.get("/memory")
async def get_memory(consulta: str = "", remitente: str = "", limite: int = 20):
    if consulta:
        return {"ok": True, "modo": "busqueda", "resultado": memory.buscar_contexto(consulta, limite=limite)}
    return {"ok": True, "modo": "historial", "resultado": memory.obtener_historial(remitente or None, limite)}


@app.get("/spotify/login")
async def spotify_login():
    url = spotify_skill.url_autorizacion()
    return RedirectResponse(url) if url.startswith("http") else HTMLResponse(url, status_code=500)


@app.get("/spotify/callback")
async def spotify_callback(code: str = "", error: str = ""):
    if error:
        return HTMLResponse(f"Spotify rechazó la autorización: {error}", status_code=400)
    if not code:
        return HTMLResponse("Falta el parámetro code.", status_code=400)
    spotify_skill.completar_autorizacion(code)
    return HTMLResponse("Spotify autorizado. Ya podés cerrar esta ventana.")


@app.on_event("startup")
def startup():
    memory.init_db()
    heartbeat.iniciar_heartbeat()
    if os.getenv("TELEGRAM_ENABLED", "false").lower() == "true":
        threading.Thread(target=iniciar_bot_telegram, daemon=True, name="telegram-bot").start()
    if os.getenv("DISCORD_ENABLED", "false").lower() == "true":
        threading.Thread(target=iniciar_bot_discord, daemon=True, name="discord-bot").start()


@app.on_event("shutdown")
def shutdown():
    heartbeat.detener_heartbeat()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host=os.getenv("JARVIS_HOST", "127.0.0.1"), port=int(os.getenv("JARVIS_PORT", "8000")))
