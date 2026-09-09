# -*- coding: utf-8 -*-
"""
skills/personality_skills.py
==============================
Skills "de personalidad" de Kaori: chistes, saludos según la hora,
estado de ánimo (basado en neurochemistry.py) y resumen de lo que
recuerda sobre el usuario (basado en memory.py).
"""

import re
import random
import logging
from typing import Optional

import memory
import personality
from neurochemistry import estado_global

logger = logging.getLogger("jarvis.skills.personality")

# Al menos 20 chistes en español, variados y sin contenido ofensivo.
_CHISTES = [
    "¿Por qué los pájaros no usan Facebook? Porque ya tienen Twitter.",
    "¿Qué le dijo un techo a otro techo? Techo de menos.",
    "¿Cómo se llama el campeón de buceo? Marco Polo.",
    "¿Qué hace una abeja en el gimnasio? Zum-ba.",
    "¿Por qué el libro de matemáticas está triste? Porque tiene demasiados problemas.",
    "¿Qué le dice un semáforo a otro? No me mires, que me estoy cambiando.",
    "¿Cómo se dice pañuelo en japonés? Sarasaka.",
    "¿Qué hace un perro con un taladro? Taladrando.",
    "¿Cuál es el colmo de un electricista? Que le den calambre las ganas de trabajar.",
    "¿Por qué el tomate se puso rojo? Porque vio a la ensalada desnuda.",
    "¿Qué le dijo una impresora a otra? ¿Esa hoja es tuya o es una copia?",
    "¿Cómo llamas a un dinosaurio que duerme? ¡Un dino-siesta!",
    "¿Qué hace una fresa en la cama? Un fresor.",
    "¿Cuál es el colmo de un jardinero? Que su mujer se llame Rosa y la pise.",
    "¿Por qué los peces no juegan tenis? Porque le tienen miedo a la red.",
    "¿Qué le dijo el número 3 al número 30? Para ser como yo, tienes que ser sincero.",
    "¿Cómo se llama el hombre invisible? No sé, no lo he visto.",
    "¿Qué hace una vaca con las patas para arriba? Leche condensada.",
    "¿Por qué no le gustan las bromas al calendario? Porque sus días están contados.",
    "¿Cuál es el café más peligroso del mundo? El ex-preso.",
    "¿Qué le dice un jaguar a otro jaguar? Jaguarl, ¿cómo estás?",
    "¿Por qué el futbolista llevaba un paraguas al partido? Por si acaso lo doblaban.",
]


def skill_chiste(parametro: Optional[str] = None, remitente: str = "") -> str:
    """Devuelve un chiste aleatorio de la lista interna."""
    return random.choice(_CHISTES)


def _buscar_nombre_usuario() -> Optional[str]:
    """
    Busca en las memorias guardadas si el usuario alguna vez dijo su
    nombre (ej: 'me llamo Juan' o 'mi nombre es Juan').
    """
    try:
        recuerdos = memory.buscar_memorias("nombre", limite=20) + memory.buscar_memorias("llamo", limite=20)
        patrones = [
            r"me llamo\s+([A-ZÁÉÍÓÚÑ][\wáéíóúñ]*)",
            r"mi nombre es\s+([A-ZÁÉÍÓÚÑ][\wáéíóúñ]*)",
        ]
        for recuerdo in recuerdos:
            contenido = recuerdo.get("contenido", "")
            for patron in patrones:
                m = re.search(patron, contenido, re.I)
                if m:
                    return m.group(1).capitalize()
    except Exception as e:
        logger.exception("Error buscando el nombre del usuario en memoria: %s", e)
    return None


def skill_saludar(parametro: Optional[str] = None, remitente: str = "") -> str:
    """Saluda según la hora del día, usando el nombre del usuario si lo conoce."""
    from datetime import datetime

    hora = datetime.now().hour
    if 5 <= hora < 12:
        momento = "manana"
        saludo_generico = "¡Buenos días"
    elif 12 <= hora < 20:
        momento = "tarde"
        saludo_generico = "¡Buenas tardes"
    else:
        momento = "noche"
        saludo_generico = "¡Buenas noches"

    # Si personality.json trae saludos personalizados, se usan esos.
    saludos_personalidad = personality.obtener_personalidad().get("saludos", {})
    saludo_base = saludos_personalidad.get(momento, saludo_generico)

    nombre = _buscar_nombre_usuario()
    honorifico = nombre if nombre else personality.obtener_honoratico()

    if not saludo_base.rstrip().endswith(("!", ".", "?")):
        return f"{saludo_base}, {honorifico}!"
    return f"{saludo_base}, {honorifico}"


def skill_estado_animo(parametro: Optional[str] = None, remitente: str = "") -> str:
    """Describe el estado de ánimo simulado de Kaori según neurochemistry.py."""
    estado = estado_global.to_dict()
    if estado["estado_animo"] == "entusiasta":
        return "Estoy con energía y contenta de hablar con vos. ¿Cómo venís, Jefe?"
    return "Estoy bien, Jefe. Me alegra que estés acá; ¿cómo venís vos?"


def skill_que_sabes_de_mi(parametro: Optional[str] = None, remitente: str = "") -> str:
    """Devuelve un resumen de las memorias guardadas sobre el usuario."""
    try:
        with memory._conexion() as conn:
            cur = conn.cursor()
            cur.execute("SELECT tipo, titulo, contenido FROM memorias ORDER BY id DESC LIMIT 15")
            filas = cur.fetchall()

        if not filas:
            return "Todavía no tengo recuerdos guardados sobre vos, Jefe."

        lineas = [f"- ({f['tipo']}) {f['titulo']}: {f['contenido']}" for f in filas]
        return "Esto es lo que recuerdo de vos, Jefe:\n" + "\n".join(lineas)

    except Exception as e:
        logger.exception("Error recuperando memorias del usuario: %s", e)
        return "Tuve un problema recuperando mis recuerdos sobre vos, Jefe."
