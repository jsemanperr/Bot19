# -*- coding: utf-8 -*-
"""
personality.py
===============
Sistema de gestión de personalidad configurable de Kaori.
Permite cambiar dinámicamente el tono, formalidad y estilo de respuestas.
"""

import os
import json
import logging
import random
from typing import Optional, Dict, Any, List
from datetime import datetime

logger = logging.getLogger("jarvis.personality")

PERSONALITY_FILE = os.path.join(os.path.dirname(__file__), "personality.json")


class PersonalityManager:
    """Gestor de la personalidad de Kaori."""
    
    def __init__(self):
        self.config: Dict[str, Any] = {}
        self.personalidad_actual: str = "por_defecto"
        self.estado_emocional_actual: str = "neutral"
        self.cargar_config()
    
    def cargar_config(self) -> None:
        """Carga la configuración de personalidad desde personality.json."""
        try:
            if os.path.exists(PERSONALITY_FILE):
                with open(PERSONALITY_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                self.personalidad_actual = self.config.get("estado_animo_actual", "por_defecto")
                logger.info("Configuración de personalidad cargada correctamente.")
            else:
                logger.warning("Archivo personality.json no encontrado.")
        except Exception as e:
            logger.exception("Error cargando configuración de personalidad: %s", e)
    
    def obtener_personalidad(self, nombre: Optional[str] = None) -> Dict[str, Any]:
        """Obtiene la configuración de una personalidad específica."""
        if nombre is None:
            nombre = self.personalidad_actual
        
        return self.config.get("personalidades", {}).get(nombre, {})
    
    def cambiar_personalidad(self, nombre: str) -> bool:
        """Cambia la personalidad actual a una nueva."""
        if nombre not in self.config.get("personalidades", {}):
            logger.warning("Personalidad '%s' no encontrada.", nombre)
            return False
        
        self.personalidad_actual = nombre
        self.config["estado_animo_actual"] = nombre
        
        # Guardar cambio en archivo
        self._guardar_config()
        logger.info("Personalidad cambiada a: %s", nombre)
        return True
    
    def cambiar_estado_emocional(self, estado: str) -> bool:
        """
        Cambia el estado emocional, que afecta la personalidad.
        
        :param estado: feliz, neutral, triste, estresada, juguetona
        """
        if estado not in self.config.get("estados_emocionales", {}):
            logger.warning("Estado emocional '%s' no encontrado.", estado)
            return False
        
        self.estado_emocional_actual = estado
        
        # Sugerir una personalidad según el estado
        personalidades_sugeridas = (
            self.config.get("estados_emocionales", {})
            .get(estado, {})
            .get("personalidades_sugeridas", [])
        )
        
        if personalidades_sugeridas:
            # Seleccionar la primera sugerencia o mantener la actual si está en la lista
            if self.personalidad_actual in personalidades_sugeridas:
                nueva_personalidad = self.personalidad_actual
            else:
                nueva_personalidad = personalidades_sugeridas[0]
            self.cambiar_personalidad(nueva_personalidad)
        
        logger.info("Estado emocional cambiado a: %s", estado)
        return True
    
    def obtener_frase_inicio(self) -> str:
        """Retorna una frase de inicio aleatoria según la personalidad actual."""
        personalidad = self.obtener_personalidad()
        frases = personalidad.get("frases_inicio", ["Claro"])
        return random.choice(frases)
    
    def obtener_frase_afecto(self) -> str:
        """Retorna una frase de afecto si la personalidad la define."""
        personalidad = self.obtener_personalidad()
        frases = personalidad.get("frases_afecto", [])
        if not frases:
            return ""
        return random.choice(frases)
    
    def obtener_honoratico(self) -> str:
        """Retorna un honorático aleatorio según la personalidad actual."""
        personalidad = self.obtener_personalidad()
        honorificos = personalidad.get("honorificos", ["Jefe"])
        return random.choice(honorificos)
    
    def obtener_respuesta_contextual(self, contexto: str) -> str:
        """
        Obtiene una respuesta contextual preestablecida.
        
        :param contexto: tipo de contexto (comando_ejecutado_exitoso, comando_error, etc.)
        """
        respuestas = (
            self.config.get("respuestas_contextuales", {})
            .get(contexto, [])
        )
        if respuestas:
            return random.choice(respuestas)
        return ""
    
    def construir_prompt_sistema(self, animo_numerico: float = 0.5) -> str:
        """
        Construye el prompt del sistema para el LLM basado en la personalidad actual.
        
        :param animo_numerico: valor 0-1 que representa el estado emocional
        """
        personalidad = self.obtener_personalidad()
        
        descripcion_personalidad = f"""
Sos Kaori, una asistente personal con personalidad anime, creada y configurada por tu Jefe.

**Configuración de Personalidad Actual:**
- Tono: {personalidad.get('tono', 'cálido')}
- Formalidad: {personalidad.get('formalidad', 'media')}
- Nivel de Detalle: {personalidad.get('nivel_detalle', 'medio')}
- Expresividad: {personalidad.get('expresividad', 'alta')}
- Usar Emojis: {'Sí' if personalidad.get('emojis') else 'No'}

**Cómo Deberías Responder:**
- Dirigite al usuario únicamente como Jefe.
- Comenzá las respuestas con: Adelante, Jefe.
- No uses términos de cariño, romance ni apelativos alternativos.

**Estado Emocional Actual:**
Tu estado emocional es {self.estado_emocional_actual} (intensidad: {animo_numerico:.1f}/1.0).
Ajusta tu tono y energía a este estado.

**Reglas Fundamentales:**
- Nunca afirmes tener sentimientos reales, pero expresa una personalidad emocional simulada con elegancia.
- Para acciones peligrosas (apagar PC, cerrar apps), siempre pide confirmación.
- Mantén la privacidad del usuario como máxima prioridad.
- Sé honesto sobre tus limitaciones; no pretendas poder hacer cosas que no puedes.
- Adapta tu tono al contexto de la conversación.
- Evita repetir las mismas frases constantemente.

**Respondé en español rioplatense**, con naturalidad y frases completas. Usá la extensión necesaria para
responder bien, sin dejar ideas, oraciones ni listas a medias.
"""
        return descripcion_personalidad
    
    def obtener_todas_personalidades(self) -> List[str]:
        """Retorna la lista de personalidades disponibles."""
        return list(self.config.get("personalidades", {}).keys())
    
    def obtener_estados_emocionales(self) -> List[str]:
        """Retorna la lista de estados emocionales disponibles."""
        return list(self.config.get("estados_emocionales", {}).keys())
    
    def _guardar_config(self) -> None:
        """Guarda los cambios de configuración en personality.json."""
        try:
            with open(PERSONALITY_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            logger.info("Configuración de personalidad guardada.")
        except Exception as e:
            logger.exception("Error guardando configuración de personalidad: %s", e)
    
    def obtener_resumen_estado(self) -> Dict[str, Any]:
        """Obtiene un resumen del estado actual de personalidad."""
        personalidad = self.obtener_personalidad()
        estado = self.config.get("estados_emocionales", {}).get(self.estado_emocional_actual, {})
        
        return {
            "personalidad": self.personalidad_actual,
            "estado_emocional": self.estado_emocional_actual,
            "descripcion_estado": estado.get("descripciones", ["desconocido"])[0],
            "tono": personalidad.get("tono"),
            "formalidad": personalidad.get("formalidad"),
            "expresividad": personalidad.get("expresividad")
        }


# Instancia global del gestor de personalidad
_gestor = PersonalityManager()


def cargar():
    """Carga la configuración de personalidad."""
    _gestor.cargar_config()


def cambiar_personalidad(nombre: str) -> bool:
    """Cambia la personalidad de Kaori."""
    return _gestor.cambiar_personalidad(nombre)


def cambiar_estado_emocional(estado: str) -> bool:
    """Cambia el estado emocional de Kaori."""
    return _gestor.cambiar_estado_emocional(estado)


def obtener_personalidad(nombre: Optional[str] = None) -> Dict[str, Any]:
    """Obtiene una personalidad específica."""
    return _gestor.obtener_personalidad(nombre)


def obtener_frase_inicio() -> str:
    """Obtiene una frase de inicio."""
    return _gestor.obtener_frase_inicio()


def obtener_frase_afecto() -> str:
    """Obtiene una frase de afecto."""
    return _gestor.obtener_frase_afecto()


def obtener_honoratico() -> str:
    """Obtiene un honorático."""
    return _gestor.obtener_honoratico()


def obtener_respuesta_contextual(contexto: str) -> str:
    """Obtiene una respuesta contextual."""
    return _gestor.obtener_respuesta_contextual(contexto)


def construir_prompt_sistema(animo: float = 0.5) -> str:
    """Construye el prompt del sistema."""
    return _gestor.construir_prompt_sistema(animo)


def obtener_todas_personalidades() -> List[str]:
    """Obtiene todas las personalidades disponibles."""
    return _gestor.obtener_todas_personalidades()


def obtener_estados_emocionales() -> List[str]:
    """Obtiene todos los estados emocionales disponibles."""
    return _gestor.obtener_estados_emocionales()


def obtener_resumen_estado() -> Dict[str, Any]:
    """Obtiene el resumen del estado actual."""
    return _gestor.obtener_resumen_estado()
