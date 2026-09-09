# -*- coding: utf-8 -*-
"""
skills/multi_llm.py
=====================
Capa de abstracción para elegir y consultar distintos modelos de lenguaje
(LLM). Por defecto Kaori usa Ollama en local (modelo liviano y gratis),
pero para tareas de mayor complejidad puede usar un modelo más grande
en la nube (DeepSeek), si hay una DEEPSEEK_API_KEY configurada.

Variables de entorno usadas:
- DEFAULT_LLM: "ollama" o "deepseek" (default: "ollama").
- OLLAMA_URL / OLLAMA_MODEL: configuración del servidor Ollama local.
- DEEPSEEK_API_KEY: API key de DeepSeek (si está vacía, siempre se usa Ollama).
- DEEPSEEK_MODEL: nombre del modelo de DeepSeek a usar (default: "deepseek-chat").
"""

import os
import time
import logging
from typing import List, Dict, Optional

import requests
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("jarvis.skills.multi_llm")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "120"))

DEEPSEEK_API_URL = os.getenv("DEEPSEEK_API_URL", "https://api.deepseek.com/v1/chat/completions")
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "").strip()
DEEPSEEK_MODEL = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")

DEFAULT_LLM = os.getenv("DEFAULT_LLM", "ollama").strip().lower()

TIMEOUT_SEGUNDOS = 120
MAX_REINTENTOS = 3


def seleccionar_modelo(complejidad: str = "media") -> str:
    """
    Elige que modelo usar según la complejidad estimada de la tarea.

    :param complejidad: "baja", "media" o "alta".
    :return: "ollama" o "deepseek".
    """
    complejidad = (complejidad or "media").strip().lower()

    if complejidad == "alta" and DEEPSEEK_API_KEY:
        return "deepseek"

    # Sin API key de DeepSeek, o complejidad baja/media: siempre Ollama (local y gratis).
    return "ollama"


def _consultar_ollama(mensajes: List[Dict[str, str]], timeout: int) -> str:
    """Consulta el modelo local de Ollama, con reintentos y backoff exponencial."""
    payload = {
        "model": OLLAMA_MODEL,
        "messages": mensajes,
        "stream": False,
        "keep_alive": OLLAMA_KEEP_ALIVE,
        "options": {
            "temperature": 0.35,
            "num_predict": OLLAMA_NUM_PREDICT,
        },
    }

    for intento in range(MAX_REINTENTOS):
        try:
            logger.debug("Intento %s/%s consultando Ollama", intento + 1, MAX_REINTENTOS)
            resp = requests.post(f"{OLLAMA_URL}/api/chat", json=payload, timeout=timeout)
            resp.raise_for_status()
            data = resp.json()
            resultado = data.get("message", {}).get("content", "").strip()
            if resultado:
                return resultado
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
            if intento < MAX_REINTENTOS - 1:
                espera = 2 ** intento  # 1s, 2s, 4s
                logger.warning("Timeout en Ollama (intento %s), reintentando en %ss: %s", intento + 1, espera, e)
                time.sleep(espera)
                continue
            logger.error("Error conectando con Ollama (agotados reintentos): %s", e)
            return "No pude conectarme con Ollama. Verificá que esté corriendo: ollama serve"
        except requests.exceptions.HTTPError as e:
            logger.error("Error HTTP de Ollama: %s", e)
            return "Ollama respondió con un error. Verificá la configuración."
        except Exception as e:
            logger.exception("Error inesperado consultando Ollama: %s", e)
            return "Ocurrió un error inesperado procesando tu mensaje."

    return "No pude procesar tu solicitud (respuesta vacía de Ollama)."


def _consultar_deepseek(mensajes: List[Dict[str, str]], timeout: int) -> str:
    """Consulta la API de DeepSeek (formato compatible con OpenAI chat completions)."""
    if not DEEPSEEK_API_KEY:
        logger.warning("Se pidió DeepSeek pero no hay DEEPSEEK_API_KEY configurada, se usa Ollama.")
        return _consultar_ollama(mensajes, timeout)

    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": DEEPSEEK_MODEL,
        "messages": mensajes,
        "stream": False,
    }

    try:
        resp = requests.post(DEEPSEEK_API_URL, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as e:
        logger.error("Error conectando con DeepSeek: %s", e)
        return "No pude conectarme con DeepSeek. Reviso Ollama como respaldo..." + "\n" + _consultar_ollama(mensajes, timeout)
    except requests.exceptions.HTTPError as e:
        logger.error("Error HTTP de DeepSeek: %s", e)
        return "DeepSeek respondió con un error. Verificá la DEEPSEEK_API_KEY y el modelo configurado."
    except Exception as e:
        logger.exception("Error inesperado consultando DeepSeek: %s", e)
        return "Ocurrió un error inesperado consultando DeepSeek."


def consultar_llm(mensajes: List[Dict[str, str]], modelo: Optional[str] = None, timeout: int = TIMEOUT_SEGUNDOS) -> str:
    """
    Envía una lista de mensajes (formato chat: [{"role": ..., "content": ...}])
    al modelo seleccionado y devuelve el texto de la respuesta.

    :param mensajes: historial de mensajes en formato chat.
    :param modelo: "ollama" o "deepseek". Si es None, se usa DEFAULT_LLM del .env.
    :param timeout: tiempo máximo de espera en segundos.
    """
    modelo = (modelo or DEFAULT_LLM or "ollama").strip().lower()

    if modelo == "deepseek":
        return _consultar_deepseek(mensajes, timeout)
    return _consultar_ollama(mensajes, timeout)
