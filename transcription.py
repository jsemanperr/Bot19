# -*- coding: utf-8 -*-
"""Transcripcion local de notas de voz con faster-whisper."""

import logging
import os
from functools import lru_cache

logger = logging.getLogger("jarvis.transcription")


@lru_cache(maxsize=1)
def _modelo():
    from faster_whisper import WhisperModel

    return WhisperModel(
        os.getenv("WHISPER_MODEL", "tiny"),
        device=os.getenv("WHISPER_DEVICE", "cpu"),
        compute_type=os.getenv("WHISPER_COMPUTE_TYPE", "int8"),
    )


def transcribir_audio(ruta: str) -> str | None:
    """Transcribe un archivo de audio y devuelve texto, o None si falla."""
    if not os.path.isfile(ruta):
        logger.error("Archivo de audio no encontrado: %s", ruta)
        return None
    
    # Validar que el archivo no esté vacío
    if os.path.getsize(ruta) < 100:
        logger.warning("Archivo de audio muy pequeño o vacío: %s", ruta)
        return None
    
    try:
        segmentos, _ = _modelo().transcribe(
            ruta,
            language=os.getenv("WHISPER_LANGUAGE", "es"),
            vad_filter=True,
        )
        texto = " ".join(segmento.text.strip() for segmento in segmentos).strip()
        if texto:
            logger.info("Audio transcrito correctamente: %s", ruta)
            return texto
        logger.warning("Transcripción vacía del audio: %s", ruta)
        return None
    except Exception as e:
        logger.warning("No se pudo transcribir el audio: %s - Error: %s", ruta, type(e).__name__)
        # No spam de excepciones completas, solo el tipo de error
        return None
