"""Router pequeno y explicito para JARVIS-LITE."""

import re
from typing import Callable

import domotics
import memory
import pc_control
from neurochemistry import estado_global
from skills import SKILLS
from skills.personality_skills import skill_chiste, skill_estado_animo, skill_que_sabes_de_mi, skill_saludar

_PENDIENTES: dict[str, str] = {}

MENU_AYUDA = """🤖 Kaori está lista

Puedo ejecutar la mayoría de las acciones con frases normales:

🌤️ CLIMA
• `clima en Madrid`
• `pronóstico en Ciudad de México`

🍽️ COMIDA Y BEBIDAS
• `receta aleatoria`
• `receta de pasta`
• `qué puedo cocinar con pollo`
• `cóctel aleatorio`

🎵 SPOTIFY
• `spotify música de Daft Punk`
• `spotify pausa` / `spotify siguiente`

🔎 BÚSQUEDAS Y DATOS
• `busca en internet ...`
• `noticias de tecnología`
• `dato curioso`
• `información de vuelos ...`
• `valida este teléfono ...`

🧰 SISTEMA
• `estado del sistema`
• `abrir aplicación Chrome`
• `enciende la luz sala`

También puedes escribir `/menu`, `/clima`, `/receta`, `/receta_aleatoria` o `/voz`.
No necesitas repetir una solicitud: si falta un detalle opcional, uso un valor razonable y ejecuto la acción."""


def _ejecutar(nombre: str, texto: str, remitente: str) -> str:
    funcion: Callable = SKILLS[nombre]
    if nombre in {"clima", "pronostico", "calidad_aire"}:
        return funcion(texto, remitente)
    return funcion(texto, remitente)


def _ciudad(texto: str) -> str:
    ciudad = re.sub(r"(?i).*\b(?:en|de|para)\b", "", texto).strip(" ?.")
    return ciudad or "Buenos Aires"


