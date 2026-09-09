# -*- coding: utf-8 -*-
"""Consultas OSINT limitadas a datos publicos de correo, dominio y usuario."""

import importlib.util
import os
import re
import subprocess
import sys
from datetime import date, datetime
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

load_dotenv()

TIMEOUT_SEGUNDOS = 12
PATRON_CORREO = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PATRON_DOMINIO = re.compile(r"(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,63}", re.I)
PATRON_USUARIO = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,63}$")


def osint_email(email: str) -> str:
    """Consulta HIBP v3 para saber si un correo figura en brechas publicadas."""
    email = (email or "").strip().lower()
    if not PATRON_CORREO.fullmatch(email):
        return "Indicame una direccion de correo valida."
    clave = os.getenv("HIBP_API_KEY", "").strip()
    if not clave:
        return "Have I Been Pwned requiere HIBP_API_KEY para consultar brechas de correo."
    try:
        respuesta = requests.get(
            f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}",
            headers={"hibp-api-key": clave, "user-agent": "Kaori-OSINT/1.0"},
            params={"truncateResponse": "true"},
            timeout=TIMEOUT_SEGUNDOS,
        )
    except requests.RequestException:
        return "No pude contactar Have I Been Pwned en este momento."
    if respuesta.status_code == 404:
        return f"No hay brechas conocidas para {email} en Have I Been Pwned."
    if respuesta.status_code == 429:
        return "Have I Been Pwned aplico limite de solicitudes. Intenta mas tarde."
    if respuesta.status_code in {401, 403}:
        return "HIBP_API_KEY no fue aceptada para esta consulta."
    if not respuesta.ok:
        return "Have I Been Pwned no pudo completar la consulta."
    try:
        brechas = respuesta.json()
    except ValueError:
        return "Have I Been Pwned devolvio una respuesta no valida."
    nombres = ", ".join(item.get("Name", "sin nombre") for item in brechas[:8])
    extra = f" y {len(brechas) - 8} mas" if len(brechas) > 8 else ""
    return f"{email} aparece en {len(brechas)} brecha(s) conocida(s): {nombres}{extra}."


def _texto_fecha(valor: object) -> str:
    if isinstance(valor, (list, tuple)):
        valor = valor[0] if valor else None
    if isinstance(valor, (date, datetime)):
        return valor.isoformat()
    return str(valor or "no informada")


def osint_domain(dominio: str) -> str:
    """Obtiene datos basicos de un dominio via SecurityTrails o WHOIS."""
    dominio = urlparse((dominio or "").strip()).netloc or (dominio or "").strip()
    dominio = dominio.lower().split("/")[0]
    if not PATRON_DOMINIO.fullmatch(dominio):
        return "Indicame un dominio valido, por ejemplo: ejemplo.com."

    clave = os.getenv("SECURITYTRAILS_API_KEY", "").strip()
    if clave:
        try:
            respuesta = requests.get(
                f"https://api.securitytrails.com/v1/domain/{dominio}",
                headers={"APIKEY": clave}, timeout=TIMEOUT_SEGUNDOS,
            )
            if respuesta.ok:
                datos = respuesta.json()
                return (
                    f"Dominio: {datos.get('hostname', dominio)}. Registrador: {datos.get('registrar') or 'no informado'}. "
                    f"Organizacion: {datos.get('current_dns', {}).get('soa', {}).get('email') or 'no informada'}."
                )
        except (requests.RequestException, ValueError):
            pass

    if importlib.util.find_spec("whois") is None:
        return "No hay datos de SecurityTrails y falta python-whois. Instala dependencias con: pip install -r requirements.txt."
    try:
        import whois

        datos = whois.whois(dominio)
        return (
            f"Dominio: {dominio}. Registrador: {datos.get('registrar') or 'no informado'}. "
            f"Creado: {_texto_fecha(datos.get('creation_date'))}. "
            f"Vence: {_texto_fecha(datos.get('expiration_date'))}."
        )
    except Exception:
        return f"No pude obtener los datos WHOIS de {dominio}."


def osint_username(username: str) -> str:
    """Busca perfiles publicos de un usuario con Sherlock cuando esta instalado."""
    username = (username or "").strip().lstrip("@")
    if not PATRON_USUARIO.fullmatch(username):
        return "Indicame un nombre de usuario valido, sin espacios."
    if os.getenv("SHERLOCK_INSTALLED", "false").strip().lower() != "true":
        return "La busqueda de usuarios requiere Sherlock. Instalala con: pip install sherlock-project, y cambia SHERLOCK_INSTALLED=true."
    try:
        proceso = subprocess.run(
            [sys.executable, "-m", "sherlock", username, "--print-found"],
            capture_output=True, text=True, timeout=60, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return "Sherlock no pudo completar la busqueda. Verifica su instalacion e intenta de nuevo."
    urls = re.findall(r"https?://\S+", proceso.stdout)
    if urls:
        return f"Perfiles publicos encontrados para {username}:\n" + "\n".join(urls[:10])
    return f"No encontre perfiles publicos para {username} con Sherlock."


def _extraer(comando: str, patron: re.Pattern[str]) -> str | None:
    coincidencia = patron.search(comando or "")
    return coincidencia.group(0) if coincidencia else None


def skill_osint_email(comando: str, remitente: str = "") -> str:
    email = _extraer(comando, PATRON_CORREO)
    return osint_email(email or "")


def skill_osint_domain(comando: str, remitente: str = "") -> str:
    dominio = _extraer(comando, PATRON_DOMINIO)
    return osint_domain(dominio or "")


def skill_osint_username(comando: str, remitente: str = "") -> str:
    coincidencia = re.search(r"(?:usuario|username|perfil)\s+@?([A-Za-z0-9_.-]+)", comando or "", re.I)
    return osint_username(coincidencia.group(1) if coincidencia else "")