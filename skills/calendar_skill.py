# -*- coding: utf-8 -*-
"""
skills/calendar_skill.py
========================
Integración de Google Calendar para gestionar eventos y tareas.

Requiere:
- google-auth-oauthlib
- google-auth-httplib2
- google-api-python-client

Usa las mismas credenciales de Gmail (credentials/gmail_credentials.json)
"""

import os
import pickle
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    HAS_CALENDAR = True
except ImportError:
    HAS_CALENDAR = False

from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger("jarvis.skills.calendar")

SCOPES = ["https://www.googleapis.com/auth/calendar"]

CREDENTIALS_DIR = os.path.join(os.path.dirname(__file__), "..", "credentials")
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, "gmail_credentials.json")
CALENDAR_TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "calendar_token.pickle")


def _obtener_servicio_calendar():
    """Obtiene un cliente autenticado del servicio de Google Calendar."""
    if not HAS_CALENDAR:
        logger.error("Librerías de Google Calendar no instaladas.")
        return None
    
    try:
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)
        
        creds = None
        
        # Cargar token existente
        if os.path.exists(CALENDAR_TOKEN_FILE):
            with open(CALENDAR_TOKEN_FILE, 'rb') as token:
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
            with open(CALENDAR_TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)
        
        servicio = build('calendar', 'v3', credentials=creds)
        return servicio
        
    except Exception as e:
        logger.exception("Error obteniendo servicio de Calendar: %s", e)
        return None


def obtener_proximos_eventos(limite: int = 10, dias: int = 7) -> List[Dict[str, Any]]:
    """
    Obtiene los próximos eventos.
    
    :param limite: cantidad máxima de eventos
    :param dias: número de días a partir de ahora
    :return: lista de eventos
    """
    try:
        servicio = _obtener_servicio_calendar()
        if not servicio:
            return []
        
        ahora = datetime.utcnow()
        hasta = ahora + timedelta(days=dias)
        
        eventos = servicio.events().list(
            calendarId='primary',
            timeMin=ahora.isoformat() + 'Z',
            timeMax=hasta.isoformat() + 'Z',
            maxResults=limite,
            singleEvents=True,
            orderBy='startTime'
        ).execute()
        
        items = eventos.get('items', [])
        
        resultado = []
        for evento in items:
            inicio = evento['start'].get('dateTime', evento['start'].get('date'))
            fin = evento['end'].get('dateTime', evento['end'].get('date'))
            
            resultado.append({
                'id': evento['id'],
                'titulo': evento.get('summary', 'Sin título'),
                'inicio': inicio,
                'fin': fin,
                'descripcion': evento.get('description', ''),
                'ubicacion': evento.get('location', ''),
                'asistentes': len(evento.get('attendees', [])),
                'enlace_video': evento.get('conferenceData', {}).get('entryPoints', [])
            })
        
        return resultado
        
    except Exception as e:
        logger.exception("Error obteniendo eventos: %s", e)
        return []


def crear_evento(
    titulo: str,
    fecha_inicio: str,
    fecha_fin: str,
    descripcion: Optional[str] = None,
    ubicacion: Optional[str] = None,
    asistentes: Optional[List[str]] = None
) -> Optional[str]:
    """
    Crea un nuevo evento en Google Calendar.
    
    :param titulo: título del evento
    :param fecha_inicio: fecha y hora de inicio (ISO format o "2024-01-15 14:00")
    :param fecha_fin: fecha y hora de fin
    :param descripcion: descripción del evento
    :param ubicacion: ubicación del evento
    :param asistentes: lista de emails de asistentes
    :return: ID del evento creado o None
    """
    try:
        servicio = _obtener_servicio_calendar()
        if not servicio:
            return None
        
        # Parsear fechas
        if isinstance(fecha_inicio, str) and ' ' in fecha_inicio:
            fecha_inicio = fecha_inicio.replace(' ', 'T')
        if isinstance(fecha_fin, str) and ' ' in fecha_fin:
            fecha_fin = fecha_fin.replace(' ', 'T')
        
        evento = {
            'summary': titulo,
            'description': descripcion or '',
            'location': ubicacion or '',
            'start': {
                'dateTime': fecha_inicio,
                'timeZone': 'UTC'
            },
            'end': {
                'dateTime': fecha_fin,
                'timeZone': 'UTC'
            }
        }
        
        if asistentes:
            evento['attendees'] = [{'email': email} for email in asistentes]
        
        evento_creado = servicio.events().insert(
            calendarId='primary',
            body=evento,
            sendNotifications=True
        ).execute()
        
        logger.info("Evento creado: %s", evento_creado['id'])
        return evento_creado['id']
        
    except Exception as e:
        logger.exception("Error creando evento: %s", e)
        return None


