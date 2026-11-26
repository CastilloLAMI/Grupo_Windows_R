-- ============================================================
-- EmotiContigo - Esquema de la base de datos (SQLite)
-- Version 2: sesiones de clase, lecturas y detecciones.
--
-- sesion (1) ---< lectura (1) ---< deteccion
--
-- Privacidad: no se guarda ninguna imagen ni dato que identifique
-- a un estudiante. Cada deteccion es un rostro anonimo.
-- ============================================================

PRAGMA foreign_keys = ON;

-- Una clase observada por el docente.
CREATE TABLE IF NOT EXISTS sesion (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    curso         TEXT    NOT NULL CHECK (length(trim(curso)) > 0),
    grado_seccion TEXT    NOT NULL CHECK (length(trim(grado_seccion)) > 0),
    docente       TEXT,
    inicio        TEXT    NOT NULL,              -- fecha y hora UTC (ISO 8601)
    fin           TEXT,                          -- NULL mientras la sesion esta abierta
    CHECK (fin IS NULL OR fin >= inicio)
);

-- Cada analisis: un cuadro de la camara o una fotografia.
CREATE TABLE IF NOT EXISTS lectura (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    sesion_id     INTEGER REFERENCES sesion (id) ON DELETE CASCADE,  -- NULL: fuera de una sesion
    fecha         TEXT    NOT NULL,              -- fecha y hora UTC (ISO 8601)
    fuente        TEXT    NOT NULL CHECK (fuente IN ('camara', 'imagen', 'anterior')),
    total_rostros INTEGER NOT NULL CHECK (total_rostros >= 0),
    predominante  TEXT    CHECK (predominante IS NULL OR predominante IN
                      ('enfado', 'asco', 'miedo', 'felicidad', 'tristeza', 'sorpresa', 'neutral'))
);

-- Cada rostro detectado en una lectura, con su emocion y la distribucion completa.
CREATE TABLE IF NOT EXISTS deteccion (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    lectura_id INTEGER NOT NULL REFERENCES lectura (id) ON DELETE CASCADE,
    emocion    TEXT    NOT NULL CHECK (emocion IN
                   ('enfado', 'asco', 'miedo', 'felicidad', 'tristeza', 'sorpresa', 'neutral')),
    confianza  REAL    NOT NULL CHECK (confianza BETWEEN 0 AND 100),
    enfado     REAL    NOT NULL DEFAULT 0 CHECK (enfado BETWEEN 0 AND 100),
    asco       REAL    NOT NULL DEFAULT 0 CHECK (asco BETWEEN 0 AND 100),
    miedo      REAL    NOT NULL DEFAULT 0 CHECK (miedo BETWEEN 0 AND 100),
    felicidad  REAL    NOT NULL DEFAULT 0 CHECK (felicidad BETWEEN 0 AND 100),
    tristeza   REAL    NOT NULL DEFAULT 0 CHECK (tristeza BETWEEN 0 AND 100),
    sorpresa   REAL    NOT NULL DEFAULT 0 CHECK (sorpresa BETWEEN 0 AND 100),
    neutral    REAL    NOT NULL DEFAULT 0 CHECK (neutral BETWEEN 0 AND 100)
);

CREATE INDEX IF NOT EXISTS idx_lectura_sesion   ON lectura (sesion_id);
CREATE INDEX IF NOT EXISTS idx_lectura_fecha    ON lectura (fecha);
CREATE INDEX IF NOT EXISTS idx_deteccion_lectura ON deteccion (lectura_id);
CREATE INDEX IF NOT EXISTS idx_deteccion_emocion ON deteccion (emocion);
