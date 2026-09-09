# -*- coding: utf-8 -*-
"""
memory.py
=========
Modulo de memoria persistente de JARVIS.

Usa SQLite como base de datos y la extension FTS5 (Full Text Search)
para poder buscar conversaciones y "nodos" de conocimiento por contenido.

Estructura:
- mensajes: historial crudo de la conversacion (usuario / asistente).
- mensajes_fts: indice de texto completo sobre "mensajes".
- nodos: unidades de conocimiento/memoria a largo plazo (hechos, notas,
  recuerdos importantes) que JARVIS puede crear y recuperar luego.
- nodos_fts: indice de texto completo sobre "nodos".

Todas las funciones publicas manejan sus propias excepciones y devuelven
valores seguros (None / listas vacias) en caso de error, registrando el
problema en el logger del modulo.
"""

import sqlite3
import logging
import os
from datetime import datetime
from contextlib import contextmanager
from typing import Optional, List, Dict, Any

logger = logging.getLogger("jarvis.memory")

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "jarvis.db")


@contextmanager
def _conexion():
    """
    Context manager que entrega una conexion SQLite con row_factory
    configurado para devolver diccionarios, y se asegura de cerrarla
    siempre (incluso si ocurre un error).
    """
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """
    Crea las tablas necesarias si no existen. Debe llamarse una vez
    al iniciar el servidor (ver server.py -> evento startup).
    """
    try:
        with _conexion() as conn:
            cur = conn.cursor()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS mensajes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    remitente TEXT NOT NULL,
                    rol TEXT NOT NULL CHECK(rol IN ('usuario', 'asistente', 'sistema')),
                    contenido TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    metadata TEXT
                )
            """)

            # Tabla virtual FTS5 para busqueda de texto completo en mensajes.
            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS mensajes_fts USING fts5(
                    contenido, content='mensajes', content_rowid='id'
                )
            """)

            # Triggers para mantener sincronizado el indice FTS con la tabla real.
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS mensajes_ai AFTER INSERT ON mensajes BEGIN
                    INSERT INTO mensajes_fts(rowid, contenido) VALUES (new.id, new.contenido);
                END;
            """)
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS mensajes_ad AFTER DELETE ON mensajes BEGIN
                    INSERT INTO mensajes_fts(mensajes_fts, rowid, contenido) VALUES('delete', old.id, old.contenido);
                END;
            """)
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS mensajes_au AFTER UPDATE ON mensajes BEGIN
                    INSERT INTO mensajes_fts(mensajes_fts, rowid, contenido) VALUES('delete', old.id, old.contenido);
                    INSERT INTO mensajes_fts(rowid, contenido) VALUES (new.id, new.contenido);
                END;
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS nodos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT NOT NULL,
                    titulo TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    tags TEXT,
                    timestamp TEXT NOT NULL
                )
            """)

            cur.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS nodos_fts USING fts5(
                    titulo, contenido, tags, content='nodos', content_rowid='id'
                )
            """)
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS nodos_ai AFTER INSERT ON nodos BEGIN
                    INSERT INTO nodos_fts(rowid, titulo, contenido, tags)
                    VALUES (new.id, new.titulo, new.contenido, new.tags);
                END;
            """)
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS nodos_ad AFTER DELETE ON nodos BEGIN
                    INSERT INTO nodos_fts(nodos_fts, rowid, titulo, contenido, tags)
                    VALUES('delete', old.id, old.titulo, old.contenido, old.tags);
                END;
            """)
            cur.execute("""
                CREATE TRIGGER IF NOT EXISTS nodos_au AFTER UPDATE ON nodos BEGIN
                    INSERT INTO nodos_fts(nodos_fts, rowid, titulo, contenido, tags)
                    VALUES('delete', old.id, old.titulo, old.contenido, old.tags);
                    INSERT INTO nodos_fts(rowid, titulo, contenido, tags)
                    VALUES (new.id, new.titulo, new.contenido, new.tags);
                END;
            """)

            # Tabla de estado neuroquimico (una fila, se va actualizando).
            cur.execute("""
                CREATE TABLE IF NOT EXISTS estado_animo (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    dopamina REAL DEFAULT 50,
                    serotonina REAL DEFAULT 50,
                    cortisol REAL DEFAULT 20,
                    oxitocina REAL DEFAULT 50,
                    ultima_actualizacion TEXT
                )
            """)
            cur.execute("INSERT OR IGNORE INTO estado_animo (id, ultima_actualizacion) VALUES (1, ?)",
                        (datetime.utcnow().isoformat(),))

            cur.execute("""
                CREATE TABLE IF NOT EXISTS memorias (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tipo TEXT NOT NULL CHECK(tipo IN ('hecho', 'preferencia', 'evento', 'relacion')),
                    titulo TEXT NOT NULL,
                    contenido TEXT NOT NULL,
                    tags TEXT,
                    timestamp TEXT NOT NULL
                )
            """)

        logger.info("Base de datos inicializada correctamente en %s", DB_PATH)
    except Exception as e:
        logger.exception("Error inicializando la base de datos: %s", e)


