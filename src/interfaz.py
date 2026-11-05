"""Interfaz de escritorio de EmotiContigo."""
import os
import threading
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
from PIL import Image

try:
    from src.historial import (
        RUTA_POR_DEFECTO, guardar_analisis, inicializar_bd, listar_historial, obtener_estadisticas,
    )
    from src.model import DetectorEmociones
    from src.preprocess import EMOCIONES, EXTENSIONES_VALIDAS
except ImportError:  # Permite ejecutar `python src/interfaz.py`
    from historial import (
        RUTA_POR_DEFECTO, guardar_analisis, inicializar_bd, listar_historial, obtener_estadisticas,
    )
    from model import DetectorEmociones
    from preprocess import EMOCIONES, EXTENSIONES_VALIDAS

MODO_APARIENCIA = "light"
TEMA_COLOR = "green"
TITULO = "EmotiContigo"
ANCHO = 1100
ALTO = 760
ANCHO_MINIMO = 950
ALTO_MINIMO = 680
ANCHO_VISTA = 400
ALTO_VISTA = 300
EXTENSIONES = " ".join("*" + extension for extension in EXTENSIONES_VALIDAS)
RETARDO_CARGA_MS = 100
PORCENTAJE_MAXIMO = 100
ULTIMOS_ANALISIS = 6
FORMATO_FECHA = "%d/%m/%Y  %H:%M"

PESTANA_ANALISIS = "Análisis"
PESTANA_ESTADISTICAS = "Estadísticas"

# Colores
COLOR_FONDO = "#EEF3F0"
COLOR_PANEL = "#FFFFFF"
COLOR_ENCABEZADO = "#183B30"
COLOR_TEXTO_ENCABEZADO = "#D0E5DB"
COLOR_FONDO_VISTA = "#E8EFEB"
COLOR_TEXTO = "#1F2D27"
COLOR_TEXTO_SUAVE = "#52665C"
COLOR_TITULO_SECCION = "#638273"
COLOR_PISTA_BARRA = "#E3EAE6"
COLOR_BORDE = "#D5E0DA"
COLOR_BOTON = "#239B72"
COLOR_BOTON_HOVER = "#1C7D5C"
COLOR_BOTON_SECUNDARIO = "#E3EAE6"
COLOR_BOTON_SECUNDARIO_HOVER = "#D2DDD7"
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
RADIO_PANEL = 14
RADIO_VISTA = 12
RADIO_BOTON = 10
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
FUENTE_SECCION = (FUENTE, 17, "bold")
FUENTE_NORMAL = (FUENTE, 12)
FUENTE_ETIQUETA = (FUENTE, 11, "bold")
FUENTE_RESULTADO = (FUENTE, 30, "bold")
FUENTE_CONFIANZA = (FUENTE, 15)
FUENTE_EMOCION = (FUENTE, 13, "bold")
FUENTE_PORCENTAJE = (FUENTE, 12)
FUENTE_BOTON = (FUENTE, 13, "bold")
FUENTE_KPI = (FUENTE, 26, "bold")
FUENTE_GRAFICO = 10


SIN_DATO = "—"
DECIMALES = 2

COLORES_EMOCION = {
    "enfado": "#D64545",
    "asco": "#6E8B2E",
    "miedo": "#7B5EA7",
    "felicidad": "#E0A100",
    "tristeza": "#3B7DD8",
    "sorpresa": "#E07B39",
    "neutral": "#7D8F87",
}
COLOR_DEFECTO = "#239B72"


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


