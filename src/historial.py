"""Persistencia del historial de análisis en SQLite."""
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from src.constantes import (
    LIMITE_HISTORIAL_DEFECTO, LIMITE_HISTORIAL_MAX, NOMBRE_BD_DEFECTO,
)
from src.preprocess import EMOCIONES

RUTA_POR_DEFECTO = NOMBRE_BD_DEFECTO
LIMITE_HISTORIAL = LIMITE_HISTORIAL_DEFECTO
LIMITE_MAXIMO = LIMITE_HISTORIAL_MAX

ESQUEMA = """
CREATE TABLE IF NOT EXISTS analisis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha TEXT NOT NULL,
    emocion TEXT NOT NULL,
    confianza REAL NOT NULL,
    todas TEXT NOT NULL
)
"""


@contextmanager
def conexion_bd(ruta):
    """Abre una conexión, confirma los cambios y la cierra siempre."""
    conexion = sqlite3.connect(ruta, timeout=5)
    conexion.row_factory = sqlite3.Row
    try:
        yield conexion
        conexion.commit()
    finally:
        conexion.close()


def inicializar_bd(ruta=RUTA_POR_DEFECTO):
    """Crea la tabla de análisis si no existe."""
    with conexion_bd(ruta) as conexion:
        conexion.execute(ESQUEMA)


def guardar_analisis(resultado, ruta=RUTA_POR_DEFECTO):
    """Guarda un resultado y devuelve la fecha registrada."""
    fecha = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with conexion_bd(ruta) as conexion:
        conexion.execute(
            "INSERT INTO analisis (fecha, emocion, confianza, todas) VALUES (?, ?, ?, ?)",
            (
                fecha,
                resultado["emocion"],
                float(resultado["confianza"]),
                json.dumps(resultado["todas"], ensure_ascii=False),
            ),
        )
    return fecha


def obtener_estadisticas(ruta=RUTA_POR_DEFECTO):
    """Devuelve el total, el conteo por emoción y el promedio de confianza."""
    with conexion_bd(ruta) as conexion:
        total = conexion.execute("SELECT COUNT(*) FROM analisis").fetchone()[0]
        filas = conexion.execute(
            "SELECT emocion, COUNT(*) AS cantidad FROM analisis GROUP BY emocion"
        ).fetchall()
        promedio = conexion.execute(
            "SELECT AVG(confianza) FROM analisis"
        ).fetchone()[0]

    por_emocion = {emocion: 0 for emocion in EMOCIONES}
    for fila in filas:
        por_emocion[fila["emocion"]] = fila["cantidad"]

    return {
        "total": total,
        "por_emocion": por_emocion,
        "promedio_confianza": round(promedio, 2) if promedio is not None else 0.0,
    }


def listar_historial(ruta=RUTA_POR_DEFECTO, limite=LIMITE_HISTORIAL):
    """Devuelve los últimos análisis, del más reciente al más antiguo."""
    with conexion_bd(ruta) as conexion:
        filas = conexion.execute(
            "SELECT id, fecha, emocion, confianza, todas "
            "FROM analisis ORDER BY id DESC LIMIT ?",
            (limite,),
        ).fetchall()

    return [
        {
            "id": fila["id"],
            "fecha": fila["fecha"],
            "emocion": fila["emocion"],
            "confianza": fila["confianza"],
            "todas": json.loads(fila["todas"]),
        }
        for fila in filas
    ]
