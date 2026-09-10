"""Skills HTTP para las APIs declaradas en la configuración extendida."""

import os
from urllib.parse import quote

import requests
from dotenv import load_dotenv

load_dotenv()
TIMEOUT = 15


def _get(url: str, **kwargs) -> dict:
    try:
        response = requests.get(url, timeout=TIMEOUT, **kwargs)
        response.raise_for_status()
        datos = response.json()
    except requests.Timeout as error:
        raise RuntimeError("La API tardó demasiado en responder.") from error
    except requests.RequestException as error:
        raise RuntimeError("No pude contactar la API configurada.") from error
    except ValueError as error:
        raise RuntimeError("La API devolvió una respuesta no válida.") from error
    if not isinstance(datos, dict):
        raise RuntimeError("La API devolvió un formato no compatible.")
    return datos


def _safe_call(func, valor: str, remitente: str) -> str:
    try:
        return func(valor, remitente)
    except RuntimeError as error:
        return f"⚠️ {error}"
    except (requests.RequestException, ValueError) as error:
        return f"⚠️ No pude completar la consulta: {error}"


def buscar_web(consulta: str, remitente: str = "") -> str:
    clave = os.getenv("SERPAPI_API_KEY", "").strip()
    if not clave or not consulta.strip():
        return "Configura SERPAPI_API_KEY y proporciona una consulta."
    datos = _get("https://serpapi.com/search.json", params={"q": consulta, "api_key": clave, "engine": "google"})
    resultados = datos.get("organic_results", [])[:5]
    if not resultados:
        return "No encontré resultados."
    return "\n".join(f"- {item.get('title', 'Sin título')}: {item.get('link', '')}" for item in resultados)


def consultar_biblia(consulta: str, remitente: str = "") -> str:
    clave = os.getenv("BIBLE_API_KEY", "").strip()
    biblia = os.getenv("BIBLE_ID", "").strip()
    if not clave or not biblia or not consulta.strip():
        return "Configura BIBLE_API_KEY, BIBLE_ID y una referencia bíblica."
    datos = _get(
        f"https://api.scripture.api.bible/v1/bibles/{quote(biblia)}/search",
        params={"q": consulta},
        headers={"api-key": clave},
    )
    versiculos = datos.get("data", {}).get("verses", [])[:5]
    return "\n".join(v.get("text", "") for v in versiculos) or "No encontré esa referencia."


def consultar_cotizacion(simbolo: str, remitente: str = "") -> str:
    clave = os.getenv("TWELVEDATA_API_KEY", "").strip()
    if not clave or not simbolo.strip():
        return "Configura TWELVEDATA_API_KEY y un símbolo bursátil."
    datos = _get("https://api.twelvedata.com/quote", params={"symbol": simbolo.strip(), "apikey": clave})
    if datos.get("status") == "error":
        return f"No pude consultar la cotización: {datos.get('message', 'error de API')}."
    return f"{datos.get('name', simbolo.upper())}: {datos.get('close', 'N/D')} ({datos.get('percent_change', 'N/D')}%)."


def geocodificar_direccion(direccion: str, remitente: str = "") -> str:
    clave = os.getenv("MAPBOX_ACCESS_TOKEN", "").strip()
    if not clave or not direccion.strip():
        return "Configura MAPBOX_ACCESS_TOKEN y una dirección."
    datos = _get(
        f"https://api.mapbox.com/geocoding/v5/mapbox.places/{quote(direccion)}.json",
        params={"access_token": clave, "limit": 1, "language": "es"},
    )
    features = datos.get("features", [])
    if not features:
        return "No encontré esa dirección."
    feature = features[0]
    lon, lat = feature.get("center", ["N/D", "N/D"])
    return f"{feature.get('place_name', direccion)}: latitud {lat}, longitud {lon}."


def verificar_filtracion(email: str, remitente: str = "") -> str:
    clave = os.getenv("HIBP_API_KEY", "").strip()
    if not clave or not email.strip():
        return "Configura HIBP_API_KEY y un correo."
    datos = _get(
        f"https://haveibeenpwned.com/api/v3/breachedaccount/{quote(email.strip())}",
        headers={"hibp-api-key": clave, "user-agent": "jarvis-lite"},
    )
    return "El correo aparece en filtraciones conocidas: " + ", ".join(item.get("Name", "desconocida") for item in datos)


def consultar_dominio_securitytrails(dominio: str, remitente: str = "") -> str:
    clave = os.getenv("SECURITYTRAILS_API_KEY", "").strip()
    if not clave or not dominio.strip():
        return "Configura SECURITYTRAILS_API_KEY y un dominio."
    datos = _get(
        f"https://api.securitytrails.com/v1/domain/{quote(dominio.strip())}",
        headers={"APIKEY": clave, "Accept": "application/json"},
    )
    registros = datos.get("current_dns", {})
    return f"Información DNS de {dominio}: {registros}"


def skill_buscar_web(comando: str, remitente: str = "") -> str:
    return _safe_call(buscar_web, comando, remitente)


def skill_biblia(comando: str, remitente: str = "") -> str:
    return _safe_call(consultar_biblia, comando, remitente)


def skill_cotizacion(comando: str, remitente: str = "") -> str:
    return _safe_call(consultar_cotizacion, comando, remitente)


def skill_geocodificar(comando: str, remitente: str = "") -> str:
    return _safe_call(geocodificar_direccion, comando, remitente)


def skill_hibp(comando: str, remitente: str = "") -> str:
    return _safe_call(verificar_filtracion, comando, remitente)


def skill_securitytrails(comando: str, remitente: str = "") -> str:
    return _safe_call(consultar_dominio_securitytrails, comando, remitente)
