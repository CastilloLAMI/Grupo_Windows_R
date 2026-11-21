"""Interfaz de escritorio de EmotiContigo."""
import os
import threading
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import customtkinter as ctk
import numpy as np
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image, ImageTk

try:
    from src.camara import (
        INTERVALO_ANALISIS_S, AnalizadorAula, Camara, ErrorCamara, MonitorCamara,
        dibujar_resultados, guardar_resultado_cuadro,
    )
    from src.historial import (
        LIMITE_MAXIMO, RUTA_POR_DEFECTO, exportar_csv, guardar_analisis, inicializar_bd,
        listar_historial, obtener_estadisticas,
    )
    from src.model import DetectorEmociones
    from src.preprocess import EMOCIONES, EXTENSIONES_VALIDAS
except ImportError:  # Permite ejecutar `python src/interfaz.py`
    from camara import (
        INTERVALO_ANALISIS_S, AnalizadorAula, Camara, ErrorCamara, MonitorCamara,
        dibujar_resultados, guardar_resultado_cuadro,
    )
    from historial import (
        LIMITE_MAXIMO, RUTA_POR_DEFECTO, exportar_csv, guardar_analisis, inicializar_bd,
        listar_historial, obtener_estadisticas,
    )
    from model import DetectorEmociones
    from preprocess import EMOCIONES, EXTENSIONES_VALIDAS

MODO_APARIENCIA = "light"
TEMA_COLOR = "green"
TITULO = "EmotiContigo"
ANCHO = 1280
ALTO = 820
ANCHO_MINIMO = 1100
ALTO_MINIMO = 720
ANCHO_VISTA = 400
ALTO_VISTA = 300
EXTENSIONES = " ".join("*" + extension for extension in EXTENSIONES_VALIDAS)
RETARDO_CARGA_MS = 100
PORCENTAJE_MAXIMO = 100
ULTIMOS_ANALISIS = 6
FORMATO_FECHA = "%d/%m/%Y  %H:%M"
FORMATO_FECHA_SESION = "%d/%m/%Y"
FORMATO_HORA = "%H:%M:%S"

PESTANA_VIVO = "Clase en vivo"
PESTANA_ANALISIS = "Analizar imagen"
PESTANA_ESTADISTICAS = "Estadísticas"
PESTANA_HISTORIAL = "Historial"

# Cámara en vivo
REFRESCO_VIDEO_MS = 40
CAMARAS = ("Cámara 0", "Cámara 1", "Cámara 2")
INTERVALOS_S = (5, 10, 30)
ULTIMAS_LECTURAS = 5
TAMANO_VIDEO_DEFECTO = (640, 360)
TAMANO_MINIMO_VISTA = 2

# Historial
TODAS = "Todas"
COLUMNAS_HISTORIAL = (
    ("fecha", "Fecha y hora", 180),
    ("emocion", "Emoción", 160),
    ("confianza", "Confianza", 120),
    ("segunda", "Segunda emoción", 200),
)
ALTO_FILA_TABLA = 30
ARCHIVO_CSV_DEFECTO = "historial_emoticontigo.csv"

# Colores
COLOR_FONDO = "#EEF3F0"
COLOR_PANEL = "#FFFFFF"
COLOR_ENCABEZADO = "#183B30"
COLOR_PILDORA = "#2A5546"
COLOR_TEXTO_ENCABEZADO = "#D0E5DB"
COLOR_FONDO_VISTA = "#E8EFEB"
COLOR_FONDO_VIDEO = "#20302A"
COLOR_TEXTO_VIDEO = "#8FA79B"
COLOR_TEXTO = "#1F2D27"
COLOR_TEXTO_SUAVE = "#52665C"
COLOR_TITULO_SECCION = "#4A6558"
COLOR_PISTA_BARRA = "#E3EAE6"
COLOR_BORDE = "#D5E0DA"
COLOR_BOTON = "#1E7F5E"
COLOR_BOTON_HOVER = "#155C44"
COLOR_BOTON_SECUNDARIO = "#E3EAE6"
COLOR_BOTON_SECUNDARIO_HOVER = "#D2DDD7"
COLOR_FILA_PAR = "#F7FAF8"
COLOR_EXITO = "#1E8E5A"
COLOR_ERROR = "#C0392B"
COLOR_PROCESO = "#C77700"
COLOR_TEXTO_TARJETA = "#FFFFFF"
COLOR_TRANSPARENTE = "transparent"

# Tamaños de componentes
ALTO_ENCABEZADO = 84
ALTO_BOTON = 42
ALTO_PESTANA = 34
ALTO_BARRA = 10
ALTO_TARJETA = 130
ALTO_MINI_TARJETA = 84
ANCHO_COMBO = 150
RADIO_PANEL = 14
RADIO_VISTA = 12
RADIO_BOTON = 10
RADIO_PILDORA = 14
BORDE = 1
MARGEN = 20
SEPARACION = 10
SEPARACION_CHICA = 4
ANCHO_INDICADOR = 6
ANCHO_TEXTO_RESULTADO = 360

# Gráfico
TAMANO_FIGURA = (5.6, 3.6)
DPI_FIGURA = 100
ANCHO_BARRA_GRAFICO = 0.6

# Fuentes
FUENTE = "Segoe UI"
FUENTE_TITULO = (FUENTE, 24, "bold")
FUENTE_SUBTITULO = (FUENTE, 13)
FUENTE_PILDORA = (FUENTE, 12)
FUENTE_SECCION = (FUENTE, 17, "bold")
FUENTE_NORMAL = (FUENTE, 12)
FUENTE_ETIQUETA = (FUENTE, 11, "bold")
FUENTE_RESULTADO = (FUENTE, 30, "bold")
FUENTE_RESULTADO_CHICO = (FUENTE, 22, "bold")
FUENTE_CONFIANZA = (FUENTE, 15)
FUENTE_EMOCION = (FUENTE, 13, "bold")
FUENTE_PORCENTAJE = (FUENTE, 12)
FUENTE_BOTON = (FUENTE, 13, "bold")
FUENTE_KPI = (FUENTE, 26, "bold")
FUENTE_TABLA = (FUENTE, 11)
FUENTE_TABLA_TITULO = (FUENTE, 11, "bold")
FUENTE_GRAFICO = 10

SIN_DATO = "—"
DECIMALES = 2
AVISO_ETICO = "La expresión es una señal de apoyo; no mide si el estudiante aprendió."
AVISO_PRIVACIDAD = "No se guardan fotografías: solo la emoción y la confianza."

