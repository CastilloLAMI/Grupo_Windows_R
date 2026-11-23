-- ============================================================
-- EmotiContigo - Consultas de ejemplo
-- Se pueden ejecutar con DB Browser for SQLite o con:
--   sqlite3 emoticontigo.db < db/consultas.sql
-- ============================================================

-- 1. Sesiones con su cantidad de lecturas y de rostros detectados.
SELECT s.id, s.grado_seccion, s.curso, s.inicio, s.fin,
       COUNT(DISTINCT l.id) AS lecturas,
       COUNT(d.id)          AS detecciones
FROM sesion s
LEFT JOIN lectura l   ON l.sesion_id = s.id
LEFT JOIN deteccion d ON d.lectura_id = l.id
GROUP BY s.id
ORDER BY s.id DESC;

-- 2. Distribucion de emociones en una sesion (cambia el 1 por el id de la sesion).
SELECT d.emocion,
       COUNT(*)                     AS cantidad,
       ROUND(AVG(d.confianza), 2)   AS confianza_promedio
FROM deteccion d
JOIN lectura l ON l.id = d.lectura_id
WHERE l.sesion_id = 1
GROUP BY d.emocion
ORDER BY cantidad DESC;

-- 3. Evolucion durante la clase: emocion predominante cada 5 minutos (hora UTC).
SELECT strftime('%H:', l.fecha) || printf('%02d', (CAST(strftime('%M', l.fecha) AS INTEGER) / 5) * 5) AS bloque,
       l.predominante,
       COUNT(*) AS lecturas
FROM lectura l
WHERE l.sesion_id = 1 AND l.predominante IS NOT NULL
GROUP BY bloque, l.predominante
ORDER BY bloque, lecturas DESC;

-- 4. Promedio de cada emocion en todas las detecciones.
SELECT ROUND(AVG(enfado), 2)    AS enfado,
       ROUND(AVG(asco), 2)      AS asco,
       ROUND(AVG(miedo), 2)     AS miedo,
       ROUND(AVG(felicidad), 2) AS felicidad,
       ROUND(AVG(tristeza), 2)  AS tristeza,
       ROUND(AVG(sorpresa), 2)  AS sorpresa,
       ROUND(AVG(neutral), 2)   AS neutral
FROM deteccion;
