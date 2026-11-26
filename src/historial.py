"""Persistencia en SQLite: sesiones de clase, lecturas y detecciones.

Modelo (ver db/esquema.sql):

    sesion (1) ---< lectura (1) ---< deteccion

- sesion: una clase (curso, grado y sección, docente, inicio y fin).
- lectura: cada análisis, de un cuadro de la cámara o de una fotografía.
- deteccion: cada rostro de una lectura, con su emoción y la distribución.

No se guardan imágenes ni datos que identifiquen a un estudiante.
"""
import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from src.constantes import (
    LIMITE_HISTORIAL_DEFECTO, LIMITE_HISTORIAL_MAX, NOMBRE_BD_DEFECTO,
)
from src.preprocess import EMOCIONES

RUTA_POR_DEFECTO = NOMBRE_BD_DEFECTO
LIMITE_HISTORIAL = LIMITE_HISTORIAL_DEFECTO
LIMITE_MAXIMO = LIMITE_HISTORIAL_MAX
RUTA_ESQUEMA = Path(__file__).resolve().parent.parent / "db" / "esquema.sql"
VERSION_ESQUEMA = 2
ESPERA_BLOQUEO_S = 5
DECIMALES = 2
PORCENTAJE_MINIMO = 0.0
PORCENTAJE_MAXIMO = 100.0

FUENTE_CAMARA = "camara"
FUENTE_IMAGEN = "imagen"
FUENTE_ANTERIOR = "anterior"
FUENTES = (FUENTE_CAMARA, FUENTE_IMAGEN, FUENTE_ANTERIOR)

# Tabla de la versión 1 (un registro suelto por análisis) y su respaldo
TABLA_ANTERIOR = "analisis"
TABLA_RESPALDO = "analisis_v1"
CURSO_ANTERIOR = "Historial anterior"
GRADO_ANTERIOR = "Sin datos"

COLUMNAS_EMOCIONES = ", ".join(EMOCIONES)
COLUMNAS_SESION = "s.id, s.curso, s.grado_seccion, s.docente, s.inicio, s.fin"


@contextmanager
def conexion_bd(ruta):
    """Abre una conexión con claves foráneas activas, confirma y cierra siempre."""
    conexion = sqlite3.connect(ruta, timeout=ESPERA_BLOQUEO_S)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    try:
        yield conexion
        conexion.commit()
    finally:
        conexion.close()


def ahora_utc():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def limitar_porcentaje(valor):
    return min(PORCENTAJE_MAXIMO, max(PORCENTAJE_MINIMO, float(valor)))


# ---------- Esquema y migración ----------

def inicializar_bd(ruta=RUTA_POR_DEFECTO):
    """Crea las tablas si no existen y migra los datos de la versión 1."""
    with conexion_bd(ruta) as conexion:
        conexion.executescript(RUTA_ESQUEMA.read_text(encoding="utf-8"))
        _migrar_tabla_anterior(conexion)
        conexion.execute(f"PRAGMA user_version = {VERSION_ESQUEMA}")


def version_esquema(ruta=RUTA_POR_DEFECTO):
    with conexion_bd(ruta) as conexion:
        return conexion.execute("PRAGMA user_version").fetchone()[0]


def _existe_tabla(conexion, nombre):
    fila = conexion.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", (nombre,),
    ).fetchone()
    return fila is not None


def _migrar_tabla_anterior(conexion):
    """Pasa los registros de la tabla `analisis` a una sesión «Historial anterior».

    La tabla original se conserva como `analisis_v1` por si hiciera falta
    revisarla. Devuelve cuántos registros migró.
    """
    if not _existe_tabla(conexion, TABLA_ANTERIOR):
        return 0
    filas = [
        fila for fila in conexion.execute(
            f"SELECT fecha, emocion, confianza, todas FROM {TABLA_ANTERIOR} ORDER BY id"
        ).fetchall()
        if fila["emocion"] in EMOCIONES
    ]
    if filas:
        fechas = [fila["fecha"] for fila in filas]
        cursor = conexion.execute(
            "INSERT INTO sesion (curso, grado_seccion, docente, inicio, fin) VALUES (?, ?, NULL, ?, ?)",
            (CURSO_ANTERIOR, GRADO_ANTERIOR, min(fechas), max(fechas)),
        )
        for fila in filas:
            rostro = {
                "emocion": fila["emocion"],
                "confianza": fila["confianza"],
                "todas": json.loads(fila["todas"]),
            }
            _insertar_lectura(
                conexion, cursor.lastrowid, fila["fecha"], FUENTE_ANTERIOR, [rostro], fila["emocion"],
            )
    if _existe_tabla(conexion, TABLA_RESPALDO):
        conexion.execute(f"INSERT INTO {TABLA_RESPALDO} SELECT * FROM {TABLA_ANTERIOR}")
        conexion.execute(f"DROP TABLE {TABLA_ANTERIOR}")
    else:
        conexion.execute(f"ALTER TABLE {TABLA_ANTERIOR} RENAME TO {TABLA_RESPALDO}")
    return len(filas)