COLORES_EMOCION = {
    "enfado": "#D64545",
    "asco": "#6E8B2E",
    "miedo": "#7B5EA7",
    "felicidad": "#E0A100",
    "tristeza": "#3B7DD8",
    "sorpresa": "#E07B39",
    "neutral": "#7D8F87",
}
COLOR_DEFECTO = "#1E7F5E"


def color_emocion(emocion):
    """Color asociado a la emoción, o el color de la marca si no se conoce."""
    return COLORES_EMOCION.get(emocion, COLOR_DEFECTO)


def nombre_visible(emocion):
    """Nombre de la emoción con mayúscula inicial."""
    return emocion.capitalize() if emocion else SIN_DATO


def texto_confianza(porcentaje):
    """Porcentaje con dos decimales, por ejemplo '90.00 %'."""
    return f"{porcentaje:.{DECIMALES}f} %"


def ordenar_distribucion(todas):
    """Lista de (emoción, porcentaje) de mayor a menor."""
    return sorted(todas.items(), key=lambda par: par[1], reverse=True)


def emocion_frecuente(estadisticas):
    """Emoción con más análisis; en empate gana la primera de FER2013."""
    conteo = estadisticas.get("por_emocion", {})
    if not estadisticas.get("total"):
        return None
    return max(EMOCIONES, key=lambda emocion: conteo.get(emocion, 0))


def serie_grafico(estadisticas):
    """Nombres, cantidades y colores en el orden de FER2013 para el gráfico."""
    conteo = estadisticas.get("por_emocion", {})
    nombres = [nombre_visible(emocion) for emocion in EMOCIONES]
    cantidades = [conteo.get(emocion, 0) for emocion in EMOCIONES]
    colores = [color_emocion(emocion) for emocion in EMOCIONES]
    return nombres, cantidades, colores


def fecha_local(fecha_iso):
    """Convierte la fecha UTC del historial a la hora local del equipo."""
    return datetime.fromisoformat(fecha_iso).astimezone().strftime(FORMATO_FECHA)


def texto_intervalo(segundos):
    return f"{segundos} segundos"


def segundos_intervalo(texto):
    """'10 segundos' -> 10."""
    return int(texto.split()[0])


def indice_camara(texto):
    """'Cámara 1' -> 1."""
    return int(texto.split()[-1])


def ajustar_tamano(ancho, alto, ancho_maximo, alto_maximo):
    """Tamaño que entra en el espacio disponible sin deformar la imagen."""
    escala = min(ancho_maximo / ancho, alto_maximo / alto)
    return max(1, int(ancho * escala)), max(1, int(alto * escala))


def segunda_emocion(todas):
    """Texto de la segunda emoción más probable, por ejemplo 'Neutral (12.00 %)'."""
    ordenadas = ordenar_distribucion(todas)
    if len(ordenadas) < 2:
        return SIN_DATO
    emocion, porcentaje = ordenadas[1]
    return f"{nombre_visible(emocion)} ({texto_confianza(porcentaje)})"


def filtrar_registros(registros, emocion=None):
    """Registros de una emoción, o todos si no se indica ninguna."""
    if not emocion:
        return list(registros)
    return [registro for registro in registros if registro["emocion"] == emocion]


def texto_lectura(resultado, hora):
    """Resumen de una lectura de la cámara para la lista de últimas lecturas."""
    rostros = resultado["total_rostros"]
    if not rostros:
        return f"{hora}  ·  sin rostros"
    plural = "rostro" if rostros == 1 else "rostros"
    return f"{hora}  ·  {nombre_visible(resultado['predominante'])}  ·  {rostros} {plural}"


