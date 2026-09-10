"""Prueba segura de conectividad y registro de skills."""

import logging
import os
import time
from collections.abc import Callable

from skills import SKILLS

logger = logging.getLogger("jarvis.diagnostics")

_PRUEBAS_LECTURA: dict[str, str] = {
    "clima": "Madrid",
    "pronostico": "Madrid",
    "calidad_aire": "Madrid",
    "vuelo": "AA100",
    "noticias": "tecnología",
    "buscar_web": "OpenAI",
    "biblia": "Juan 3:16",
    "cotizacion": "AAPL",
    "geocodificar": "Ciudad de México",
    "hibp": "test@example.com",
    "securitytrails": "example.com",
    "info_pais": "México",
    "geoip": "8.8.8.8",
    "geoip_ipstack": "8.8.8.8",
    "geoip_ipapi": "8.8.8.8",
    "geoapify_ip": "8.8.8.8",
    "track_usuario": "8.8.8.8",
    "telefono_abstract": "+14155552671",
    "telefono_numlookup": "+14155552671",
    "telefono_numverify": "+14155552671",
    "telefono_veriphone": "+14155552671",
    "email_abstract": "test@example.com",
    "email_mailboxlayer": "test@example.com",
    "ip_abstract": "8.8.8.8",
    "osint_email": "test@example.com",
    "osint_domain": "example.com",
    "osint_username": "octocat",
    "buscar_celular": "+14155552671",
    "postal": "06000",
    "futbol": "Premier League",
    "receta": "pasta",
    "dietly": "pollo",
    "tasty": "pasta",
    "comida": "pasta",
    "comida_random": "",
    "coctel": "mojito",
    "coctel_random": "",
    "coctel_ingrediente": "tequila",
    "dato_curioso": "",
    "clima_weatherstack": "Madrid",
}

_OMITIDAS = {
    "imagen": "genera archivos y puede consumir créditos",
    "imagen_orshot": "genera archivos y puede consumir créditos",
    "editar_imagen": "requiere archivo de entrada",
    "lempi": "puede descargar contenido multimedia",
    "video": "genera un video y puede consumir créditos",
    "spotify_buscar": "requiere OAuth y puede alterar la reproducción",
    "spotify_control": "altera la reproducción",
    "eventos": "requiere Google OAuth",
    "agregar_evento": "crea un evento real",
    "correos": "accede a correo privado",
    "gasto": "escribe datos financieros",
    "geoapify_reverse": "requiere coordenadas de entrada",
}

_SOLO_REMITENTE = {"comida_random", "coctel_random", "dato_curioso"}

_PRUEBAS_USO: tuple[str, ...] = (
    "clima en Madrid",
    "pronóstico en Madrid",
    "receta aleatoria",
    "cóctel aleatorio",
    "dato curioso",
    "noticias de tecnología",
    "busca en internet Python",
    "información de vuelos AA100",
    "información del país México",
    "geolocaliza la IP 8.8.8.8",
    "valida este teléfono +14155552671",
    "valida este correo test@example.com",
)


def _estado(respuesta: str) -> str:
    texto = (respuesta or "").strip()
    if not texto:
        return "ERROR: respuesta vacía"
    if any(marca in texto.lower() for marca in ("falta configurar", "no está configur", "no pude contactar", "rechazó la credencial")):
        return f"PENDIENTE: {texto.splitlines()[0][:180]}"
    if any(marca in texto.lower() for marca in ("error", "no encontré", "no pude")):
        return f"RESPONDIÓ: {texto.splitlines()[0][:180]}"
    return f"OK: {texto.splitlines()[0][:180]}"


def ejecutar_diagnostico() -> str:
    """Prueba skills de lectura y devuelve un informe apto para enviar por chat."""
    inicio = time.monotonic()
    lineas = ["🧪 DIAGNÓSTICO DE JARVIS-LITE", f"Skills registradas: {len(SKILLS)}", ""]
    for nombre, funcion in SKILLS.items():
        if nombre in _OMITIDAS:
            lineas.append(f"⏭️ {nombre}: omitida ({_OMITIDAS[nombre]})")
            continue
        entrada = _PRUEBAS_LECTURA.get(nombre)
        if entrada is None:
            lineas.append(f"⚠️ {nombre}: sin caso de prueba definido")
            continue
        try:
            if nombre in _SOLO_REMITENTE:
                respuesta = funcion("diagnostico")
            else:
                respuesta = funcion(entrada, "diagnostico")
            lineas.append(f"✅ {nombre}: {_estado(str(respuesta))}")
        except Exception as error:
            logger.exception("Fallo en diagnóstico de %s", nombre)
            lineas.append(f"❌ {nombre}: ERROR {type(error).__name__}: {error}")
    lineas.extend(
        [
            "",
            f"Duración: {time.monotonic() - inicio:.1f}s",
            "Las skills omitidas requieren confirmación, OAuth, archivos o pueden generar cargos.",
        ]
    )
    return "\n".join(lineas)


def enviar_diagnostico() -> str:
    """Ejecuta la prueba y la entrega a los canales configurados."""
    informe = ejecutar_diagnostico()
    from notifications import enviar_todos

    resultados = enviar_todos(informe)
    canales = ", ".join(nombre for nombre, enviado in resultados.items() if enviado) or "ningún canal configurado"
    return f"{informe}\n\n📨 Informe enviado a: {canales}."


def ejecutar_pruebas_uso(remitente: str = "diagnostico") -> str:
    """Ejecuta ejemplos seguros pasando por el mismo router que usa el chat."""
    import command_router

    anterior = os.environ.get("BROADCAST_RESPONSES")
    os.environ["BROADCAST_RESPONSES"] = "false"
    lineas = ["🧪 PRUEBAS DE USO REAL", "Cada línea simula un mensaje normal del usuario.", ""]
    try:
        for numero, ejemplo in enumerate(_PRUEBAS_USO, 1):
            inicio = time.monotonic()
            try:
                respuesta = command_router.procesar_comando(ejemplo, remitente)
                resumen = " ".join(str(respuesta).split())
                if len(resumen) > 220:
                    resumen = resumen[:217] + "..."
                lineas.append(f"{numero}. ✅ «{ejemplo}»\n   ↳ {resumen} ({time.monotonic() - inicio:.1f}s)")
            except Exception as error:
                lineas.append(f"{numero}. ❌ «{ejemplo}»\n   ↳ {type(error).__name__}: {error}")
    finally:
        if anterior is None:
            os.environ.pop("BROADCAST_RESPONSES", None)
        else:
            os.environ["BROADCAST_RESPONSES"] = anterior
    lineas.extend(["", "⏭️ No se probaron acciones destructivas, privadas o con efectos reales."])
    return "\n".join(lineas)
