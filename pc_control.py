# -*- coding: utf-8 -*-
"""
pc_control.py
==============
Funciones para controlar la PC local (pensado para Windows, ya que
install.ps1 y el flujo general del proyecto asumen ese entorno).

SEGURIDAD: las acciones destructivas (apagar_pc, reiniciar_pc,
cerrar_aplicacion) requieren el parametro 'confirmado=True'. El
command_router.py es responsable de pedir confirmacion explicita al
usuario antes de invocarlas con confirmado=True.
"""

import os
import logging
import subprocess
import platform

import psutil

logger = logging.getLogger("jarvis.pc_control")

ES_WINDOWS = platform.system().lower() == "windows"


def apagar_pc(confirmado: bool = False) -> str:
    """
    Apaga la PC. Requiere confirmacion explicita.
    """
    if not confirmado:
        return "Esta accion apagara la PC. Respondé 'confirmar apagado' para continuar."
    try:
        if ES_WINDOWS:
            subprocess.run(["shutdown", "/s", "/t", "5"], check=True)
        else:
            subprocess.run(["shutdown", "-h", "now"], check=True)
        return "Apagando la PC en unos segundos."
    except Exception as e:
        logger.exception("Error apagando la PC: %s", e)
        return f"No pude apagar la PC: {e}"


def reiniciar_pc(confirmado: bool = False) -> str:
    """
    Reinicia la PC. Requiere confirmacion explicita.
    """
    if not confirmado:
        return "Esta accion reiniciara la PC. Respondé 'confirmar reinicio' para continuar."
    try:
        if ES_WINDOWS:
            subprocess.run(["shutdown", "/r", "/t", "5"], check=True)
        else:
            subprocess.run(["shutdown", "-r", "now"], check=True)
        return "Reiniciando la PC en unos segundos."
    except Exception as e:
        logger.exception("Error reiniciando la PC: %s", e)
        return f"No pude reiniciar la PC: {e}"


def cancelar_apagado() -> str:
    """Cancela un apagado/reinicio programado (por si el usuario se arrepiente)."""
    try:
        if ES_WINDOWS:
            subprocess.run(["shutdown", "/a"], check=True)
        return "Apagado/reinicio cancelado."
    except Exception as e:
        logger.exception("Error cancelando apagado: %s", e)
        return f"No pude cancelar el apagado: {e}"


def abrir_aplicacion(nombre: str) -> str:
    """
    Abre una aplicacion por su nombre de ejecutable o comando conocido
    (ej: 'notepad', 'chrome', 'explorer').
    """
    if not nombre:
        return "Decime que aplicacion queres abrir."
    try:
        if ES_WINDOWS:
            os.startfile(nombre)  # type: ignore[attr-defined]
        else:
            subprocess.Popen([nombre])
        logger.info("Aplicacion abierta: %s", nombre)
        return f"Abriendo {nombre}."
    except FileNotFoundError:
        return f"No encontre la aplicacion '{nombre}'. Verificá el nombre o la ruta."
    except Exception as e:
        logger.exception("Error abriendo aplicacion '%s': %s", nombre, e)
        return f"No pude abrir {nombre}: {e}"


def cerrar_aplicacion(nombre: str, confirmado: bool = False) -> str:
    """
    Cierra (mata) todos los procesos cuyo nombre coincida con 'nombre'.
    Requiere confirmacion explicita por ser una accion potencialmente
    destructiva (puede perderse trabajo no guardado).
    """
    if not nombre:
        return "Decime que aplicacion queres cerrar."
    if not confirmado:
        return f"Esto cerrara todos los procesos de '{nombre}'. Respondé 'confirmar cierre' para continuar."

    cerrados = 0
    try:
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                if nombre.lower() in (proc.info["name"] or "").lower():
                    proc.terminate()
                    cerrados += 1
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        if cerrados:
            return f"Cerré {cerrados} proceso(s) de '{nombre}'."
        return f"No encontre procesos activos de '{nombre}'."
    except Exception as e:
        logger.exception("Error cerrando aplicacion '%s': %s", nombre, e)
        return f"No pude cerrar {nombre}: {e}"


def obtener_estado_sistema() -> dict:
    """
    Devuelve metricas basicas del sistema: uso de CPU, memoria y disco.
    """
    try:
        return {
            "cpu_porcentaje": psutil.cpu_percent(interval=0.5),
            "memoria_porcentaje": psutil.virtual_memory().percent,
            "disco_porcentaje": psutil.disk_usage(os.path.abspath(os.sep)).percent,
            "procesos_activos": len(psutil.pids()),
            "bateria": _obtener_bateria(),
        }
    except Exception as e:
        logger.exception("Error obteniendo estado del sistema: %s", e)
        return {"error": str(e)}


def _obtener_bateria():
    try:
        bateria = psutil.sensors_battery()
        if bateria is None:
            return None
        return {"porcentaje": bateria.percent, "cargando": bateria.power_plugged}
    except Exception:
        return None