def guardar_mensaje(remitente: str, rol: str, contenido: str, metadata: Optional[str] = None) -> Optional[int]:
    """
    Guarda un mensaje en el historial de conversacion.

    :param remitente: identificador del remitente (numero de WhatsApp o "jarvis").
    :param rol: 'usuario' | 'asistente' | 'sistema'
    :param contenido: texto del mensaje.
    :param metadata: informacion adicional en formato string/JSON (opcional).
    :return: id del mensaje insertado, o None si fallo.
    """
    try:
        with _conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO mensajes (remitente, rol, contenido, timestamp, metadata) VALUES (?, ?, ?, ?, ?)",
                (remitente, rol, contenido, datetime.utcnow().isoformat(), metadata)
            )
            return cur.lastrowid
    except Exception as e:
        logger.exception("Error guardando mensaje: %s", e)
        return None


def crear_nodo(tipo: str, titulo: str, contenido: str, tags: Optional[str] = None) -> Optional[int]:
    """
    Crea un nodo de memoria a largo plazo (un hecho, una nota, un recuerdo).

    :param tipo: categoria del nodo (ej: 'nota', 'preferencia', 'evento').
    :param titulo: titulo corto descriptivo.
    :param contenido: contenido completo del nodo.
    :param tags: etiquetas separadas por coma (opcional).
    :return: id del nodo creado, o None si fallo.
    """
    try:
        with _conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO nodos (tipo, titulo, contenido, tags, timestamp) VALUES (?, ?, ?, ?, ?)",
                (tipo, titulo, contenido, tags, datetime.utcnow().isoformat())
            )
            return cur.lastrowid
    except Exception as e:
        logger.exception("Error creando nodo: %s", e)
        return None


def buscar_contexto(consulta: str, limite: int = 5) -> Dict[str, List[Dict[str, Any]]]:
    """
    Busca contexto relevante (mensajes y nodos) usando FTS5 a partir
    de una consulta en texto libre. Util para dar contexto al LLM
    antes de responder.

    :param consulta: texto a buscar.
    :param limite: cantidad maxima de resultados por tabla.
    :return: diccionario con listas 'mensajes' y 'nodos'.
    """
    resultado = {"mensajes": [], "nodos": []}
    if not consulta or not consulta.strip():
        return resultado

    # FTS5 usa una sintaxis de consulta especial; escapamos comillas dobles
    # y envolvemos cada termino para hacer una busqueda tipo "OR" simple.
    terminos = consulta.replace('"', ' ').split()
    if not terminos:
        return resultado
    consulta_fts = " OR ".join(f'"{t}"' for t in terminos)

    try:
        with _conexion() as conn:
            cur = conn.cursor()

            cur.execute("""
                SELECT m.id, m.remitente, m.rol, m.contenido, m.timestamp
                FROM mensajes_fts
                JOIN mensajes m ON m.id = mensajes_fts.rowid
                WHERE mensajes_fts MATCH ?
                ORDER BY m.id DESC
                LIMIT ?
            """, (consulta_fts, limite))
            resultado["mensajes"] = [dict(r) for r in cur.fetchall()]

            cur.execute("""
                SELECT n.id, n.tipo, n.titulo, n.contenido, n.tags, n.timestamp
                FROM nodos_fts
                JOIN nodos n ON n.id = nodos_fts.rowid
                WHERE nodos_fts MATCH ?
                ORDER BY n.id DESC
                LIMIT ?
            """, (consulta_fts, limite))
            resultado["nodos"] = [dict(r) for r in cur.fetchall()]

    except sqlite3.OperationalError as e:
        # Puede ocurrir si la consulta FTS queda mal formada; degradamos con log.
        logger.warning("Consulta FTS invalida ('%s'): %s", consulta, e)
    except Exception as e:
        logger.exception("Error buscando contexto: %s", e)

    return resultado