# ---------- Sesiones de clase ----------

def _texto_obligatorio(valor, campo):
    texto = (valor or "").strip()
    if not texto:
        raise ValueError(f"Falta el dato: {campo}")
    return texto


def iniciar_sesion(curso, grado_seccion, docente=None, ruta=RUTA_POR_DEFECTO):
    """Abre una sesión de clase y devuelve su id.

    Solo puede haber una sesión abierta: si queda otra abierta (por ejemplo,
    porque se cerró la aplicación sin terminarla), se cierra primero.
    """
    curso = _texto_obligatorio(curso, "curso")
    grado_seccion = _texto_obligatorio(grado_seccion, "grado y sección")
    docente = (docente or "").strip() or None
    ahora = ahora_utc()
    with conexion_bd(ruta) as conexion:
        conexion.execute("UPDATE sesion SET fin = ? WHERE fin IS NULL", (ahora,))
        cursor = conexion.execute(
            "INSERT INTO sesion (curso, grado_seccion, docente, inicio) VALUES (?, ?, ?, ?)",
            (curso, grado_seccion, docente, ahora),
        )
        return cursor.lastrowid


def cerrar_sesion(sesion_id, ruta=RUTA_POR_DEFECTO):
    """Cierra la sesión indicada. Devuelve False si no existía o ya estaba cerrada."""
    with conexion_bd(ruta) as conexion:
        cursor = conexion.execute(
            "UPDATE sesion SET fin = ? WHERE id = ? AND fin IS NULL", (ahora_utc(), sesion_id),
        )
        return cursor.rowcount == 1


def _consulta_sesiones(condicion="", parametros=(), limite=LIMITE_MAXIMO, ruta=RUTA_POR_DEFECTO):
    with conexion_bd(ruta) as conexion:
        filas = conexion.execute(
            f"SELECT {COLUMNAS_SESION}, COUNT(DISTINCT l.id) AS lecturas, COUNT(d.id) AS detecciones "
            "FROM sesion s "
            "LEFT JOIN lectura l ON l.sesion_id = s.id "
            "LEFT JOIN deteccion d ON d.lectura_id = l.id "
            f"{condicion} GROUP BY s.id ORDER BY s.id DESC LIMIT ?",
            (*parametros, limite),
        ).fetchall()
    return [{**dict(fila), "activa": fila["fin"] is None} for fila in filas]


def listar_sesiones(ruta=RUTA_POR_DEFECTO, limite=LIMITE_MAXIMO):
    """Sesiones de la más reciente a la más antigua, con lecturas y detecciones."""
    return _consulta_sesiones(limite=limite, ruta=ruta)


def obtener_sesion(sesion_id, ruta=RUTA_POR_DEFECTO):
    sesiones = _consulta_sesiones("WHERE s.id = ?", (sesion_id,), ruta=ruta)
    return sesiones[0] if sesiones else None


def sesion_activa(ruta=RUTA_POR_DEFECTO):
    """La sesión abierta, o None si no hay ninguna."""
    sesiones = _consulta_sesiones("WHERE s.fin IS NULL", limite=1, ruta=ruta)
    return sesiones[0] if sesiones else None


# ---------- Lecturas y detecciones ----------

def _insertar_lectura(conexion, sesion_id, fecha, fuente, rostros, predominante):
    cursor = conexion.execute(
        "INSERT INTO lectura (sesion_id, fecha, fuente, total_rostros, predominante) VALUES (?, ?, ?, ?, ?)",
        (sesion_id, fecha, fuente, len(rostros), predominante),
    )
    lectura_id = cursor.lastrowid
    marcadores = ", ".join("?" * (len(EMOCIONES) + 3))
    conexion.executemany(
        f"INSERT INTO deteccion (lectura_id, emocion, confianza, {COLUMNAS_EMOCIONES}) VALUES ({marcadores})",
        [
            (
                lectura_id, rostro["emocion"], limitar_porcentaje(rostro["confianza"]),
                *[limitar_porcentaje(rostro["todas"].get(emocion, 0.0)) for emocion in EMOCIONES],
            )
            for rostro in rostros
        ],
    )
    return lectura_id


def _avisar(rostros):
    try:
        from src.notificaciones import notificar_rostros
    except ImportError:
        from notificaciones import notificar_rostros
    notificar_rostros(rostros)


