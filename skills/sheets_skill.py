# -*- coding: utf-8 -*-
"""
skills/sheets_skill.py
=======================
Integración con Google Sheets para registrar gastos personales.

Requiere:
- google-auth-oauthlib
- google-auth-httplib2
- google-api-python-client
- Archivo de credenciales OAuth en credentials/gmail_credentials.json
  (se reutilizan las mismas credenciales que Gmail/Calendar).

Configuración (.env):
- GOOGLE_SHEETS_ID: ID de la hoja de cálculo donde se registrarán los gastos.
  (Es la parte de la URL entre "/d/" y "/edit" cuando abrís la hoja en el navegador).

La hoja debe tener una pestaña llamada "Gastos" (se crea si no existe) con
columnas: Fecha | Concepto | Monto.
"""

import os
import pickle
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime

from dotenv import load_dotenv

try:
    from google.auth.transport.requests import Request
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    HAS_SHEETS = True
except ImportError:
    HAS_SHEETS = False

load_dotenv()
logger = logging.getLogger("jarvis.skills.sheets")

# Permite lectura y escritura sobre las hojas de cálculo del usuario.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

CREDENTIALS_DIR = os.path.join(os.path.dirname(__file__), "..", "credentials")
CREDENTIALS_FILE = os.path.join(CREDENTIALS_DIR, "gmail_credentials.json")
SHEETS_TOKEN_FILE = os.path.join(CREDENTIALS_DIR, "sheets_token.pickle")

GOOGLE_SHEETS_ID = os.getenv("GOOGLE_SHEETS_ID", "").strip()
NOMBRE_HOJA_GASTOS = "Gastos"


def _obtener_servicio_sheets():
    """Obtiene un cliente autenticado del servicio de Google Sheets."""
    if not HAS_SHEETS:
        logger.error("Librerías de Google Sheets no instaladas (google-api-python-client / google-auth-oauthlib).")
        return None

    try:
        os.makedirs(CREDENTIALS_DIR, exist_ok=True)

        creds = None

        # Cargar token existente si ya se autenticó antes.
        if os.path.exists(SHEETS_TOKEN_FILE):
            with open(SHEETS_TOKEN_FILE, "rb") as token:
                creds = pickle.load(token)

        # Si no hay credenciales validas, se refrescan o se pide login.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CREDENTIALS_FILE):
                    logger.error("Archivo de credenciales no encontrado: %s", CREDENTIALS_FILE)
                    return None

                flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)

            # Guardar el token para no tener que volver a autenticarse.
            with open(SHEETS_TOKEN_FILE, "wb") as token:
                pickle.dump(creds, token)

        servicio = build("sheets", "v4", credentials=creds)
        return servicio

    except Exception as e:
        logger.exception("Error obteniendo servicio de Google Sheets: %s", e)
        return None


def _asegurar_hoja_gastos(servicio) -> bool:
    """
    Verifica que exista la pestaña 'Gastos' con sus encabezados.
    Si no existe, la crea automáticamente.
    """
    try:
        metadata = servicio.spreadsheets().get(spreadsheetId=GOOGLE_SHEETS_ID).execute()
        hojas_existentes = [h["properties"]["title"] for h in metadata.get("sheets", [])]

        if NOMBRE_HOJA_GASTOS not in hojas_existentes:
            # Crear la pestaña "Gastos".
            servicio.spreadsheets().batchUpdate(
                spreadsheetId=GOOGLE_SHEETS_ID,
                body={"requests": [{"addSheet": {"properties": {"title": NOMBRE_HOJA_GASTOS}}}]},
            ).execute()

            # Agregar encabezados.
            servicio.spreadsheets().values().update(
                spreadsheetId=GOOGLE_SHEETS_ID,
                range=f"{NOMBRE_HOJA_GASTOS}!A1:C1",
                valueInputOption="RAW",
                body={"values": [["Fecha", "Concepto", "Monto"]]},
            ).execute()

        return True

    except HttpError as e:
        logger.exception("Error verificando/creando la hoja 'Gastos': %s", e)
        return False
    except Exception as e:
        logger.exception("Error inesperado verificando la hoja 'Gastos': %s", e)
        return False


