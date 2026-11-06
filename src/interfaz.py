"""Interfaz de escritorio de EmotiContigo."""
import threading
from pathlib import Path
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

try:
    from src.model import DetectorEmociones
except ImportError:  # Permite ejecutar `python src/interfaz.py`
    from model import DetectorEmociones

MODO_APARIENCIA = "light"
TEMA_COLOR = "green"
TITULO = "EmotiContigo"
ANCHO = 1000
ALTO = 700
ANCHO_MINIMO = 850
ALTO_MINIMO = 600
ANCHO_VISTA = 380
ALTO_VISTA = 300
COLOR_ENCABEZADO = "#183B30"
COLOR_TEXTO_ENCABEZADO = "#D0E5DB"
COLOR_FONDO_VISTA = "#E8EFEB"
COLOR_TEXTO_VISTA = "#52665C"
COLOR_PROGRESO = "#239B72"
COLOR_TITULO_SECCION = "#638273"
COLOR_EXITO = "green"
COLOR_ERROR = "red"
COLOR_PROCESO = "orange"
COLOR_TRANSPARENTE = "transparent"
EXTENSIONES = "*.jpg *.jpeg *.png *.bmp"
RETARDO_CARGA_MS = 100
FUENTE = "Arial"
FUENTE_TITULO = (FUENTE, 26, "bold")
FUENTE_SUBTITULO = (FUENTE, 13)
FUENTE_ESTADO = (FUENTE, 12)
FUENTE_PANEL = (FUENTE, 19, "bold")
FUENTE_ETIQUETA = (FUENTE, 12, "bold")
FUENTE_RESULTADO = (FUENTE, 20, "bold")
FUENTE_SECCION = (FUENTE, 15, "bold")
FUENTE_EMOCION = (FUENTE, 13, "bold")
FUENTE_PORCENTAJE = (FUENTE, 11)
ALTO_ENCABEZADO = 90
ALTO_BOTON = 42
ALTO_BARRA = 12
ANCHO_TEXTO_RESULTADO = 350