def actualizar_evento(evento_id: str, cambios: Dict[str, Any]) -> bool:
    """Actualiza un evento existente."""
    try:
        servicio = _obtener_servicio_calendar()
        if not servicio:
            return False
        
        # Obtener evento actual
        evento = servicio.events().get(
            calendarId='primary',
            eventId=evento_id
        ).execute()
        
        # Aplicar cambios
        if 'titulo' in cambios:
            evento['summary'] = cambios['titulo']
        if 'descripcion' in cambios:
            evento['description'] = cambios['descripcion']
        if 'ubicacion' in cambios:
            evento['location'] = cambios['ubicacion']
        
        # Actualizar
        servicio.events().update(
            calendarId='primary',
            eventId=evento_id,
            body=evento
        ).execute()
        
        logger.info("Evento actualizado: %s", evento_id)
        return True
        
    except Exception as e:
        logger.exception("Error actualizando evento: %s", e)
        return False


def eliminar_evento(evento_id: str) -> bool:
    """Elimina un evento."""
    try:
        servicio = _obtener_servicio_calendar()
        if not servicio:
            return False
        
        servicio.events().delete(
            calendarId='primary',
            eventId=evento_id
        ).execute()
        
        logger.info("Evento eliminado: %s", evento_id)
        return True
        
    except Exception as e:
        logger.exception("Error eliminando evento: %s", e)
        return False


def obtener_disponibilidad(num_dias: int = 30) -> Dict[str, Any]:
    """
    Obtiene un resumen de disponibilidad (horas ocupadas vs libres).
    
    :param num_dias: número de días a analizar
    """
    try:
        eventos = obtener_proximos_eventos(limite=100, dias=num_dias)
        
        horas_ocupadas = 0
        horas_totales = num_dias * 24
        
        for evento in eventos:
            try:
                inicio = datetime.fromisoformat(evento['inicio'].replace('Z', '+00:00'))
                fin = datetime.fromisoformat(evento['fin'].replace('Z', '+00:00'))
                duracion = (fin - inicio).total_seconds() / 3600
                horas_ocupadas += duracion
            except:
                pass
        
        porcentaje_ocupacion = (horas_ocupadas / horas_totales * 100) if horas_totales > 0 else 0
        
        return {
            'horas_ocupadas': round(horas_ocupadas, 1),
            'horas_disponibles': round(horas_totales - horas_ocupadas, 1),
            'porcentaje_ocupacion': round(porcentaje_ocupacion, 1),
            'eventos_totales': len(eventos)
        }
        
    except Exception as e:
        logger.exception("Error calculando disponibilidad: %s", e)
        return {}


