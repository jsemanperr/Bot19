# -*- coding: utf-8 -*-
"""Compatibilidad de TTS Fish Audio para otras integraciones."""

import os
import shutil

import voice


def generar_audio(texto: str, nombre_archivo: str = "kaori.mp3") -> str | None:
    """Genera audio con Fish Audio y copia el resultado al nombre indicado."""
    ruta = voice.sintetizar_texto(texto)
    if not ruta:
        return None
    destino = os.path.abspath(nombre_archivo)
    shutil.copyfile(ruta, destino)
    return destino