class AplicacionEmociones(ctk.CTk):
    """Ventana principal: cámara en vivo, análisis de fotos, estadísticas e historial."""

    def __init__(self, detector=None, ruta_bd=None):
        super().__init__(fg_color=COLOR_FONDO)
        self.detector = detector or DetectorEmociones()
        self.ruta_bd = ruta_bd or os.getenv("EMOTI_BD") or RUTA_POR_DEFECTO
        inicializar_bd(self.ruta_bd)
        self.ruta_imagen = None
        self.modelo_listo = False
        self.monitor = None
        self.ultimo_numero = 0
        self.lecturas = []
        self.registros = []
        self._construir_interfaz()
        self._actualizar_estadisticas()
        self.protocol("WM_DELETE_WINDOW", self._cerrar)
        self.after(RETARDO_CARGA_MS, self._iniciar_carga_modelo)

    # ---------- Construcción ----------

    def _construir_interfaz(self):
        self.title(TITULO)
        self.geometry(f"{ANCHO}x{ALTO}")
        self.minsize(ANCHO_MINIMO, ALTO_MINIMO)
        self._configurar_estilo_tabla()
        self._crear_encabezado()

        self.pestanas = ctk.CTkTabview(
            self,
            fg_color=COLOR_FONDO,
            segmented_button_selected_color=COLOR_BOTON,
            segmented_button_selected_hover_color=COLOR_BOTON_HOVER,
            command=self._cambiar_pestana,
        )
        self.pestanas.pack(fill="both", expand=True, padx=MARGEN, pady=(SEPARACION, 0))
        self.pestanas._segmented_button.configure(font=FUENTE_BOTON, height=ALTO_PESTANA)
        self._crear_pestana_vivo(self.pestanas.add(PESTANA_VIVO))
        self._crear_pestana_analisis(self.pestanas.add(PESTANA_ANALISIS))
        self._crear_pestana_estadisticas(self.pestanas.add(PESTANA_ESTADISTICAS))
        self._crear_pestana_historial(self.pestanas.add(PESTANA_HISTORIAL))
        self.pestanas.set(PESTANA_VIVO)
        self._crear_pie()

    def _configurar_estilo_tabla(self):
        estilo = ttk.Style(self)
        estilo.theme_use("clam")
        estilo.configure(
            "Emoti.Treeview", background=COLOR_PANEL, fieldbackground=COLOR_PANEL,
            foreground=COLOR_TEXTO, rowheight=ALTO_FILA_TABLA, font=FUENTE_TABLA, borderwidth=0,
        )
        estilo.configure(
            "Emoti.Treeview.Heading", background=COLOR_FONDO_VISTA, foreground=COLOR_TITULO_SECCION,
            font=FUENTE_TABLA_TITULO, relief="flat", borderwidth=0,
        )
        estilo.map("Emoti.Treeview.Heading", background=[("active", COLOR_BOTON_SECUNDARIO_HOVER)])
        estilo.map(
            "Emoti.Treeview",
            background=[("selected", COLOR_BOTON)],
            foreground=[("selected", COLOR_TEXTO_TARJETA)],
        )

    def _crear_encabezado(self):
        encabezado = ctk.CTkFrame(
            self, height=ALTO_ENCABEZADO, corner_radius=0, fg_color=COLOR_ENCABEZADO,
        )
        encabezado.pack(fill="x")
        encabezado.pack_propagate(False)

        textos = ctk.CTkFrame(encabezado, fg_color=COLOR_TRANSPARENTE)
        textos.pack(side="left", padx=MARGEN * 2)
        ctk.CTkLabel(
            textos, text="EMOTICONTIGO", font=FUENTE_TITULO, text_color=COLOR_TEXTO_TARJETA, anchor="w",
        ).pack(anchor="w")
        ctk.CTkLabel(
            textos,
            text="Apoyo al docente para observar expresiones faciales",
            font=FUENTE_SUBTITULO,
            text_color=COLOR_TEXTO_ENCABEZADO,
            anchor="w",
        ).pack(anchor="w")

        pildoras = ctk.CTkFrame(encabezado, fg_color=COLOR_TRANSPARENTE)
        pildoras.pack(side="right", padx=MARGEN * 2)
        self._crear_pildora(pildoras, f"Sesión: {datetime.now().strftime(FORMATO_FECHA_SESION)}")
        self.pildora_modelo = self._crear_pildora(pildoras, "Cargando modelo...")

    def _crear_pildora(self, contenedor, texto):
        pildora = ctk.CTkLabel(
            contenedor, text=texto, font=FUENTE_PILDORA, text_color=COLOR_TEXTO_TARJETA,
            fg_color=COLOR_PILDORA, corner_radius=RADIO_PILDORA, height=ALTO_PESTANA,
        )
        pildora.pack(side="left", padx=SEPARACION_CHICA, ipadx=SEPARACION)
        return pildora

    def _crear_pie(self):
        pie = ctk.CTkFrame(self, fg_color=COLOR_TRANSPARENTE)
        pie.pack(fill="x", padx=MARGEN, pady=SEPARACION)
        self.estado = ctk.CTkLabel(
            pie, text="Cargando modelo de inteligencia artificial...",
            font=FUENTE_NORMAL, text_color=COLOR_PROCESO, anchor="w",
        )
        self.estado.pack(side="left")
        ctk.CTkLabel(
            pie, text=f"{AVISO_ETICO}  {AVISO_PRIVACIDAD}", font=FUENTE_PORCENTAJE,
            text_color=COLOR_TEXTO_SUAVE, anchor="e",
        ).pack(side="right")

    def _crear_panel(self, contenedor):
        return ctk.CTkFrame(
            contenedor,
            corner_radius=RADIO_PANEL,
            fg_color=COLOR_PANEL,
            border_width=BORDE,
            border_color=COLOR_BORDE,
        )

    def _titulo_seccion(self, contenedor, texto):
        etiqueta = ctk.CTkLabel(
            contenedor, text=texto, font=FUENTE_SECCION, text_color=COLOR_TEXTO, anchor="w",
        )
        etiqueta.pack(fill="x", padx=MARGEN, pady=(MARGEN, SEPARACION))
        return etiqueta

    def _etiqueta_seccion(self, contenedor, texto):
        ctk.CTkLabel(
            contenedor, text=texto, font=FUENTE_ETIQUETA, text_color=COLOR_TITULO_SECCION, anchor="w",
        ).pack(fill="x", padx=SEPARACION, pady=(MARGEN, SEPARACION_CHICA))

    def _crear_boton(self, contenedor, texto, comando, principal=True, **opciones):
        colores = (
            {"fg_color": COLOR_BOTON, "hover_color": COLOR_BOTON_HOVER}
            if principal else
            {"fg_color": COLOR_BOTON_SECUNDARIO, "hover_color": COLOR_BOTON_SECUNDARIO_HOVER,
             "text_color": COLOR_TEXTO}
        )
        return ctk.CTkButton(
            contenedor, text=texto, command=comando, height=ALTO_BOTON,
            corner_radius=RADIO_BOTON, font=FUENTE_BOTON, **colores, **opciones,
        )

    def _crear_combo(self, contenedor, etiqueta, valores, comando=None):
        caja = ctk.CTkFrame(contenedor, fg_color=COLOR_TRANSPARENTE)
        ctk.CTkLabel(
            caja, text=etiqueta, font=FUENTE_ETIQUETA, text_color=COLOR_TEXTO_SUAVE, anchor="w",
        ).pack(anchor="w")
        combo = ctk.CTkComboBox(
            caja, values=list(valores), width=ANCHO_COMBO, state="readonly", font=FUENTE_NORMAL,
            dropdown_font=FUENTE_NORMAL, border_color=COLOR_BORDE, button_color=COLOR_BOTON,
            button_hover_color=COLOR_BOTON_HOVER, command=comando,
        )
        combo.set(valores[0])
        combo.pack(anchor="w")
        return caja, combo

    # ---------- Pestaña: clase en vivo ----------

    def _crear_pestana_vivo(self, pestana):
        pestana.grid_columnconfigure(0, weight=3, uniform="vivo")
        pestana.grid_columnconfigure(1, weight=2, uniform="vivo")
        pestana.grid_rowconfigure(0, weight=1)

        izquierda = self._crear_panel(pestana)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, SEPARACION))
        derecha = self._crear_panel(pestana)
        derecha.grid(row=0, column=1, sticky="nsew", padx=(SEPARACION, 0))

        self._crear_panel_camara(izquierda)
        self._crear_panel_grupo(derecha)

    def _crear_panel_camara(self, panel):
        cabecera = ctk.CTkFrame(panel, fg_color=COLOR_TRANSPARENTE)
        cabecera.pack(fill="x", padx=MARGEN, pady=(MARGEN, SEPARACION))
        ctk.CTkLabel(
            cabecera, text="Cámara del aula", font=FUENTE_SECCION, text_color=COLOR_TEXTO,
        ).pack(side="left")
        self.estado_camara = ctk.CTkLabel(
            cabecera, text="Detenida", font=FUENTE_ETIQUETA, text_color=COLOR_TEXTO_SUAVE,
            fg_color=COLOR_BOTON_SECUNDARIO, corner_radius=RADIO_PILDORA, height=ALTO_BARRA * 3,
        )
        self.estado_camara.pack(side="right", ipadx=SEPARACION)

        self.marco_video = tk.Frame(panel, bg=COLOR_FONDO_VIDEO)
        self.marco_video.pack(fill="both", expand=True, padx=MARGEN)
        self.video = tk.Label(
            self.marco_video, bg=COLOR_FONDO_VIDEO, fg=COLOR_TEXTO_VIDEO, font=FUENTE_NORMAL,
            text="La cámara está detenida.\nPresiona «Iniciar cámara» para empezar.",
        )
        self.video.place(relx=0.5, rely=0.5, anchor="center")

        controles = ctk.CTkFrame(panel, fg_color=COLOR_TRANSPARENTE)
        controles.pack(fill="x", padx=MARGEN, pady=(SEPARACION, 0))
        caja, self.combo_camara = self._crear_combo(controles, "Cámara", CAMARAS)
        caja.pack(side="left", padx=(0, SEPARACION))
        caja, self.combo_intervalo = self._crear_combo(
            controles, "Analizar cada", [texto_intervalo(s) for s in INTERVALOS_S],
            comando=self._cambiar_intervalo,
        )
        self.combo_intervalo.set(texto_intervalo(INTERVALO_ANALISIS_S))
        caja.pack(side="left")

        botones = ctk.CTkFrame(panel, fg_color=COLOR_TRANSPARENTE)
        botones.pack(fill="x", padx=MARGEN, pady=(SEPARACION, MARGEN))
        botones.grid_columnconfigure((0, 1, 2), weight=1, uniform="camara")
        self.boton_iniciar = self._crear_boton(
            botones, "Iniciar cámara", self._iniciar_camara, state="disabled",
        )
        self.boton_iniciar.grid(row=0, column=0, sticky="ew", padx=(0, SEPARACION_CHICA))
        self.boton_detener = self._crear_boton(
            botones, "Detener", self._detener_camara, principal=False, state="disabled",
        )
        self.boton_detener.grid(row=0, column=1, sticky="ew", padx=SEPARACION_CHICA)
        self.boton_capturar = self._crear_boton(
            botones, "Capturar ahora", self._capturar_ahora, principal=False, state="disabled",
        )
        self.boton_capturar.grid(row=0, column=2, sticky="ew", padx=(SEPARACION_CHICA, 0))

    def _crear_panel_grupo(self, panel):
        self._titulo_seccion(panel, "Resumen del grupo")
        contenido = ctk.CTkScrollableFrame(panel, fg_color=COLOR_TRANSPARENTE)
        contenido.pack(fill="both", expand=True, padx=SEPARACION, pady=(0, SEPARACION))

        tarjetas = ctk.CTkFrame(contenido, fg_color=COLOR_TRANSPARENTE)
        tarjetas.pack(fill="x", padx=SEPARACION)
        tarjetas.grid_columnconfigure((0, 1), weight=1, uniform="grupo")

        rostros = ctk.CTkFrame(
            tarjetas, height=ALTO_MINI_TARJETA, corner_radius=RADIO_VISTA, fg_color=COLOR_FONDO_VISTA,
        )
        rostros.grid(row=0, column=0, sticky="ew", padx=(0, SEPARACION_CHICA))
        rostros.pack_propagate(False)
        ctk.CTkLabel(
            rostros, text="ROSTROS AHORA", font=FUENTE_ETIQUETA, text_color=COLOR_TITULO_SECCION,
        ).pack(pady=(SEPARACION, 0))
        self.valor_rostros = ctk.CTkLabel(
            rostros, text=SIN_DATO, font=FUENTE_RESULTADO_CHICO, text_color=COLOR_TEXTO,
        )
        self.valor_rostros.pack()

        self.tarjeta_predominante = ctk.CTkFrame(
            tarjetas, height=ALTO_MINI_TARJETA, corner_radius=RADIO_VISTA, fg_color=COLOR_FONDO_VISTA,
        )
        self.tarjeta_predominante.grid(row=0, column=1, sticky="ew", padx=(SEPARACION_CHICA, 0))
        self.tarjeta_predominante.pack_propagate(False)
        self.etiqueta_predominante = ctk.CTkLabel(
            self.tarjeta_predominante, text="PREDOMINANTE", font=FUENTE_ETIQUETA,
            text_color=COLOR_TITULO_SECCION,
        )
        self.etiqueta_predominante.pack(pady=(SEPARACION, 0))
        self.valor_predominante = ctk.CTkLabel(
            self.tarjeta_predominante, text=SIN_DATO, font=FUENTE_RESULTADO_CHICO, text_color=COLOR_TEXTO,
        )
        self.valor_predominante.pack()

        self._etiqueta_seccion(contenido, "DISTRIBUCIÓN EN LA ÚLTIMA LECTURA")
        self.barras_grupo = {}
        for emocion in EMOCIONES:
            self.barras_grupo[emocion] = self._crear_barra(contenido, emocion, 0.0)

        self._etiqueta_seccion(contenido, "ÚLTIMAS LECTURAS")
        self.lista_lecturas = ctk.CTkLabel(
            contenido, text="Sin lecturas todavía", font=FUENTE_NORMAL, text_color=COLOR_TEXTO_SUAVE,
            justify="left", anchor="w",
        )
        self.lista_lecturas.pack(fill="x", padx=SEPARACION, pady=(0, SEPARACION))

    def _crear_barra(self, contenedor, emocion, porcentaje):
        """Fila con nombre, porcentaje y barra; devuelve (porcentaje, barra)."""
        fila = ctk.CTkFrame(contenedor, fg_color=COLOR_TRANSPARENTE)
        fila.pack(fill="x", padx=SEPARACION, pady=SEPARACION_CHICA)
        fila.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            fila, text=nombre_visible(emocion), font=FUENTE_EMOCION, text_color=COLOR_TEXTO, anchor="w",
        ).grid(row=0, column=0, sticky="w")
        etiqueta = ctk.CTkLabel(
            fila, text=texto_confianza(porcentaje), font=FUENTE_PORCENTAJE, text_color=COLOR_TEXTO_SUAVE,
        )
        etiqueta.grid(row=0, column=1, sticky="e")

        barra = ctk.CTkProgressBar(
            fila, height=ALTO_BARRA, progress_color=color_emocion(emocion), fg_color=COLOR_PISTA_BARRA,
        )
        barra.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SEPARACION_CHICA, 0))
        barra.set(porcentaje / PORCENTAJE_MAXIMO)
        return etiqueta, barra

    # ---------- Cámara en vivo ----------

    def _crear_monitor(self):
        camara = Camara(indice_camara(self.combo_camara.get()))
        return MonitorCamara(
            camara,
            AnalizadorAula(self.detector),
            intervalo=segundos_intervalo(self.combo_intervalo.get()),
            guardar=lambda resultado: guardar_resultado_cuadro(resultado, self.ruta_bd),
        )

    def _iniciar_camara(self):
        self._botones_camara(iniciar=False, detener=False, capturar=False)
        self.combo_camara.configure(state="disabled")
        self._mostrar_estado("Abriendo la cámara...", COLOR_PROCESO)
        threading.Thread(target=self._abrir_camara, daemon=True).start()

    def _abrir_camara(self):
        try:
            monitor = self._crear_monitor()
            monitor.iniciar()
        except (ErrorCamara, OSError) as error:
            mensaje = str(error)
            self.after(0, lambda m=mensaje: self._fallo_camara(m))
        else:
            self.after(0, lambda: self._camara_iniciada(monitor))

    def _camara_iniciada(self, monitor):
        self.monitor = monitor
        self.ultimo_numero = 0
        self._botones_camara(iniciar=False, detener=True, capturar=True)
        self.estado_camara.configure(text="En vivo", fg_color=COLOR_BOTON, text_color=COLOR_TEXTO_TARJETA)
        self.video.configure(text="")
        self.video.place_configure(relx=0.5, rely=0.5)
        self._mostrar_estado(
            f"Cámara activa: se analiza cada {self.monitor.intervalo} s y se guarda en el historial",
            COLOR_EXITO,
        )
        self._refrescar_video()

    def _fallo_camara(self, mensaje):
        self._camara_detenida()
        self._mostrar_estado("No se pudo usar la cámara", COLOR_ERROR)
        messagebox.showerror(
            "Cámara", f"{mensaje}\n\nRevisa que la cámara esté conectada y que otra aplicación no la esté usando.",
        )

    def _detener_camara(self):
        monitor = self.monitor
        self.monitor = None
        self._botones_camara(iniciar=False, detener=False, capturar=False)
        if monitor is None:
            self._camara_detenida()
            return
        threading.Thread(target=self._cerrar_monitor, args=(monitor,), daemon=True).start()

    def _cerrar_monitor(self, monitor):
        monitor.detener()
        self.after(0, self._camara_detenida)

    def _camara_detenida(self):
        self._botones_camara(iniciar=self.modelo_listo, detener=False, capturar=False)
        self.combo_camara.configure(state="readonly")
        self.estado_camara.configure(text="Detenida", fg_color=COLOR_BOTON_SECUNDARIO, text_color=COLOR_TEXTO_SUAVE)
        self.video.configure(image="", text="La cámara está detenida.\nPresiona «Iniciar cámara» para empezar.")
        self.video.image = None
        self._mostrar_estado("Cámara detenida", COLOR_TEXTO_SUAVE)

    def _botones_camara(self, iniciar, detener, capturar):
        self.boton_iniciar.configure(state="normal" if iniciar else "disabled")
        self.boton_detener.configure(state="normal" if detener else "disabled")
        self.boton_capturar.configure(state="normal" if capturar else "disabled")

    def _capturar_ahora(self):
        if self.monitor:
            self.monitor.capturar_ahora()
            self._mostrar_estado("Analizando el cuadro actual...", COLOR_PROCESO)

    def _cambiar_intervalo(self, texto):
        if self.monitor:
            self.monitor.intervalo = segundos_intervalo(texto)
            self._mostrar_estado(f"Ahora se analiza cada {self.monitor.intervalo} s", COLOR_EXITO)

    def _refrescar_video(self):
        monitor = self.monitor
        if monitor is None:
            return
        if monitor.error:
            error = monitor.error
            self.monitor = None
            threading.Thread(target=monitor.detener, daemon=True).start()
            self._fallo_camara(error)
            return
        cuadro, resultado, numero = monitor.instantanea()
        if cuadro is not None:
            rostros = resultado["rostros"] if resultado else []
            self._mostrar_cuadro(dibujar_resultados(cuadro, rostros))
        if resultado and numero != self.ultimo_numero:
            self.ultimo_numero = numero
            self._mostrar_resumen_grupo(resultado)
        self.after(REFRESCO_VIDEO_MS, self._refrescar_video)

    def _mostrar_cuadro(self, cuadro_bgr):
        imagen = Image.fromarray(np.ascontiguousarray(cuadro_bgr[:, :, ::-1]))
        ancho_maximo = self.marco_video.winfo_width()
        alto_maximo = self.marco_video.winfo_height()
        if ancho_maximo < TAMANO_MINIMO_VISTA or alto_maximo < TAMANO_MINIMO_VISTA:
            ancho_maximo, alto_maximo = TAMANO_VIDEO_DEFECTO
        tamano = ajustar_tamano(imagen.width, imagen.height, ancho_maximo, alto_maximo)
        foto = ImageTk.PhotoImage(imagen.resize(tamano, Image.BILINEAR))
        self.video.configure(image=foto)
        self.video.image = foto

    def _mostrar_resumen_grupo(self, resultado):
        hora = datetime.now().strftime(FORMATO_HORA)
        self.valor_rostros.configure(text=str(resultado["total_rostros"]))
        predominante = resultado["predominante"]
        if predominante:
            self.tarjeta_predominante.configure(fg_color=color_emocion(predominante))
            self.etiqueta_predominante.configure(text_color=COLOR_TEXTO_TARJETA)
            self.valor_predominante.configure(text=nombre_visible(predominante), text_color=COLOR_TEXTO_TARJETA)
        else:
            self.tarjeta_predominante.configure(fg_color=COLOR_FONDO_VISTA)
            self.etiqueta_predominante.configure(text_color=COLOR_TITULO_SECCION)
            self.valor_predominante.configure(text=SIN_DATO, text_color=COLOR_TEXTO)
        for emocion, (etiqueta, barra) in self.barras_grupo.items():
            porcentaje = resultado["distribucion"].get(emocion, 0.0)
            etiqueta.configure(text=texto_confianza(porcentaje))
            barra.set(porcentaje / PORCENTAJE_MAXIMO)
        self.lecturas.insert(0, texto_lectura(resultado, hora))
        del self.lecturas[ULTIMAS_LECTURAS:]
        self.lista_lecturas.configure(text="\n".join(self.lecturas), text_color=COLOR_TEXTO)
        self._mostrar_estado(f"Última lectura: {hora}", COLOR_EXITO)

    # ---------- Pestaña: analizar imagen ----------

    def _crear_pestana_analisis(self, pestana):
        pestana.grid_columnconfigure((0, 1), weight=1, uniform="columnas")
        pestana.grid_rowconfigure(0, weight=1)

        izquierda = self._crear_panel(pestana)
        izquierda.grid(row=0, column=0, sticky="nsew", padx=(0, SEPARACION))
        derecha = self._crear_panel(pestana)
        derecha.grid(row=0, column=1, sticky="nsew", padx=(SEPARACION, 0))

        self._crear_panel_imagen(izquierda)
        self._crear_panel_resultados(derecha)

    def _crear_panel_imagen(self, panel):
        self._titulo_seccion(panel, "Imagen")

        self.vista_imagen = ctk.CTkLabel(
            panel,
            text="Selecciona una fotografía del rostro\n(jpg o png, máximo 5 MB)",
            width=ANCHO_VISTA,
            height=ALTO_VISTA,
            fg_color=COLOR_FONDO_VISTA,
            corner_radius=RADIO_VISTA,
            text_color=COLOR_TEXTO_SUAVE,
            font=FUENTE_NORMAL,
        )
        self.vista_imagen.pack(padx=MARGEN, fill="both", expand=True)

        self.nombre = ctk.CTkLabel(
            panel, text="Ninguna imagen seleccionada", font=FUENTE_NORMAL, text_color=COLOR_TEXTO_SUAVE,
        )
        self.nombre.pack(pady=SEPARACION)

        botones = ctk.CTkFrame(panel, fg_color=COLOR_TRANSPARENTE)
        botones.pack(fill="x", padx=MARGEN, pady=(0, MARGEN))
        botones.grid_columnconfigure((0, 1), weight=1, uniform="botones")

        self.boton_seleccionar = self._crear_boton(
            botones, "Seleccionar imagen", self._seleccionar_imagen, principal=False,
        )
        self.boton_seleccionar.grid(row=0, column=0, sticky="ew", padx=(0, SEPARACION_CHICA))
        self.boton_analizar = self._crear_boton(
            botones, "Analizar", self._analizar_imagen, state="disabled",
        )
        self.boton_analizar.grid(row=0, column=1, sticky="ew", padx=(SEPARACION_CHICA, 0))

    def _crear_panel_resultados(self, panel):
        self._titulo_seccion(panel, "Resultado")

        self.tarjeta = ctk.CTkFrame(
            panel, height=ALTO_TARJETA, corner_radius=RADIO_VISTA, fg_color=COLOR_FONDO_VISTA,
        )
        self.tarjeta.pack(fill="x", padx=MARGEN)
        self.tarjeta.pack_propagate(False)

        self.tarjeta_etiqueta = ctk.CTkLabel(
            self.tarjeta, text="EXPRESIÓN PRINCIPAL", font=FUENTE_ETIQUETA, text_color=COLOR_TITULO_SECCION,
        )
        self.tarjeta_etiqueta.pack(pady=(MARGEN, 0))
        self.resultado_principal = ctk.CTkLabel(
            self.tarjeta,
            text="Esperando análisis",
            font=FUENTE_RESULTADO,
            text_color=COLOR_TEXTO_SUAVE,
            wraplength=ANCHO_TEXTO_RESULTADO,
        )
        self.resultado_principal.pack()
        self.resultado_confianza = ctk.CTkLabel(
            self.tarjeta, text="", font=FUENTE_CONFIANZA, text_color=COLOR_TEXTO_SUAVE,
        )
        self.resultado_confianza.pack()

        ctk.CTkLabel(
            panel, text="DISTRIBUCIÓN DE EXPRESIONES", font=FUENTE_ETIQUETA,
            text_color=COLOR_TITULO_SECCION, anchor="w",
        ).pack(fill="x", padx=MARGEN, pady=(MARGEN, SEPARACION_CHICA))

        self.resultados_frame = ctk.CTkScrollableFrame(panel, fg_color=COLOR_TRANSPARENTE)
        self.resultados_frame.pack(fill="both", expand=True, padx=SEPARACION, pady=(0, SEPARACION))

    # ---------- Modelo ----------

    def _iniciar_carga_modelo(self):
        threading.Thread(target=self._cargar_modelo, daemon=True).start()

    def _cargar_modelo(self):
        try:
            self.detector.cargar()
        except Exception as error:  # noqa: BLE001
            mensaje = str(error)
            self.after(0, lambda m=mensaje: self._fallo_carga_modelo(m))
        else:
            self.after(0, self._modelo_listo)

    def _modelo_listo(self):
        self.modelo_listo = True
        self.pildora_modelo.configure(text="●  Modelo listo")
        self._mostrar_estado("Modelo listo. Inicia la cámara o analiza una fotografía.", COLOR_EXITO)
        if self.monitor is None:
            self.boton_iniciar.configure(state="normal")
        if self.ruta_imagen:
            self.boton_analizar.configure(state="normal")

    def _fallo_carga_modelo(self, mensaje):
        self.pildora_modelo.configure(text="Modelo no disponible")
        self._mostrar_estado("No se pudo cargar el modelo", COLOR_ERROR)
        messagebox.showerror("Error", mensaje)

    # ---------- Análisis de una imagen ----------

    def _seleccionar_imagen(self):
        archivo = filedialog.askopenfilename(
            title="Seleccionar fotografía",
            filetypes=[("Imágenes", EXTENSIONES)],
        )
        if not archivo:
            return
        try:
            imagen = Image.open(archivo).convert("RGB")
        except (OSError, ValueError) as error:
            messagebox.showerror("Error", f"No se pudo abrir la imagen: {error}")
            return

        self.ruta_imagen = archivo
        imagen.thumbnail((ANCHO_VISTA, ALTO_VISTA))
        foto = ctk.CTkImage(light_image=imagen, dark_image=imagen, size=imagen.size)
        self.vista_imagen.configure(image=foto, text="")
        self.vista_imagen.image = foto
        self.nombre.configure(text=Path(archivo).name)
        self._limpiar_resultados()
        if self.modelo_listo:
            self.boton_analizar.configure(state="normal")

    def _analizar_imagen(self):
        if not self.ruta_imagen:
            messagebox.showwarning("Aviso", "Primero selecciona una imagen.")
            return
        self.boton_analizar.configure(state="disabled")
        self.boton_seleccionar.configure(state="disabled")
        self._mostrar_estado("Analizando imagen...", COLOR_PROCESO)
        threading.Thread(target=self._procesar_imagen, args=(self.ruta_imagen,), daemon=True).start()

    def _procesar_imagen(self, ruta):
        try:
            imagen = Image.open(ruta).convert("RGB")
            resultado = self.detector.predecir(imagen)
            guardar_analisis(resultado, self.ruta_bd)
        except Exception as error:  # noqa: BLE001
            mensaje = str(error)
            self.after(0, lambda m=mensaje: self._fallo_analisis(m))
        else:
            self.after(0, lambda r=resultado: self._mostrar_resultados(r))
        finally:
            self.after(0, self._reactivar_controles)

    def _reactivar_controles(self):
        self.boton_analizar.configure(state="normal")
        self.boton_seleccionar.configure(state="normal")

    def _fallo_analisis(self, mensaje):
        self._mostrar_estado("Error durante el análisis", COLOR_ERROR)
        messagebox.showerror("Error", mensaje)

    def _mostrar_resultados(self, datos):
        self._limpiar_resultados()
        self.tarjeta.configure(fg_color=color_emocion(datos["emocion"]))
        self.tarjeta_etiqueta.configure(text_color=COLOR_TEXTO_TARJETA)
        self.resultado_principal.configure(
            text=nombre_visible(datos["emocion"]), text_color=COLOR_TEXTO_TARJETA,
        )
        self.resultado_confianza.configure(
            text=f"Confianza: {texto_confianza(datos['confianza'])}", text_color=COLOR_TEXTO_TARJETA,
        )
        for emocion, porcentaje in ordenar_distribucion(datos["todas"]):
            self._crear_barra(self.resultados_frame, emocion, porcentaje)
        self._mostrar_estado("Análisis completado y guardado en el historial", COLOR_EXITO)

    def _limpiar_resultados(self):
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()
        self.tarjeta.configure(fg_color=COLOR_FONDO_VISTA)
        self.tarjeta_etiqueta.configure(text_color=COLOR_TITULO_SECCION)
        self.resultado_principal.configure(text="Esperando análisis", text_color=COLOR_TEXTO_SUAVE)
        self.resultado_confianza.configure(text="")

    # ---------- Pestaña: estadísticas ----------

    def _crear_pestana_estadisticas(self, pestana):
        pestana.grid_columnconfigure(0, weight=3, uniform="estadisticas")
        pestana.grid_columnconfigure(1, weight=2, uniform="estadisticas")
        pestana.grid_rowconfigure(1, weight=1)

        tarjetas = ctk.CTkFrame(pestana, fg_color=COLOR_TRANSPARENTE)
        tarjetas.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, SEPARACION))
        tarjetas.grid_columnconfigure((0, 1, 2), weight=1, uniform="kpi")
        self.kpi_total = self._crear_kpi(tarjetas, 0, "ANÁLISIS REGISTRADOS")
        self.kpi_frecuente = self._crear_kpi(tarjetas, 1, "EXPRESIÓN MÁS FRECUENTE")
        self.kpi_promedio = self._crear_kpi(tarjetas, 2, "CONFIANZA PROMEDIO")

        panel_grafico = self._crear_panel(pestana)
        panel_grafico.grid(row=1, column=0, sticky="nsew", padx=(0, SEPARACION))
        self._titulo_seccion(panel_grafico, "Expresiones detectadas")
        self.figura = Figure(figsize=TAMANO_FIGURA, dpi=DPI_FIGURA, facecolor=COLOR_PANEL)
        self.eje = self.figura.add_subplot(111)
        self.lienzo = FigureCanvasTkAgg(self.figura, master=panel_grafico)
        self.lienzo.get_tk_widget().pack(fill="both", expand=True, padx=MARGEN, pady=(0, MARGEN))
        # El panel no crece con el gráfico: así el gráfico usa el espacio libre sin empujar el pie
        panel_grafico.pack_propagate(False)

        panel_ultimos = self._crear_panel(pestana)
        panel_ultimos.grid(row=1, column=1, sticky="nsew", padx=(SEPARACION, 0))
        self._titulo_seccion(panel_ultimos, "Últimos análisis")
        self.lista_ultimos = ctk.CTkScrollableFrame(panel_ultimos, fg_color=COLOR_TRANSPARENTE, height=ALTO_TARJETA)
        self.lista_ultimos.pack(fill="both", expand=True, padx=SEPARACION)
        self._crear_boton(
            panel_ultimos, "Actualizar", self._actualizar_estadisticas, principal=False,
        ).pack(fill="x", padx=MARGEN, pady=MARGEN)

    def _crear_kpi(self, contenedor, columna, titulo):
        tarjeta = self._crear_panel(contenedor)
        tarjeta.grid(row=0, column=columna, sticky="ew", padx=SEPARACION_CHICA)
        ctk.CTkLabel(
            tarjeta, text=titulo, font=FUENTE_ETIQUETA, text_color=COLOR_TITULO_SECCION,
        ).pack(pady=(MARGEN, 0))
        valor = ctk.CTkLabel(tarjeta, text=SIN_DATO, font=FUENTE_KPI, text_color=COLOR_TEXTO)
        valor.pack(pady=(0, MARGEN))
        return valor

    def _cambiar_pestana(self):
        pestana = self.pestanas.get()
        if pestana == PESTANA_ESTADISTICAS:
            self._actualizar_estadisticas()
        elif pestana == PESTANA_HISTORIAL:
            self._actualizar_historial()

    def _actualizar_estadisticas(self):
        estadisticas = obtener_estadisticas(self.ruta_bd)
        frecuente = emocion_frecuente(estadisticas)
        self.kpi_total.configure(text=str(estadisticas["total"]))
        self.kpi_frecuente.configure(
            text=nombre_visible(frecuente),
            text_color=color_emocion(frecuente) if frecuente else COLOR_TEXTO,
        )
        promedio = estadisticas["promedio_confianza"]
        self.kpi_promedio.configure(
            text=texto_confianza(promedio) if estadisticas["total"] else SIN_DATO,
        )
        self._dibujar_grafico(estadisticas)
        self._mostrar_ultimos()

    def _dibujar_grafico(self, estadisticas):
        nombres, cantidades, colores = serie_grafico(estadisticas)
        posiciones = list(range(len(nombres)))
        eje = self.eje
        eje.clear()
        eje.set_facecolor(COLOR_PANEL)
        eje.barh(posiciones, cantidades, color=colores, height=ANCHO_BARRA_GRAFICO)
        eje.set_yticks(posiciones, nombres, fontsize=FUENTE_GRAFICO, color=COLOR_TEXTO)
        eje.invert_yaxis()
        eje.tick_params(axis="x", labelsize=FUENTE_GRAFICO, colors=COLOR_TEXTO_SUAVE)
        eje.tick_params(axis="y", length=0)
        eje.xaxis.get_major_locator().set_params(integer=True)
        for lado in ("top", "right", "left"):
            eje.spines[lado].set_visible(False)
        eje.spines["bottom"].set_color(COLOR_BORDE)
        eje.grid(axis="x", color=COLOR_PISTA_BARRA)
        eje.set_axisbelow(True)
        for posicion, cantidad in zip(posiciones, cantidades):
            if cantidad:
                eje.text(cantidad, posicion, f"  {cantidad}", va="center",
                         fontsize=FUENTE_GRAFICO, color=COLOR_TEXTO)
        if not any(cantidades):
            eje.set_xticks([])
            eje.text(0.5, 0.5, "Aún no hay análisis registrados", transform=eje.transAxes,
                     ha="center", va="center", fontsize=FUENTE_GRAFICO, color=COLOR_TEXTO_SUAVE)
        self.figura.tight_layout()
        self.lienzo.draw_idle()

    def _mostrar_ultimos(self):
        for widget in self.lista_ultimos.winfo_children():
            widget.destroy()
        registros = listar_historial(self.ruta_bd, ULTIMOS_ANALISIS)
        if not registros:
            ctk.CTkLabel(
                self.lista_ultimos, text="Sin registros todavía", font=FUENTE_NORMAL,
                text_color=COLOR_TEXTO_SUAVE,
            ).pack(pady=MARGEN)
            return
        for registro in registros:
            self._agregar_registro(registro)

    def _agregar_registro(self, registro):
        fila = ctk.CTkFrame(self.lista_ultimos, fg_color=COLOR_FONDO_VISTA, corner_radius=RADIO_BOTON)
        fila.pack(fill="x", pady=SEPARACION_CHICA)
        fila.grid_columnconfigure(1, weight=1)
        ctk.CTkFrame(
            fila, width=ANCHO_INDICADOR, height=ANCHO_INDICADOR, fg_color=color_emocion(registro["emocion"]),
            corner_radius=ANCHO_INDICADOR // 2,
        ).grid(row=0, column=0, rowspan=2, sticky="ns", padx=(SEPARACION, 0), pady=SEPARACION)
        ctk.CTkLabel(
            fila, text=nombre_visible(registro["emocion"]), font=FUENTE_EMOCION,
            text_color=COLOR_TEXTO, anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=SEPARACION, pady=(SEPARACION, 0))
        ctk.CTkLabel(
            fila, text=fecha_local(registro["fecha"]), font=FUENTE_PORCENTAJE,
            text_color=COLOR_TEXTO_SUAVE, anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=SEPARACION, pady=(0, SEPARACION))
        ctk.CTkLabel(
            fila, text=texto_confianza(registro["confianza"]), font=FUENTE_PORCENTAJE,
            text_color=COLOR_TEXTO_SUAVE,
        ).grid(row=0, column=2, rowspan=2, padx=SEPARACION)

    # ---------- Pestaña: historial ----------

    def _crear_pestana_historial(self, pestana):
        panel = self._crear_panel(pestana)
        panel.pack(fill="both", expand=True)

        cabecera = ctk.CTkFrame(panel, fg_color=COLOR_TRANSPARENTE)
        cabecera.pack(fill="x", padx=MARGEN, pady=(MARGEN, SEPARACION))
        ctk.CTkLabel(
            cabecera, text="Historial de análisis", font=FUENTE_SECCION, text_color=COLOR_TEXTO,
        ).pack(side="left")
        self.contador_historial = ctk.CTkLabel(
            cabecera, text="", font=FUENTE_NORMAL, text_color=COLOR_TEXTO_SUAVE,
        )
        self.contador_historial.pack(side="right")

        barra = ctk.CTkFrame(panel, fg_color=COLOR_TRANSPARENTE)
        barra.pack(fill="x", padx=MARGEN, pady=(0, SEPARACION))
        caja, self.combo_emocion = self._crear_combo(
            barra, "Emoción", [TODAS] + [nombre_visible(emocion) for emocion in EMOCIONES],
            comando=lambda _: self._mostrar_historial(),
        )
        caja.pack(side="left")
        self._crear_boton(barra, "Exportar CSV", self._exportar_csv).pack(side="right", anchor="s")
        self._crear_boton(
            barra, "Actualizar", self._actualizar_historial, principal=False,
        ).pack(side="right", anchor="s", padx=SEPARACION)

        marco = tk.Frame(panel, bg=COLOR_BORDE, bd=0)
        marco.pack(fill="both", expand=True, padx=MARGEN, pady=(0, MARGEN))
        columnas = [clave for clave, _, _ in COLUMNAS_HISTORIAL]
        self.tabla = ttk.Treeview(marco, columns=columnas, show="headings", style="Emoti.Treeview")
        for clave, titulo, ancho in COLUMNAS_HISTORIAL:
            self.tabla.heading(clave, text=titulo, anchor="w")
            self.tabla.column(clave, width=ancho, anchor="w")
        self.tabla.tag_configure("par", background=COLOR_FILA_PAR)
        desplazamiento = ttk.Scrollbar(marco, orient="vertical", command=self.tabla.yview)
        self.tabla.configure(yscrollcommand=desplazamiento.set)
        desplazamiento.pack(side="right", fill="y", padx=(0, BORDE), pady=BORDE)
        self.tabla.pack(side="left", fill="both", expand=True, padx=(BORDE, 0), pady=BORDE)

    def _actualizar_historial(self):
        self.registros = listar_historial(self.ruta_bd, LIMITE_MAXIMO)
        self._mostrar_historial()

    def _emocion_filtrada(self):
        texto = self.combo_emocion.get()
        return None if texto == TODAS else texto.lower()

    def _mostrar_historial(self):
        self.tabla.delete(*self.tabla.get_children())
        visibles = filtrar_registros(self.registros, self._emocion_filtrada())
        for numero, registro in enumerate(visibles):
            self.tabla.insert(
                "", "end",
                values=(
                    fecha_local(registro["fecha"]),
                    nombre_visible(registro["emocion"]),
                    texto_confianza(registro["confianza"]),
                    segunda_emocion(registro["todas"]),
                ),
                tags=("par",) if numero % 2 else (),
            )
        self.contador_historial.configure(
            text=f"Mostrando {len(visibles)} de los últimos {len(self.registros)} análisis",
        )

    def _exportar_csv(self):
        ruta = filedialog.asksaveasfilename(
            title="Exportar historial", defaultextension=".csv",
            initialfile=ARCHIVO_CSV_DEFECTO, filetypes=[("CSV", "*.csv")],
        )
        if not ruta:
            return
        try:
            cantidad = exportar_csv(filtrar_registros(self.registros, self._emocion_filtrada()), ruta)
        except OSError as error:
            messagebox.showerror("Error", f"No se pudo guardar el archivo: {error}")
            return
        self._mostrar_estado(f"Se exportaron {cantidad} registros a {Path(ruta).name}", COLOR_EXITO)

    # ---------- General ----------

    def _mostrar_estado(self, texto, color):
        self.estado.configure(text=texto, text_color=color)

    def _cerrar(self):
        if self.monitor is not None:
            self.monitor.detener()
            self.monitor = None
        self.destroy()


def main():
    ctk.set_appearance_mode(MODO_APARIENCIA)
    ctk.set_default_color_theme(TEMA_COLOR)
    AplicacionEmociones().mainloop()


if __name__ == "__main__":
    main()