class AplicacionEmociones(ctk.CTk):
    """Ventana principal: analiza una foto y muestra estadísticas del historial."""

    def __init__(self, detector=None, ruta_bd=None):
        super().__init__(fg_color=COLOR_FONDO)
        self.detector = detector or DetectorEmociones()
        self.ruta_bd = ruta_bd or os.getenv("EMOTI_BD") or RUTA_POR_DEFECTO
        inicializar_bd(self.ruta_bd)
        self.ruta_imagen = None
        self.modelo_listo = False
        self._construir_interfaz()
        self._actualizar_estadisticas()
        self.after(RETARDO_CARGA_MS, self._iniciar_carga_modelo)

    # ---------- Construcción ----------

    def _construir_interfaz(self):
        self.title(TITULO)
        self.geometry(f"{ANCHO}x{ALTO}")
        self.minsize(ANCHO_MINIMO, ALTO_MINIMO)
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
        self._crear_pestana_analisis(self.pestanas.add(PESTANA_ANALISIS))
        self._crear_pestana_estadisticas(self.pestanas.add(PESTANA_ESTADISTICAS))

        self.estado = ctk.CTkLabel(
            self,
            text="Cargando modelo de inteligencia artificial...",
            font=FUENTE_NORMAL,
            text_color=COLOR_PROCESO,
        )
        self.estado.pack(pady=SEPARACION)

    def _crear_encabezado(self):
        encabezado = ctk.CTkFrame(
            self, height=ALTO_ENCABEZADO, corner_radius=0, fg_color=COLOR_ENCABEZADO,
        )
        encabezado.pack(fill="x")
        encabezado.pack_propagate(False)

        textos = ctk.CTkFrame(encabezado, fg_color=COLOR_TRANSPARENTE)
        textos.place(relx=0.5, rely=0.5, anchor="center")
        ctk.CTkLabel(
            textos, text="EMOTICONTIGO", font=FUENTE_TITULO, text_color=COLOR_TEXTO_TARJETA,
        ).pack()
        ctk.CTkLabel(
            textos,
            text="Apoyo al docente para observar expresiones faciales",
            font=FUENTE_SUBTITULO,
            text_color=COLOR_TEXTO_ENCABEZADO,
        ).pack()

    def _crear_panel(self, contenedor):
        return ctk.CTkFrame(
            contenedor,
            corner_radius=RADIO_PANEL,
            fg_color=COLOR_PANEL,
            border_width=BORDE,
            border_color=COLOR_BORDE,
        )

    def _titulo_seccion(self, contenedor, texto):
        ctk.CTkLabel(
            contenedor, text=texto, font=FUENTE_SECCION, text_color=COLOR_TEXTO, anchor="w",
        ).pack(fill="x", padx=MARGEN, pady=(MARGEN, SEPARACION))

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
        self._titulo_seccion(panel, "Fotografía")

        self.vista_imagen = ctk.CTkLabel(
            panel,
            text="Selecciona una fotografía del rostro\n(jpg o png)",
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

        ctk.CTkLabel(
            panel,
            text="La expresión es una señal de apoyo; no mide si el estudiante aprendió.",
            font=FUENTE_PORCENTAJE,
            text_color=COLOR_TEXTO_SUAVE,
        ).pack(pady=(0, SEPARACION))

    def _crear_pestana_estadisticas(self, pestana):
        pestana.grid_columnconfigure(0, weight=3)
        pestana.grid_columnconfigure(1, weight=2)
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

        panel_historial = self._crear_panel(pestana)
        panel_historial.grid(row=1, column=1, sticky="nsew", padx=(SEPARACION, 0))
        self._titulo_seccion(panel_historial, "Últimos análisis")
        self.lista_historial = ctk.CTkScrollableFrame(panel_historial, fg_color=COLOR_TRANSPARENTE)
        self.lista_historial.pack(fill="both", expand=True, padx=SEPARACION)
        self._crear_boton(
            panel_historial, "Actualizar", self._actualizar_estadisticas, principal=False,
        ).pack(fill="x", padx=MARGEN, pady=MARGEN)

    def _crear_kpi(self, contenedor, columna, titulo):
        tarjeta = self._crear_panel(contenedor)
        tarjeta.grid(row=0, column=columna, sticky="ew", padx=SEPARACION_CHICA)
        ctk.CTkLabel(
            tarjeta, text=titulo, font=FUENTE_ETIQUETA, text_color=COLOR_TITULO_SECCION,
        ).pack(pady=(MARGEN, 0))
        valor = ctk.CTkLabel(tarjeta, text="—", font=FUENTE_KPI, text_color=COLOR_TEXTO)
        valor.pack(pady=(0, MARGEN))
        return valor

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
        self._mostrar_estado("Modelo listo. Selecciona una fotografía.", COLOR_EXITO)
        if self.ruta_imagen:
            self.boton_analizar.configure(state="normal")

    def _fallo_carga_modelo(self, mensaje):
        self._mostrar_estado("No se pudo cargar el modelo", COLOR_ERROR)
        messagebox.showerror("Error", mensaje)

    # ---------- Análisis ----------

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
            self._agregar_barra(emocion, porcentaje)
        self._mostrar_estado("Análisis completado y guardado en el historial", COLOR_EXITO)
        self._actualizar_estadisticas()

    def _agregar_barra(self, emocion, porcentaje):
        fila = ctk.CTkFrame(self.resultados_frame, fg_color=COLOR_TRANSPARENTE)
        fila.pack(fill="x", padx=SEPARACION, pady=SEPARACION_CHICA)
        fila.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(
            fila, text=nombre_visible(emocion), font=FUENTE_EMOCION, text_color=COLOR_TEXTO, anchor="w",
        ).grid(row=0, column=0, sticky="w")
        ctk.CTkLabel(
            fila, text=texto_confianza(porcentaje), font=FUENTE_PORCENTAJE, text_color=COLOR_TEXTO_SUAVE,
        ).grid(row=0, column=1, sticky="e")

        barra = ctk.CTkProgressBar(
            fila, height=ALTO_BARRA, progress_color=color_emocion(emocion), fg_color=COLOR_PISTA_BARRA,
        )
        barra.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(SEPARACION_CHICA, 0))
        barra.set(porcentaje / PORCENTAJE_MAXIMO)

    def _limpiar_resultados(self):
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()
        self.tarjeta.configure(fg_color=COLOR_FONDO_VISTA)
        self.tarjeta_etiqueta.configure(text_color=COLOR_TITULO_SECCION)
        self.resultado_principal.configure(text="Esperando análisis", text_color=COLOR_TEXTO_SUAVE)
        self.resultado_confianza.configure(text="")

    # ---------- Estadísticas ----------

    def _cambiar_pestana(self):
        if self.pestanas.get() == PESTANA_ESTADISTICAS:
            self._actualizar_estadisticas()

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
        self._mostrar_historial()

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

    def _mostrar_historial(self):
        for widget in self.lista_historial.winfo_children():
            widget.destroy()
        registros = listar_historial(self.ruta_bd, ULTIMOS_ANALISIS)
        if not registros:
            ctk.CTkLabel(
                self.lista_historial, text="Sin registros todavía", font=FUENTE_NORMAL,
                text_color=COLOR_TEXTO_SUAVE,
            ).pack(pady=MARGEN)
            return
        for registro in registros:
            self._agregar_registro(registro)

    def _agregar_registro(self, registro):
        fila = ctk.CTkFrame(self.lista_historial, fg_color=COLOR_FONDO_VISTA, corner_radius=RADIO_BOTON)
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

    def _mostrar_estado(self, texto, color):
        self.estado.configure(text=texto, text_color=color)


def main():
    ctk.set_appearance_mode(MODO_APARIENCIA)
    ctk.set_default_color_theme(TEMA_COLOR)
    AplicacionEmociones().mainloop()


if __name__ == "__main__":
    main()