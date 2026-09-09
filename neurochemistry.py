# -*- coding: utf-8 -*-
"""
neurochemistry.py
==================
Simula de forma simple un "estado de animo" para JARVIS, basado en
cuatro variables inspiradas en neurotransmisores (todas en escala 0-100):

- dopamina: motivacion / recompensa (sube con logros, tareas completadas).
- serotonina: bienestar general / estabilidad (sube con rutina, interaccion positiva).
- cortisol: estres (sube con errores, urgencias, silencio prolongado del usuario).
- oxitocina: vinculo social (sube con interacciones calidas con el usuario).

Esto es una capa cosmetica/heuristica para dar personalidad a las
respuestas y al heartbeat, no un modelo cientifico.
"""

import logging
from datetime import datetime
from typing import Dict

import memory

logger = logging.getLogger("jarvis.neurochemistry")


class EstadoNeuroquimico:
    """
    Representa y actualiza el estado emocional simulado de JARVIS.
    El estado se persiste en la tabla 'estado_animo' de memory.py.
    """

    LIMITE_MIN = 0
    LIMITE_MAX = 100

    # Como afecta cada tipo de evento a cada variable (delta).
    EVENTOS: Dict[str, Dict[str, float]] = {
        "tarea_completada": {"dopamina": 8, "cortisol": -3},
        "error_sistema": {"cortisol": 12, "serotonina": -4},
        "interaccion_positiva": {"oxitocina": 6, "serotonina": 4},
        "interaccion_negativa": {"oxitocina": -5, "cortisol": 6},
        "usuario_ausente_prolongado": {"cortisol": 4, "oxitocina": -2},
        "usuario_regresa": {"oxitocina": 5, "dopamina": 3, "cortisol": -4},
    }

    def __init__(self):
        self.dopamina = 50.0
        self.serotonina = 50.0
        self.cortisol = 20.0
        self.oxitocina = 50.0
        self.ultima_actualizacion = datetime.utcnow()
        self._cargar_desde_db()

    def _cargar_desde_db(self) -> None:
        """Carga el ultimo estado guardado en la base de datos, si existe."""
        try:
            with memory._conexion() as conn:
                cur = conn.cursor()
                cur.execute("SELECT * FROM estado_animo WHERE id = 1")
                fila = cur.fetchone()
                if fila:
                    self.dopamina = fila["dopamina"]
                    self.serotonina = fila["serotonina"]
                    self.cortisol = fila["cortisol"]
                    self.oxitocina = fila["oxitocina"]
                    if fila["ultima_actualizacion"]:
                        self.ultima_actualizacion = datetime.fromisoformat(fila["ultima_actualizacion"])
        except Exception as e:
            logger.warning("No se pudo cargar estado neuroquimico previo, se usan valores por defecto: %s", e)

    def _guardar_en_db(self) -> None:
        try:
            with memory._conexion() as conn:
                cur = conn.cursor()
                cur.execute("""
                    UPDATE estado_animo
                    SET dopamina = ?, serotonina = ?, cortisol = ?, oxitocina = ?, ultima_actualizacion = ?
                    WHERE id = 1
                """, (self.dopamina, self.serotonina, self.cortisol, self.oxitocina,
                      self.ultima_actualizacion.isoformat()))
        except Exception as e:
            logger.exception("Error guardando estado neuroquimico: %s", e)

    def _limitar(self, valor: float) -> float:
        return max(self.LIMITE_MIN, min(self.LIMITE_MAX, valor))

    def actualizar(self, evento: str) -> None:
        """
        Aplica el efecto de un evento conocido sobre el estado actual.
        Si el evento no esta registrado, no hace nada (y lo informa por log).
        """
        efectos = self.EVENTOS.get(evento)
        if not efectos:
            logger.info("Evento neuroquimico desconocido, se ignora: %s", evento)
            return

        self.dopamina = self._limitar(self.dopamina + efectos.get("dopamina", 0))
        self.serotonina = self._limitar(self.serotonina + efectos.get("serotonina", 0))
        self.cortisol = self._limitar(self.cortisol + efectos.get("cortisol", 0))
        self.oxitocina = self._limitar(self.oxitocina + efectos.get("oxitocina", 0))
        self.ultima_actualizacion = datetime.utcnow()
        self._guardar_en_db()
        logger.debug("Estado neuroquimico actualizado por evento '%s': %s", evento, self.to_dict())

    def decaimiento_temporal(self, minutos_transcurridos: float) -> None:
        """
        Aplica un decaimiento natural hacia valores "base" con el paso
        del tiempo (homeostasis). Pensado para llamarse periodicamente
        desde heartbeat.py.
        """
        try:
            factor = min(1.0, minutos_transcurridos / (60 * 6))  # se estabiliza en ~6hs
            self.dopamina += (50 - self.dopamina) * 0.05 * factor
            self.serotonina += (50 - self.serotonina) * 0.05 * factor
            self.cortisol += (15 - self.cortisol) * 0.08 * factor
            self.oxitocina += (50 - self.oxitocina) * 0.05 * factor

            self.dopamina = self._limitar(self.dopamina)
            self.serotonina = self._limitar(self.serotonina)
            self.cortisol = self._limitar(self.cortisol)
            self.oxitocina = self._limitar(self.oxitocina)

            self.ultima_actualizacion = datetime.utcnow()
            self._guardar_en_db()
        except Exception as e:
            logger.exception("Error aplicando decaimiento temporal: %s", e)

    def obtener_estado_animo(self) -> str:
        """
        Traduce las variables numericas a una etiqueta de animo legible,
        usada por heartbeat.py y command_router.py para dar contexto al LLM.
        """
        if self.cortisol > 70:
            return "estresado"
        if self.dopamina > 70 and self.serotonina > 60:
            return "entusiasta"
        if self.serotonina < 30:
            return "apagado"
        if self.oxitocina > 70:
            return "cercano"
        return "neutral"

    def to_dict(self) -> Dict[str, float]:
        return {
            "dopamina": round(self.dopamina, 1),
            "serotonina": round(self.serotonina, 1),
            "cortisol": round(self.cortisol, 1),
            "oxitocina": round(self.oxitocina, 1),
            "estado_animo": self.obtener_estado_animo(),
            "ultima_actualizacion": self.ultima_actualizacion.isoformat(),
        }


# Instancia unica compartida por toda la aplicacion (patron singleton simple).
estado_global = EstadoNeuroquimico()