def registrar_gasto_en_sheet(concepto: str, monto: float) -> bool:
    """
    Agrega una nueva fila con el gasto (fecha, concepto, monto) a la hoja 'Gastos'.

    :param concepto: descripción del gasto (ej: "Supermercado").
    :param monto: monto gastado (ej: 1500.50).
    :return: True si se registró correctamente, False en caso de error.
    """
    try:
        if not GOOGLE_SHEETS_ID:
            logger.error("GOOGLE_SHEETS_ID no está configurado en el .env")
            return False

        servicio = _obtener_servicio_sheets()
        if not servicio:
            return False

        if not _asegurar_hoja_gastos(servicio):
            return False

        fecha = datetime.now().strftime("%Y-%m-%d %H:%M")
        fila = [[fecha, concepto, monto]]

        servicio.spreadsheets().values().append(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"{NOMBRE_HOJA_GASTOS}!A:C",
            valueInputOption="USER_ENTERED",
            insertDataOption="INSERT_ROWS",
            body={"values": fila},
        ).execute()

        logger.info("Gasto registrado: %s - %s", concepto, monto)
        return True

    except Exception as e:
        logger.exception("Error registrando gasto en Sheets: %s", e)
        return False


def listar_gastos_recientes(limite: int = 10) -> List[Dict[str, Any]]:
    """Devuelve los últimos gastos registrados en la hoja."""
    try:
        if not GOOGLE_SHEETS_ID:
            return []

        servicio = _obtener_servicio_sheets()
        if not servicio:
            return []

        resultado = servicio.spreadsheets().values().get(
            spreadsheetId=GOOGLE_SHEETS_ID,
            range=f"{NOMBRE_HOJA_GASTOS}!A2:C",
        ).execute()

        filas = resultado.get("values", [])
        gastos = [
            {"fecha": f[0] if len(f) > 0 else "", "concepto": f[1] if len(f) > 1 else "", "monto": f[2] if len(f) > 2 else ""}
            for f in filas
        ]
        return gastos[-limite:][::-1]

    except Exception as e:
        logger.exception("Error listando gastos: %s", e)
        return []


def _parsear_concepto_y_monto(texto: str) -> Optional[tuple]:
    """
    Intenta separar el texto libre en (concepto, monto).
    Acepta formatos como: "Supermercado 1500", "1500 Supermercado", "Nafta: 800".
    """
    import re

    texto = texto.strip()
    if not texto:
        return None

    # Busca el primer numero (con decimales opcionales) en el texto.
    match = re.search(r"(\d+[.,]?\d*)", texto)
    if not match:
        return None

    monto_str = match.group(1).replace(",", ".")
    try:
        monto = float(monto_str)
    except ValueError:
        return None

    # El concepto es el resto del texto sin el numero ni caracteres sueltos.
    concepto = (texto[:match.start()] + texto[match.end():]).strip(" :-$")
    if not concepto:
        concepto = "Gasto sin descripción"

    return concepto, monto


def registrar_gasto(texto: str, remitente: str = "") -> str:
    """
    Función puente usada por el command_router. Recibe texto libre con el
    concepto y el monto del gasto (ej: "Supermercado 1500") y lo registra
    en Google Sheets.
    """
    if not HAS_SHEETS:
        return "No tengo instaladas las librerías de Google para usar Sheets."

    if not GOOGLE_SHEETS_ID or GOOGLE_SHEETS_ID == "cambia_esto":
        return "Todavía no configuraste el ID de tu hoja de Google Sheets (GOOGLE_SHEETS_ID) en el .env, Jefe."

    datos = _parsear_concepto_y_monto(texto or "")
    if not datos:
        return "Decime el concepto y el monto del gasto, por ejemplo: 'Supermercado 1500'."

    concepto, monto = datos
    exito = registrar_gasto_en_sheet(concepto, monto)

    if exito:
        return f"Listo, Jefe. Registré el gasto '{concepto}' por ${monto:,.2f} en la hoja de cálculo."
    return "No pude registrar el gasto en Google Sheets. Revisá la configuración de credenciales."


def procesar_comando(comando: str, parametro: Optional[str] = None) -> str:
    """Procesa comandos de Sheets (uso independiente/manual)."""
    comando = (comando or "").lower().strip()

    if "gasto" in comando or "registrar" in comando:
        return registrar_gasto(parametro or comando)

    if "listar" in comando or "ver gastos" in comando:
        gastos = listar_gastos_recientes(10)
        if not gastos:
            return "No hay gastos registrados todavía."
        resultado = "💰 **Últimos gastos:**\n"
        for g in gastos:
            resultado += f"\n- {g['fecha']}: {g['concepto']} — ${g['monto']}"
        return resultado

    return "Comandos disponibles: 'registrar gasto <concepto> <monto>', 'listar gastos'."