def ver_eventos(parametro: Optional[str] = None, remitente: str = "") -> str:
    """
    Función puente para el command_router: muestra los próximos 5 eventos
    del calendario principal de Google Calendar.
    """
    if not HAS_CALENDAR:
        return "No tengo instaladas las librerías de Google Calendar (google-api-python-client / google-auth-oauthlib)."

    eventos = obtener_proximos_eventos(limite=5, dias=30)
    if not eventos:
        return "No tenés eventos próximos en tu calendario, Jefe."

    resultado = f"📅 Tus próximos {len(eventos)} eventos:\n"
    for evento in eventos:
        resultado += f"\n- **{evento['titulo']}**\n  Cuándo: {evento['inicio']}"
        if evento["ubicacion"]:
            resultado += f"\n  Dónde: {evento['ubicacion']}"
    return resultado


def agregar_evento(parametro: Optional[str] = None, remitente: str = "") -> str:
    """
    Función puente para el command_router: crea un evento básico en Google
    Calendar a partir de texto libre.

    Formato esperado (simple, separado por " | "):
        "Título | 2024-06-15 14:00 | 2024-06-15 15:00"
    Si no se especifica hora de fin, se asume 1 hora de duración.
    Si no se especifica fecha, se pide más información al usuario.
    """
    if not HAS_CALENDAR:
        return "No tengo instaladas las librerías de Google Calendar (google-api-python-client / google-auth-oauthlib)."

    if not parametro or not parametro.strip():
        return (
            "Decime el evento con este formato, Jefe: "
            "'Título | AAAA-MM-DD HH:MM | AAAA-MM-DD HH:MM' (la hora de fin es opcional)."
        )

    partes = [p.strip() for p in parametro.split("|")]
    if len(partes) < 2:
        return (
            "Me falta información. Usá el formato: "
            "'Título | AAAA-MM-DD HH:MM | AAAA-MM-DD HH:MM' (la hora de fin es opcional)."
        )

    titulo = partes[0]
    fecha_inicio = partes[1]

    if len(partes) >= 3 and partes[2]:
        fecha_fin = partes[2]
    else:
        # Si no se especifica fin, se asume una hora de duración.
        try:
            inicio_dt = datetime.fromisoformat(fecha_inicio.replace(" ", "T"))
            fecha_fin = (inicio_dt + timedelta(hours=1)).isoformat()
        except ValueError:
            return "No pude interpretar la fecha. Usá el formato 'AAAA-MM-DD HH:MM'."

    evento_id = crear_evento(titulo=titulo, fecha_inicio=fecha_inicio, fecha_fin=fecha_fin)

    if evento_id:
        return f"Listo, Jefe. Creé el evento '{titulo}' para el {fecha_inicio}."
    return "No pude crear el evento en Google Calendar. Revisá la configuración de credenciales."


def procesar_comando(comando: str, parametro: Optional[str] = None) -> str:
    """Procesa comandos de Calendar."""
    comando = comando.lower().strip()
    
    if "proximos" in comando or "siguiente" in comando or "eventos" in comando:
        eventos = obtener_proximos_eventos(limite=5)
        if not eventos:
            return "No tienes eventos próximos."
        
        resultado = f"📅 Tus próximos {len(eventos)} eventos:\n"
        for evento in eventos:
            resultado += f"\n**{evento['titulo']}**\n"
            resultado += f"   Cuándo: {evento['inicio']}\n"
            if evento['ubicacion']:
                resultado += f"   Dónde: {evento['ubicacion']}\n"
        
        return resultado
    
    elif "disponibilidad" in comando or "ocupación" in comando:
        disponibilidad = obtener_disponibilidad(30)
        return f"""📊 **Disponibilidad (30 días):**
- Horas ocupadas: {disponibilidad.get('horas_ocupadas', 0)}h
- Horas disponibles: {disponibilidad.get('horas_disponibles', 0)}h
- Ocupación: {disponibilidad.get('porcentaje_ocupacion', 0)}%
- Eventos: {disponibilidad.get('eventos_totales', 0)}"""
    
    elif "crear" in comando or "nuevo" in comando:
        return "Para crear un evento, proporciona: título, fecha y hora."
    
    else:
        return "Comandos disponibles: 'próximos eventos', 'disponibilidad', 'crear evento'"
