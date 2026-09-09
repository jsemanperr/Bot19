# -*- coding: utf-8 -*-
"""
skills/spotify_skill.py
=======================
Control de Spotify via API oficial.
Requisitos:
- pip install spotipy
- Crear app en https://developer.spotify.com/dashboard
- Obtener CLIENT_ID, CLIENT_SECRET y configurar REDIRECT_URI (ej: http://localhost:8888/callback)
- Guardar en .env: SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET, SPOTIFY_REDIRECT_URI
"""
import os
import logging
from urllib.parse import urlencode
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("jarvis.skills.spotify")

CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
REDIRECT_URI = os.getenv("SPOTIFY_REDIRECT_URI", "http://localhost:8888/callback")
SCOPE = "user-read-playback-state user-modify-playback-state user-read-currently-playing"
CACHE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", ".spotify_cache")


def _oauth():
    return SpotifyOAuth(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        redirect_uri=REDIRECT_URI,
        scope=SCOPE,
        cache_path=CACHE_PATH,
        open_browser=False,
    )


def url_autorizacion() -> str:
    """Devuelve la URL que el usuario debe abrir para autorizar Spotify."""
    if not CLIENT_ID or not CLIENT_SECRET:
        return "Faltan SPOTIFY_CLIENT_ID y SPOTIFY_CLIENT_SECRET en .env"
    return _oauth().get_authorize_url()


def completar_autorizacion(code: str) -> None:
    """Guarda el token obtenido por Spotify tras el callback OAuth."""
    _oauth().get_access_token(code, as_dict=False, check_cache=False)

def _get_spotify():
    if not CLIENT_ID or not CLIENT_SECRET:
        return None, "Faltan credenciales de Spotify en .env"
    try:
        oauth = _oauth()
        if not oauth.get_cached_token():
            return None, (
                "Spotify necesita autorización. Abre http://127.0.0.1:8000/spotify/login "
                "en el navegador y acepta el acceso."
            )
        sp = spotipy.Spotify(auth_manager=oauth)
        sp.current_user()
        return sp, None
    except Exception as e:
        logger.error("Error autenticando Spotify: %s", e)
        return None, (
            "Spotify necesita autorización. Abre http://127.0.0.1:8000/spotify/login "
            "en el navegador y acepta el acceso. Detalle: " + str(e)
        )


def _activar_dispositivo(sp) -> str | None:
    """Selecciona un dispositivo disponible para evitar NO_ACTIVE_DEVICE."""
    dispositivos = sp.devices().get("devices", [])
    if not dispositivos:
        return None

    activo = next((d for d in dispositivos if d.get("is_active")), None)
    dispositivo = activo or dispositivos[0]
    if not dispositivo.get("is_active"):
        sp.transfer_playback(dispositivo["id"], device_ids=[dispositivo["id"]], play=False)
    return dispositivo.get("name", "dispositivo Spotify")


def buscar_y_reproducir(query: str, remitente: str = "") -> str:
    if not query:
        return "¿Qué quieres reproducir?"
    sp, error = _get_spotify()
    if error:
        return error
    try:
        resultados = sp.search(q=query, type="track,album,playlist", limit=3)
        items = []
        for tipo in ["tracks", "albums", "playlists"]:
            for item in resultados.get(tipo, {}).get("items", []):
                if tipo == "tracks":
                    uri = item["uri"]
                    nombre = f"{item['name']} - {item['artists'][0]['name']}"
                elif tipo == "albums":
                    uri = item["uri"]
                    nombre = f"Álbum: {item['name']} - {item['artists'][0]['name']}"
                else:
                    uri = item["uri"]
                    nombre = f"Playlist: {item['name']} - {item['owner']['display_name']}"
                items.append({"uri": uri, "nombre": nombre})
        if not items:
            return f"No encontré nada para '{query}' en Spotify."
        dispositivo = _activar_dispositivo(sp)
        if not dispositivo:
            return (
                "No hay ningún dispositivo Spotify activo. Abre Spotify en tu teléfono, "
                "computadora, navegador o altavoz e inténtalo de nuevo."
            )
        sp.start_playback(uris=[items[0]["uri"]])
        return f"Reproduciendo en {dispositivo}: {items[0]['nombre']}"
    except Exception as e:
        logger.exception("Error reproduciendo en Spotify: %s", e)
        return f"No pude reproducir en Spotify: {e}"

def controlar_spotify(comando: str, remitente: str = "") -> str:
    sp, error = _get_spotify()
    if error:
        return error
    try:
        comando_lower = comando.lower()
        if any(palabra in comando_lower for palabra in ("pausa", "siguiente", "next", "anterior", "prev", "reanuda", "resume", "volumen")):
            if not _activar_dispositivo(sp):
                return "No hay ningún dispositivo Spotify activo. Abre Spotify e inténtalo de nuevo."
        if "pausa" in comando_lower:
            sp.pause_playback()
            return "Pausé la reproducción."
        elif "siguiente" in comando_lower or "next" in comando_lower:
            sp.next_track()
            return "Siguiente canción."
        elif "anterior" in comando_lower or "prev" in comando_lower:
            sp.previous_track()
            return "Canción anterior."
        elif "sube" in comando_lower and "volumen" in comando_lower:
            info = sp.current_playback()
            if info and info.get("device"):
                vol = info["device"]["volume_percent"]
                nuevo = min(100, vol + 10)
                sp.volume(nuevo)
                return f"Volumen subido a {nuevo}%."
        elif "baja" in comando_lower and "volumen" in comando_lower:
            info = sp.current_playback()
            if info and info.get("device"):
                vol = info["device"]["volume_percent"]
                nuevo = max(0, vol - 10)
                sp.volume(nuevo)
                return f"Volumen bajado a {nuevo}%."
        elif "reanuda" in comando_lower or "resume" in comando_lower:
            sp.start_playback()
            return "Reanudé la reproducción."
        else:
            return "Comandos: pausa, siguiente, anterior, sube volumen, baja volumen, reanuda."
    except Exception as e:
        logger.exception("Error controlando Spotify: %s", e)
        return f"No pude controlar Spotify: {e}"