def guardar_memoria(tipo: str, titulo: str, contenido: str, tags: str = "") -> Optional[int]:
    """Guarda un recuerdo estructurado de largo plazo."""
    tipos_validos = {"hecho", "preferencia", "evento", "relacion"}
    if tipo not in tipos_validos:
        raise ValueError(f"Tipo de memoria inválido: {tipo}")
    try:
        with _conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO memorias (tipo, titulo, contenido, tags, timestamp) VALUES (?, ?, ?, ?, ?)",
                (tipo, titulo.strip(), contenido.strip(), tags, datetime.utcnow().isoformat()),
            )
            return cur.lastrowid
    except Exception as e:
        logger.exception("Error guardando memoria: %s", e)
        return None


def buscar_memorias(consulta: str, limite: int = 10) -> List[Dict[str, Any]]:
    """Busca recuerdos estructurados por título, contenido o etiquetas."""
    if not consulta.strip():
        return []
    terminos = [f"%{termino}%" for termino in consulta.split()]
    clausulas = " OR ".join("titulo LIKE ? OR contenido LIKE ? OR tags LIKE ?" for _ in terminos)
    parametros = [valor for termino in terminos for valor in (termino, termino, termino)]
    try:
        with _conexion() as conn:
            cur = conn.cursor()
            cur.execute(
                f"SELECT * FROM memorias WHERE {clausulas} ORDER BY id DESC LIMIT ?",
                (*parametros, limite),
            )
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.exception("Error buscando memorias: %s", e)
        return []


def limpiar_historial(remitente: str, max_turns: int = 15) -> None:
    """Conserva solo los últimos max_turns mensajes del remitente."""
    try:
        with _conexion() as conn:
            conn.execute(
                "DELETE FROM mensajes WHERE remitente = ? AND id NOT IN "
                "(SELECT id FROM mensajes WHERE remitente = ? ORDER BY id DESC LIMIT ?)",
                (remitente, remitente, max_turns),
            )
    except Exception as e:
        logger.exception("Error limpiando historial de %s: %s", remitente, e)


def obtener_historial(remitente: Optional[str] = None, limite: int = 20) -> List[Dict[str, Any]]:
    """
    Devuelve los ultimos N mensajes de la conversacion (globales o de
    un remitente en particular), en orden cronologico ascendente.
    """
    try:
        with _conexion() as conn:
            cur = conn.cursor()
            if remitente:
                cur.execute("""
                    SELECT * FROM (
                        SELECT * FROM mensajes WHERE remitente = ? ORDER BY id DESC LIMIT ?
                    ) ORDER BY id ASC
                """, (remitente, limite))
            else:
                cur.execute("""
                    SELECT * FROM (
                        SELECT * FROM mensajes ORDER BY id DESC LIMIT ?
                    ) ORDER BY id ASC
                """, (limite,))
            return [dict(r) for r in cur.fetchall()]
    except Exception as e:
        logger.exception("Error obteniendo historial: %s", e)
        return []


def obtener_ultima_interaccion() -> Optional[datetime]:
    """Devuelve el timestamp (datetime) del ultimo mensaje registrado, o None."""
    try:
        with _conexion() as conn:
            cur = conn.cursor()
            cur.execute("SELECT timestamp FROM mensajes ORDER BY id DESC LIMIT 1")
            fila = cur.fetchone()
            if fila:
                return datetime.fromisoformat(fila["timestamp"])
            return None
    except Exception as e:
        logger.exception("Error obteniendo ultima interaccion: %s", e)
        return None
