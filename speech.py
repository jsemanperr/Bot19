# -*- coding: utf-8 -*-
"""Captura y transcribe voz del micrófono."""

import os
import tempfile
import wave


def capturar_y_transcribir(duracion: int = 5) -> str | None:
    """Graba el micrófono durante duracion segundos y transcribe con Whisper."""
    import sounddevice as sd
    import transcription

    frecuencia = int(os.getenv("SPEECH_SAMPLE_RATE", "16000"))
    audio = sd.rec(int(duracion * frecuencia), samplerate=frecuencia, channels=1, dtype="int16")
    sd.wait()
    ruta = os.path.join(tempfile.gettempdir(), "kaori_mic.wav")
    with wave.open(ruta, "wb") as archivo:
        archivo.setnchannels(1)
        archivo.setsampwidth(2)
        archivo.setframerate(frecuencia)
        archivo.writeframes(audio.tobytes())
    return transcription.transcribir_audio(ruta)
