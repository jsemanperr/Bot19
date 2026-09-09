# -*- coding: utf-8 -*-
"""
skills/gmail_skill.py
====================
Integración de Gmail para leer, resumir y gestionar correos.

Requiere:
- google-auth-oauthlib
- google-auth-httplib2
- google-api-python-client
- Archivo de credenciales OAuth en credentials/gmail_credentials.json

Configuración:
1. Crear una aplicación en Google Cloud Console
2. Descargar credenciales OAuth 2.0 (Cliente de escritorio)
3. Guardar en credentials/gmail_credentials.json
"""

import os
import pickle
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

import requests
from dotenv import load_dotenv

try:
    from google.auth.transport.requests import Request
    from google.oauth2.service_account import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth import default as google_default
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    HAS_GMAIL = True
except ImportError:
    HAS_GMAIL = False

load_dotenv()
logger = logging.getLogger("jarvis.skills.gmail")

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly", 
          "https://www.googleapis.com/auth/gmail.modify"]

CREDENTIALS_DIR = os.path.join(os.path.dirname(__file__), "..", "credentials")
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, "gmail_credentials.json")
TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "gmail_token.pickle")

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")


def _obtener_servicio_gmail():
    """Obtiene un cliente autenticado del servicio de Gmail."""
    if not HAS_GMAIL:
        logger.error("Librerías de Gmail no instaladas.")
        return None
    
    try:
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        
        creds = None
        
        # Cargar token existente
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        # Si no hay credenciales válidas, realizar autenticación
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    logger.error("Archivo de credenciales no encontrado: %s", CREDENTIALS_FILE)
                    return None
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            # Guardar token para uso futuro
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        servicio = build('gmail', 'v1', credentials=creds)
        return servicio
        
    except Exception as e:
        logger.exception("Error obteniendo servicio de Gmail: %s", e)
        return None


def obtener_correos_recientes(limite: int = 10, no_leidos: bool = False) -> List[Dict[str, Any]]:
    """
    Obtiene los correos recientes.
    
    :param limite: cantidad máxima de correos
    :param no_leidos: si True, solo correos no leídos
    :return: lista de correos con metadata
    """
    try:
        servicio = _obtener_servicio_gmail()
        if not servicio:
            return []
        
        query = "is:unread" if no_leidos else ""
        
        resultados = servicio.users().messages().list(
            userId='me',
            q=query,
            maxResults=limite
        ).execute()
        
        mensajes = resultados.get('messages', [])
        correos = []
        
        for mensaje in mensajes:
            msg = servicio.users().messages().get(
                userId='me',
                id=mensaje['id'],
                format='full'
            ).execute()
            
            headers = msg['payload']['headers']
            asunto = next((h['value'] for h in headers if h['name'] == 'Subject'), 'Sin asunto')
            remitente = next((h['value'] for h in headers if h['name'] == 'From'), 'Desconocido')
            fecha = next((h['value'] for h in headers if h['name'] == 'Date'), '')
            
            # Obtener fragmento del cuerpo
            snippet = msg.get('snippet', '')
            
            correos.append({
                'id': mensaje['id'],
                'asunto': asunto,
                'remitente': remitente,
                'fecha': fecha,
                'snippet': snippet,
                'no_leido': 'UNREAD' in msg.get('labelIds', [])
            })
        
        return correos
        
    except Exception as e:
        logger.exception("Error obteniendo correos recientes: %s", e)
        return []


def resumir_correos(correos: Optional[List[Dict[str, Any]]] = None, limite: int = 5) -> Optional[str]:
    """
    Obtiene y resume los correos más recientes usando un LLM.
    
    :param correos: lista de correos (si es None, obtiene los más recientes)
    :param limite: cantidad de correos a resumir
    :return: resumen de los correos
    """
    try:
        if correos is None:
            correos = obtener_correos_recientes(limite=limite)
        
        if not correos:
            return "No hay correos nuevos."
        
        # Preparar texto para el LLM
        texto_correos = "Estos son mis correos recientes:\n\n"
        for correo in correos[:limite]:
            texto_correos += f"""
**De:** {correo['remitente']}
**Asunto:** {correo['asunto']}
**Resumen:** {correo['snippet'][:150]}...

"""
        
        # Usar LLM para generar resumen
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": f"""{texto_correos}