def guardar_lectura(resultado, fuente, sesion_id=None, ruta=RUTA_POR_DEFECTO):
    """Guarda una lectura con todos sus rostros y devuelve el id de la lectura.

    `resultado` tiene la forma de AnalizadorAula.analizar_cuadro:
    {"rostros": [{"emocion", "confianza", "todas", ...}], "predominante": ...}.
    Una lectura sin rostros también se guarda (total_rostros = 0).
    """
    if fuente not in FUENTES:
        raise ValueError(f"Fuente no válida: {fuente}")
    with conexion_bd(ruta) as conexion:
        lectura_id = _insertar_lectura(
            conexion, sesion_id, ahora_utc(), fuente, resultado["rostros"], resultado.get("predominante"),
        )
    _avisar(resultado["rostros"])
    return lectura_id


def guardar_analisis(resultado, ruta=RUTA_POR_DEFECTO, sesion_id=None):
    """Guarda el análisis de una fotografía (un rostro) y devuelve la fecha."""
    fecha = ahora_utc()
    with conexion_bd(ruta) as conexion:
        _insertar_lectura(conexion, sesion_id, fecha, FUENTE_IMAGEN, [resultado], resultado["emocion"])
    _avisar([resultado])
    return fecha


def _filtro_sesion(sesion_id):
    if sesion_id is None:
        return "", ()
    return "WHERE l.sesion_id = ?", (sesion_id,)


def listar_historial(ruta=RUTA_POR_DEFECTO, limite=LIMITE_HISTORIAL, sesion_id=None):
    """Últimas detecciones, de la más reciente a la más antigua."""
    condicion, parametros = _filtro_sesion(sesion_id)
    with conexion_bd(ruta) as conexion:
        filas = conexion.execute(
            "SELECT d.id, l.fecha, d.emocion, d.confianza, l.sesion_id, l.fuente, d.lectura_id, "
            f"{', '.join('d.' + emocion for emocion in EMOCIONES)} "
            "FROM deteccion d JOIN lectura l ON l.id = d.lectura_id "
            f"{condicion} ORDER BY l.fecha DESC, d.id DESC LIMIT ?",
            (*parametros, limite),
        ).fetchall()
    return [
        {
            "id": fila["id"],
            "fecha": fila["fecha"],
            "emocion": fila["emocion"],
            "confianza": fila["confianza"],
            "todas": {emocion: fila[emocion] for emocion in EMOCIONES},
            "sesion_id": fila["sesion_id"],
            "fuente": fila["fuente"],
            "lectura_id": fila["lectura_id"],
        }
        for fila in filas
    ]


def obtener_estadisticas(ruta=RUTA_POR_DEFECTO, sesion_id=None):
    """Total de detecciones, conteo por emoción, confianza promedio y lecturas."""
    condicion, parametros = _filtro_sesion(sesion_id)
    union = "FROM deteccion d JOIN lectura l ON l.id = d.lectura_id"
    with conexion_bd(ruta) as conexion:
        total, promedio = conexion.execute(
            f"SELECT COUNT(*), AVG(d.confianza) {union} {condicion}", parametros,
        ).fetchone()
        filas = conexion.execute(
            f"SELECT d.emocion, COUNT(*) AS cantidad {union} {condicion} GROUP BY d.emocion", parametros,
        ).fetchall()
        lecturas = conexion.execute(f"SELECT COUNT(*) FROM lectura l {condicion}", parametros).fetchone()[0]

    por_emocion = {emocion: 0 for emocion in EMOCIONES}
    for fila in filas:
        por_emocion[fila["emocion"]] = fila["cantidad"]

    return {
        "total": total,
        "por_emocion": por_emocion,
        "promedio_confianza": round(promedio, DECIMALES) if promedio is not None else 0.0,
        "lecturas": lecturas,
    }


# ---------- Exportación ----------

COLUMNAS_CSV = ("id", "fecha", "emocion", "confianza")


def exportar_csv(registros, ruta_csv):
    """Escribe los registros en un CSV y devuelve cuántos escribió.

    Incluye una columna por emoción con su porcentaje y, al final, la sesión
    y la fuente. Usa UTF-8 con BOM para que Excel muestre bien las tildes.
    """
    with open(ruta_csv, "w", newline="", encoding="utf-8-sig") as archivo:
        escritor = csv.writer(archivo)
        escritor.writerow(COLUMNAS_CSV + tuple(EMOCIONES) + ("sesion_id", "fuente"))
        for registro in registros:
            escritor.writerow([
                registro["id"], registro["fecha"], registro["emocion"], registro["confianza"],
                *[registro["todas"].get(emocion, 0.0) for emocion in EMOCIONES],
                registro.get("sesion_id") or "", registro.get("fuente", ""),
            ])
    return len(registros)
