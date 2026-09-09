# -*- coding: utf-8 -*-
"""Escucha opcional de la palabra clave Kaori."""

import logging
import os
import queue
import threading

logger = logging.getLogger("jarvis.wakeword")
detection_queue: queue.Queue[str] = queue.Queue()


def iniciar_escucha() -> threading.Thread | None:
    """Inicia Porcupine solo si está configurado y devuelve su hilo."""
    if os.getenv("VOICE_ALWAYS_LISTEN", "false").lower() != "true":
        logger.info("Escucha continua desactivada (VOICE_ALWAYS_LISTEN=false).")
        return None
    access_key = os.getenv("PICOVOICE_ACCESS_KEY", "")
    if not access_key or access_key == "cambia_esto":
        logger.warning("Escucha continua omitida: falta configurar PICOVOICE_ACCESS_KEY en .env.")
        return None

    def escuchar() -> None:
        import pvporcupine
        import sounddevice as sd

        keyword_path = os.getenv("PICOVOICE_KEYWORD_PATH", "")
        if keyword_path:
            porcupine = pvporcupine.create(
                access_key=os.environ["PICOVOICE_ACCESS_KEY"],
                keyword_paths=[keyword_path],
            )
        else:
            porcupine = pvporcupine.create(
                access_key=os.environ["PICOVOICE_ACCESS_KEY"],
                keywords=["porcupine"],
            )
        try:
            with sd.RawInputStream(
                samplerate=porcupine.sample_rate,
                blocksize=porcupine.frame_length,
                dtype="int16",
                channels=1,
            ) as stream:
                while True:
                    frame, _ = stream.read(porcupine.frame_length)
                    if porcupine.process(frame) >= 0:
                        detection_queue.put("kaori")
        finally:
            porcupine.delete()

    hilo = threading.Thread(target=escuchar, name="kaori-wakeword", daemon=True)
    hilo.start()
    return hilo