Proporciona un resumen breve (máximo 3 líneas) de los puntos más importantes en estos correos.
Incluye solo información esencial y actionable.""",
            "stream": False
        }
        
        respuesta = requests.post(
            f"{OLLAMA_URL}/api/generate",
            json=payload,
            timeout=30
        )
        respuesta.raise_for_status()
        
        resultado = respuesta.json()
        return resultado.get("response", "No se pudo generar resumen.").strip()
        
    except Exception as e:
        logger.exception("Error resumiendo correos: %s", e)
        return None


def marcar_como_leido(id_mensaje: str) -> bool:
    """Marca un correo como leído."""
    try:
        servicio = _obtener_servicio_gmail()
        if not servicio:
            return False
        
        servicio.users().messages().modify(
            userId='me',
            id=id_mensaje,
            body={'removeLabelIds': ['UNREAD']}
        ).execute()
        
        return True
        
    except Exception as e:
        logger.exception("Error marcando correo como leído: %s", e)
        return False


def obtener_correo_completo(id_mensaje: str) -> Optional[Dict[str, Any]]:
    """Obtiene el texto completo de un correo."""
    try:
        servicio = _obtener_servicio_gmail()
        if not servicio:
            return None
        
        msg = servicio.users().messages().get(
            userId='me',
            id=id_mensaje,
            format='full'
        ).execute()
        
        headers = msg['payload']['headers']
        asunto = next((h['value'] for h in headers if h['name'] == 'Subject'), '')
        remitente = next((h['value'] for h in headers if h['name'] == 'From'), '')
        fecha = next((h['value'] for h in headers if h['name'] == 'Date'), '')
        
        # Extraer cuerpo del mensaje
        cuerpo = _extraer_cuerpo_mensaje(msg['payload'])
        
        return {
            'id': id_mensaje,
            'asunto': asunto,
            'remitente': remitente,
            'fecha': fecha,
            'cuerpo': cuerpo
        }
        
    except Exception as e:
        logger.exception("Error obteniendo correo completo: %s", e)
        return None


def _extraer_cuerpo_mensaje(payload: Dict[str, Any]) -> str:
    """Extrae el cuerpo de texto de un payload de Gmail."""
    try:
        if 'parts' in payload:
            cuerpo = ""
            for parte in payload['parts']:
                if parte['mimeType'] == 'text/plain':
                    datos = parte['body'].get('data', '')
                    if datos:
                        import base64
                        cuerpo += base64.urlsafe_b64decode(datos).decode('utf-8')
            return cuerpo
        else:
            datos = payload['body'].get('data', '')
            if datos:
                import base64
                return base64.urlsafe_b64decode(datos).decode('utf-8')
    except Exception as e:
        logger.exception("Error extrayendo cuerpo: %s", e)
    
    return ""


def enviar_correo(destinatario: str, asunto: str, cuerpo: str) -> bool:
    """Envía un correo por Gmail."""
    try:
        servicio = _obtener_servicio_gmail()
        if not servicio:
            return False
        
        import base64
        from email.mime.text import MIMEText
        
        mensaje = MIMEText(cuerpo)
        mensaje['to'] = destinatario
        mensaje['subject'] = asunto
        
        raw = base64.urlsafe_b64encode(mensaje.as_bytes()).decode()
        
        servicio.users().messages().send(
            userId='me',
            body={'raw': raw}
        ).execute()
        
        logger.info("Correo enviado a %s", destinatario)
        return True
        
    except Exception as e:
        logger.exception("Error enviando correo: %s", e)
        return False


def obtener_estadisticas() -> Dict[str, Any]:
    """Obtiene estadísticas de la bandeja de entrada."""
    try:
        servicio = _obtener_servicio_gmail()
        if not servicio:
            return {}
        
        # Contar no leídos
        resultado = servicio.users().messages().list(
            userId='me',
            q='is:unread',
            maxResults=1
        ).execute()
        total_no_leidos = resultado.get('resultSizeEstimate', 0)
        
        # Contar total
        resultado = servicio.users().messages().list(
            userId='me',
            maxResults=1
        ).execute()
        total_correos = resultado.get('resultSizeEstimate', 0)
        
        return {
            'total_correos': total_correos,
            'no_leidos': total_no_leidos,
            'leidos': total_correos - total_no_leidos
        }
        
    except Exception as e:
        logger.exception("Error obteniendo estadísticas: %s", e)
        return {}


def leer_correos(parametro: Optional[str] = None, remitente: str = "") -> str:
    """
    Función puente para el command_router: lee los correos no leídos de
    Gmail y devuelve un resumen con remitente y asunto de cada uno.
    """
    if not HAS_GMAIL:
        return "No tengo instaladas las librerías de Gmail (google-api-python-client / google-auth-oauthlib)."

    correos = obtener_correos_recientes(limite=10, no_leidos=True)
    if not correos:
        return "No tenés correos sin leer, Jefe. ¡Bandeja al día!"

    resultado = f"📬 Tenés {len(correos)} correos sin leer:\n"
    for correo in correos:
        resultado += f"\n- De: {correo['remitente']}\n  Asunto: {correo['asunto']}"
    return resultado


# Integración como skill
def procesar_comando(comando: str, parametro: Optional[str] = None) -> str:
    """Procesa comandos de Gmail."""
    comando = comando.lower().strip()
    
    if "ultimos" in comando or "recientes" in comando or "nuevos" in comando:
        correos = obtener_correos_recientes(limite=5, no_leidos=True)
        if not correos:
            return "No tienes correos sin leer."
        
        resultado = f"Tienes {len(correos)} correos sin leer:\n"
        for correo in correos:
            resultado += f"\n📧 **{correo['asunto']}**\nDe: {correo['remitente']}\n{correo['snippet'][:100]}...\n"
        return resultado
    
    elif "resumir" in comando or "resumen" in comando:
        resumen = resumir_correos()
        return resumen or "No se pudo generar el resumen."
    
    elif "estadisticas" in comando or "stats" in comando:
        stats = obtener_estadisticas()
        return f"📊 **Gmail Stats:**\n- Total: {stats.get('total_correos', 0)}\n- Sin leer: {stats.get('no_leidos', 0)}\n- Leídos: {stats.get('leidos', 0)}"
    
    else:
        return "Comandos disponibles: 'últimos correos', 'resumir correos', 'estadísticas de Gmail'"
