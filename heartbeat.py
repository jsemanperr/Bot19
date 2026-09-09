"""Heartbeat opcional y liviano de JARVIS-LITE."""

import json
import logging
import os
from datetime import datetime, timedelta

from apscheduler.schedulers.background import BackgroundScheduler
from dotenv import load_dotenv

import memory
from neurochemistry import estado_global

load_dotenv()
logger = logging.getLogger("jarvis-lite.heartbeat")
INTERVALO_MINUTOS = int(os.getenv("HEARTBEAT_INTERVALO_MINUTOS", "30"))
_scheduler = None
_RUTA_EVENTO = os.path.join(os.path.dirname(__file__), "data", "ultimo_evento_hud.json")


def _notificar_hud(evento: dict) -> None:
    os.makedirs(os.path.dirname(_RUTA_EVENTO), exist_ok=True)
    with open(_RUTA_EVENTO, "w", encoding="utf-8") as archivo:
        json.dump(evento, archivo, ensure_ascii=False, indent=2)


def check_in() -> None:
    """Actualiza el estado y deja un evento para el HUD si hubo inactividad."""
    estado_global.decaimiento_temporal(INTERVALO_MINUTOS)
    ultima = memory.obtener_ultima_interaccion()
    inactivo = ultima is None or (datetime.utcnow() - ultima).total_seconds() >= INTERVALO_MINUTOS * 60
    if inactivo:
        _notificar_hud({
            "timestamp": datetime.utcnow().isoformat(),
            "estado_animo": estado_global.to_dict(),
            "mensaje_proactivo": "Hola, soy Kaori. ¿Hay algo en lo que pueda ayudarte?",
        })


def iniciar_heartbeat() -> BackgroundScheduler:
    global _scheduler
    if _scheduler is not None:
        return _scheduler
    _scheduler = BackgroundScheduler(timezone="UTC")
    _scheduler.add_job(
        check_in,
        "interval",
        minutes=max(1, INTERVALO_MINUTOS),
        next_run_time=datetime.utcnow() + timedelta(minutes=max(1, INTERVALO_MINUTOS)),
    )
    _scheduler.start()
    return _scheduler


def detener_heartbeat() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