class AplicacionEmociones(ctk.CTk):
    """Ventana principal: selecciona una imagen y muestra las emociones."""

    def __init__(self, detector=None):
        super().__init__()
        self.detector = detector or DetectorEmociones()
        self.ruta_imagen = None
        self._construir_interfaz()
        self.after(RETARDO_CARGA_MS, self._iniciar_carga_modelo)

    def _construir_interfaz(self):
        self.title(TITULO)
        self.geometry(f"{ANCHO}x{ALTO}")
        self.minsize(ANCHO_MINIMO, ALTO_MINIMO)
        self._crear_encabezado()

        contenido = ctk.CTkFrame(self, fg_color=COLOR_TRANSPARENTE)
        contenido.pack(fill="both", expand=True, padx=25, pady=20)
        self._crear_panel_imagen(contenido)
        self._crear_panel_resultados(contenido)

        self.estado = ctk.CTkLabel(
            self,
            text="Cargando modelo de inteligencia artificial...",
            font=FUENTE_ESTADO,
            text_color=COLOR_PROCESO,
        )
        self.estado.pack(pady=(0, 12))

    def _crear_encabezado(self):
        encabezado = ctk.CTkFrame(
            self,
            height=ALTO_ENCABEZADO,
            corner_radius=0,
            fg_color=COLOR_ENCABEZADO,
        )
        encabezado.pack(fill="x")
        encabezado.pack_propagate(False)

        ctk.CTkLabel(
            encabezado,
            text=TITULO.upper(),
            font=FUENTE_TITULO,
            text_color="white",
        ).pack(pady=(17, 0))

        ctk.CTkLabel(
            encabezado,
            text="Sistema de detección de expresiones faciales",
            font=FUENTE_SUBTITULO,
            text_color=COLOR_TEXTO_ENCABEZADO,
        ).pack()

    def _crear_panel_imagen(self, contenedor):
        panel = ctk.CTkFrame(contenedor, corner_radius=15)
        panel.pack(side="left", fill="both", expand=True, padx=(0, 12))

        ctk.CTkLabel(
            panel,
            text="Imagen seleccionada",
            font=FUENTE_PANEL,
        ).pack(pady=20)

        self.vista_imagen = ctk.CTkLabel(
            panel,
            text="Selecciona una fotografía\npara comenzar",
            width=ANCHO_VISTA,
            height=ALTO_VISTA,
            fg_color=COLOR_FONDO_VISTA,
            corner_radius=12,
            text_color=COLOR_TEXTO_VISTA,
        )
        self.vista_imagen.pack(padx=20, pady=10, fill="both", expand=True)

        self.nombre = ctk.CTkLabel(
            panel,
            text="Ninguna imagen seleccionada",
            font=FUENTE_ESTADO,
        )
        self.nombre.pack(pady=10)

        self.boton_seleccionar = ctk.CTkButton(
            panel,
            text="Seleccionar imagen",
            height=ALTO_BOTON,
            command=self._seleccionar_imagen,
        )
        self.boton_seleccionar.pack(padx=30, pady=10, fill="x")

        self.boton_analizar = ctk.CTkButton(
            panel,
            text="Analizar imagen",
            height=ALTO_BOTON,
            command=self._analizar_imagen,
            state="disabled",
        )
        self.boton_analizar.pack(padx=30, pady=(0, 25), fill="x")

    def _crear_panel_resultados(self, contenedor):
        panel = ctk.CTkFrame(contenedor, corner_radius=15)
        panel.pack(side="right", fill="both", expand=True, padx=(12, 0))

        ctk.CTkLabel(
            panel,
            text="Resultados del análisis",
            font=FUENTE_PANEL,
        ).pack(pady=20)

        ctk.CTkLabel(
            panel,
            text="EXPRESIÓN PRINCIPAL",
            font=FUENTE_ETIQUETA,
            text_color=COLOR_TITULO_SECCION,
        ).pack(pady=(15, 5))

        self.resultado_principal = ctk.CTkLabel(
            panel,
            text="Esperando análisis...",
            font=FUENTE_RESULTADO,
            text_color=COLOR_PROGRESO,
            wraplength=ANCHO_TEXTO_RESULTADO,
        )
        self.resultado_principal.pack(pady=15)

        ctk.CTkLabel(
            panel,
            text="Distribución de expresiones",
            font=FUENTE_SECCION,
        ).pack(pady=10)

        self.resultados_frame = ctk.CTkScrollableFrame(
            panel,
            fg_color=COLOR_TRANSPARENTE,
        )
        self.resultados_frame.pack(
            fill="both",
            expand=True,
            padx=20,
            pady=10,
        )

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
        self.estado.configure(
            text="Modelo cargado correctamente",
            text_color=COLOR_EXITO,
        )
        self.boton_analizar.configure(state="normal")

    def _fallo_carga_modelo(self, mensaje):
        self.estado.configure(
            text="Error al cargar el modelo",
            text_color=COLOR_ERROR,
        )
        messagebox.showerror("Error", mensaje)

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
        foto = ctk.CTkImage(
            light_image=imagen,
            dark_image=imagen,
            size=imagen.size,
        )
        self.vista_imagen.configure(image=foto, text="")
        self.vista_imagen.image = foto
        self.nombre.configure(text=Path(archivo).name)
        self._limpiar_resultados()

    def _analizar_imagen(self):
        if not self.ruta_imagen:
            messagebox.showwarning("Aviso", "Primero selecciona una imagen.")
            return
        self.boton_analizar.configure(state="disabled")
        self.boton_seleccionar.configure(state="disabled")
        self.estado.configure(
            text="Analizando imagen...",
            text_color=COLOR_PROCESO,
        )
        threading.Thread(
            target=self._procesar_imagen,
            args=(self.ruta_imagen,),
            daemon=True,
        ).start()

    def _procesar_imagen(self, ruta):
        try:
            imagen = Image.open(ruta).convert("RGB")
            resultado = self.detector.predecir(imagen)
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
        self.estado.configure(
            text="Error durante el análisis",
            text_color=COLOR_ERROR,
        )
        messagebox.showerror("Error", mensaje)

    def _mostrar_resultados(self, datos):
        self._limpiar_resultados()
        self.resultado_principal.configure(
            text=f"{datos['emocion']}  |  {datos['confianza']:.2f}%"
        )
        for emocion, porcentaje in datos["todas"].items():
            self._agregar_barra(emocion, porcentaje)
        self.estado.configure(
            text="Análisis completado",
            text_color=COLOR_EXITO,
        )

    def _agregar_barra(self, emocion, porcentaje):
        fila = ctk.CTkFrame(self.resultados_frame, fg_color=COLOR_TRANSPARENTE)
        fila.pack(fill="x", pady=5)

        ctk.CTkLabel(
            fila,
            text=emocion,
            font=FUENTE_EMOCION,
        ).pack(anchor="w")

        barra = ctk.CTkProgressBar(
            fila,
            height=ALTO_BARRA,
            progress_color=COLOR_PROGRESO,
        )
        barra.pack(fill="x", pady=3)
        barra.set(porcentaje / 100)

        ctk.CTkLabel(
            fila,
            text=f"{porcentaje:.2f}%",
            font=FUENTE_PORCENTAJE,
        ).pack(anchor="e")

    def _limpiar_resultados(self):
        for widget in self.resultados_frame.winfo_children():
            widget.destroy()
        self.resultado_principal.configure(text="Esperando análisis...")


def main():
    ctk.set_appearance_mode(MODO_APARIENCIA)
    ctk.set_default_color_theme(TEMA_COLOR)
    AplicacionEmociones().mainloop()


if __name__ == "__main__":
    main()