def procesar_comando(texto: str | None, remitente: str = "local") -> str:
    texto = (texto or "").strip()
    if not texto:
        return "No recibí ningún comando, Jefe."
    normalizado = texto.lower()
    memory.guardar_mensaje(remitente, "usuario", texto)

    if normalizado in {"/help", "/ayuda", "/menu", "ayuda", "menú", "menu"} or "qué puedes hacer" in normalizado or "capacidades" in normalizado:
        respuesta = MENU_AYUDA
    elif re.search(r"\b(hola|buenas|buenos días|buenas tardes|buenas noches)\b", normalizado):
        respuesta = skill_saludar(remitente=remitente)
    elif "chiste" in normalizado:
        respuesta = skill_chiste(remitente=remitente)
    elif "cómo estás" in normalizado or "estado de ánimo" in normalizado:
        respuesta = skill_estado_animo(remitente=remitente)
    elif "qué sabes de mí" in normalizado:
        respuesta = skill_que_sabes_de_mi(remitente=remitente)
    elif "estado del sistema" in normalizado:
        respuesta = str(pc_control.obtener_estado_sistema())
    elif re.search(r"\b(apaga|apagar)\s+(la\s+)?pc\b", normalizado):
        _PENDIENTES[remitente] = "apagar"
        respuesta = "Esta acción apagará la PC. Respondé 'confirmar apagado' para continuar."
    elif "confirmar apagado" in normalizado and _PENDIENTES.get(remitente) == "apagar":
        _PENDIENTES.pop(remitente, None)
        respuesta = pc_control.apagar_pc(confirmado=True)
    elif re.search(r"\b(reinicia|reiniciar)\s+(la\s+)?pc\b", normalizado):
        _PENDIENTES[remitente] = "reiniciar"
        respuesta = "Esta acción reiniciará la PC. Respondé 'confirmar reinicio' para continuar."
    elif "confirmar reinicio" in normalizado and _PENDIENTES.get(remitente) == "reiniciar":
        _PENDIENTES.pop(remitente, None)
        respuesta = pc_control.reiniciar_pc(confirmado=True)
    elif match := re.search(r"abr[ií]r (?:la )?app(?:licaci[oó]n)? (.+)", texto, re.I):
        respuesta = pc_control.abrir_aplicacion(match.group(1).strip())
    elif "calidad del aire" in normalizado:
        respuesta = _ejecutar("calidad_aire", _ciudad(texto), remitente)
    elif "pronóstico" in normalizado or "pronostico" in normalizado:
        respuesta = _ejecutar("pronostico", _ciudad(texto), remitente)
    elif re.search(r"\bclima\b|\btiempo\b", normalizado):
        respuesta = _ejecutar("clima", _ciudad(texto), remitente)
    elif re.search(r"\bvuelos?\b", normalizado):
        respuesta = _ejecutar("vuelo", texto, remitente)
    elif "genera" in normalizado and "imagen" in normalizado:
        respuesta = _ejecutar("imagen", texto, remitente)
    elif "video" in normalizado and any(x in normalizado for x in ("genera", "crea", "haz")):
        respuesta = _ejecutar("video", texto, remitente)
    elif "lempi" in normalizado:
        respuesta = _ejecutar("lempi", texto, remitente)
    elif "spotify" in normalizado and any(x in normalizado for x in ("pausa", "siguiente", "anterior", "volumen", "reanuda")):
        respuesta = _ejecutar("spotify_control", texto, remitente)
    elif "spotify" in normalizado:
        respuesta = _ejecutar("spotify_buscar", re.sub(r"(?i).*spotify", "", texto).strip(), remitente)
    elif "dato curioso" in normalizado or "dato fun" in normalizado:
        respuesta = _ejecutar("dato_curioso", texto, remitente)
    elif re.search(r"\b(cóctel|coctel)\b", normalizado) and any(x in normalizado for x in ("aleatorio", "random", "sorpresa", "dame uno")):
        respuesta = _ejecutar("coctel_random", texto, remitente)
    elif "cóctel" in normalizado or "coctel" in normalizado:
        respuesta = _ejecutar("coctel", texto, remitente)
    elif re.search(r"\b(receta|comida|plato)\b", normalizado) and any(x in normalizado for x in ("aleatoria", "aleatorio", "random", "sorpresa", "qué cocino", "que cocino", "dame una")):
        respuesta = _ejecutar("comida_random", "", remitente)
    elif "receta" in normalizado:
        respuesta = _ejecutar("comida", texto, remitente)
    elif "comida" in normalizado or "meal" in normalizado:
        respuesta = _ejecutar("comida", texto, remitente)
    elif "fútbol" in normalizado or "futbol" in normalizado:
        respuesta = _ejecutar("futbol", texto, remitente)
    elif "noticia" in normalizado or " noticias" in normalizado:
        respuesta = _ejecutar("noticias", texto, remitente)
    elif "biblia" in normalizado or "versículo" in normalizado or "versiculo" in normalizado:
        respuesta = _ejecutar("biblia", texto, remitente)
    elif "buscar en internet" in normalizado or "busca en la web" in normalizado or re.search(r"\b(busca|buscar)\b", normalizado):
        respuesta = _ejecutar("buscar_web", re.sub(r"(?i)^(?:busca|buscar)\s*", "", texto), remitente)
    elif "cotización" in normalizado or "cotizacion" in normalizado or "acciones de" in normalizado:
        respuesta = _ejecutar("cotizacion", texto, remitente)
    elif "mapa" in normalizado or "geocodifica" in normalizado:
        respuesta = _ejecutar("geocodificar", texto, remitente)
    elif "hibp" in normalizado or "filtración" in normalizado or "filtracion" in normalizado:
        respuesta = _ejecutar("hibp", texto, remitente)
    elif "securitytrails" in normalizado:
        respuesta = _ejecutar("securitytrails", texto, remitente)
    elif "país" in normalizado or "pais" in normalizado:
        respuesta = _ejecutar("info_pais", texto, remitente)
    elif "weatherstack" in normalizado:
        respuesta = _ejecutar("clima_weatherstack", texto, remitente)
    elif "geoapify" in normalizado:
        respuesta = _ejecutar("geoapify_ip", texto, remitente)
    elif "ipstack" in normalizado:
        respuesta = _ejecutar("geoip_ipstack", texto, remitente)
    elif "ipapi" in normalizado:
        respuesta = _ejecutar("geoip_ipapi", texto, remitente)
    elif "geoip" in normalizado:
        respuesta = _ejecutar("geoip", texto, remitente)
    elif "osint" in normalizado and "email" in normalizado:
        respuesta = _ejecutar("osint_email", texto, remitente)
    elif "osint" in normalizado and "dominio" in normalizado:
        respuesta = _ejecutar("osint_domain", texto, remitente)
    elif "osint" in normalizado:
        respuesta = _ejecutar("osint_username", texto, remitente)
    elif "dietly" in normalizado or "nutrición" in normalizado or "nutricion" in normalizado:
        respuesta = _ejecutar("dietly", texto, remitente)
    elif "teléfono" in normalizado or "telefono" in normalizado:
        respuesta = _ejecutar("telefono_veriphone", texto, remitente)
    elif "correo" in normalizado or "email" in normalizado:
        respuesta = _ejecutar("correos", texto, remitente) if "mis correos" in normalizado else _ejecutar("email_abstract", texto, remitente)
    elif re.search(r"\b(ip|dirección ip)\b", normalizado):
        respuesta = _ejecutar("ip_abstract", texto, remitente)
    elif "evento" in normalizado or "calendario" in normalizado:
        respuesta = _ejecutar("eventos", texto, remitente)
    elif "gasto" in normalizado and ("registr" in normalizado or "anot" in normalizado):
        respuesta = _ejecutar("gasto", texto, remitente)
    elif re.search(r"\b(encend|apag).*\bluz\b", normalizado):
        entidad = texto.split("luz", 1)[-1].strip(" .")
        respuesta = domotics.encender_luz(entidad) if "encend" in normalizado else domotics.apagar_luz(entidad)
    else:
        respuesta = "No reconocí esa solicitud todavía. Escribí *menu* para ver ejemplos o probá: `clima en Madrid`, `receta aleatoria`, `busca en internet ...` o `dato curioso`."

    memory.guardar_mensaje("jarvis", "asistente", respuesta)
    estado_global.actualizar("tarea_completada")
    return respuesta
