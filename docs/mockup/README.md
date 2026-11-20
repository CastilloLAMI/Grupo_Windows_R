# Mockup de la interfaz – EmotiContigo

Mockup de la interfaz gráfica de escritorio que se implementará con **Tkinter**, según lo indicado por el docente.
Sirve como guía visual antes de programar: define pantallas, controles y la información que verá el docente.

Cada pantalla está en un archivo `.html` que se abre en cualquier navegador; las pestañas enlazan entre pantallas.
Los archivos `.png` son capturas de las mismas pantallas. **Todos los números son datos de ejemplo.**

## Pantallas

| # | Pantalla | Archivo | Qué muestra |
|---|---|---|---|
| 1 | Clase en vivo | `01-clase-en-vivo.html` | Vista de la cámara con un recuadro por rostro y su emoción; selección de cámara e intervalo de análisis; botones Iniciar, Pausar y Capturar ahora; resumen del grupo (rostros, emoción predominante, distribución de las 7 emociones, últimas lecturas). |
| 2 | Analizar imagen | `02-analizar-imagen.html` | Flujo actual: seleccionar una foto (jpg/png, máx. 5 MB), analizarla y ver la expresión principal con su confianza y la distribución. |
| 3 | Estadísticas | `03-estadisticas.html` | Filtros por sesión y periodo; indicadores (total, emoción más frecuente, confianza promedio, sesiones); gráfico por emoción y evolución durante la clase. |
| 4 | Historial | `04-historial.html` | Tabla de análisis (fecha, sesión, fuente, rostros, emoción, confianza) con búsqueda, filtros, paginación y exportación a CSV. |

## Widgets de Tkinter sugeridos

| Elemento del mockup | Widget / librería |
|---|---|
| Pestañas | `ttk.Notebook` |
| Vista de la cámara | `tk.Label` o `tk.Canvas` con `ImageTk.PhotoImage`, actualizado con `after()` |
| Captura y detección de rostros | OpenCV (`cv2.VideoCapture`) |
| Selectores (cámara, intervalo, filtros) | `ttk.Combobox` |
| Barras de distribución | `ttk.Progressbar` o `tk.Canvas` |
| Botones | `ttk.Button` |
| Gráficos de estadísticas | matplotlib con `FigureCanvasTkAgg` |
| Tabla del historial | `ttk.Treeview` + `ttk.Scrollbar` |
| Exportar CSV | módulo `csv` + `filedialog.asksaveasfilename` |
| Datos | `src/historial.py` (SQLite) |

## Criterios de diseño

- Se mantienen los colores de la interfaz actual (verde `#183B30` / `#1E7F5E`) y un color fijo por emoción.
- El pie de cada pantalla recuerda el alcance ético: la expresión es una señal de apoyo, no mide si el estudiante aprendió, y no se guardan fotografías.
- La sesión se muestra como `[Grado y sección] · [Curso]` hasta definir los datos reales.
