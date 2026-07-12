"""Ventana principal de la aplicación (layout y widgets Tkinter)."""

import tkinter as tk
from tkinter import ttk

LANGUAGE_OPTIONS = ["Español", "Inglés", "Ambos"]


class MainView:
    """Construye y expone los widgets de la ventana principal.

    No contiene lógica de negocio: solo layout y setters/getters simples.
    El Controller conecta los eventos (`open_button`, `transcribe_button`)
    con el Model.
    """

    def __init__(self, root: tk.Tk) -> None:
        """Crea los widgets de la ventana sobre el `root` recibido."""
        self.root = root

        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)

        toolbar = tk.Frame(root)
        toolbar.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.open_button = tk.Button(toolbar, text="Abrir imagen")
        self.open_button.pack(side="left")

        self.language_var = tk.StringVar(value="Ambos")
        self.language_combobox = ttk.Combobox(
            toolbar,
            textvariable=self.language_var,
            values=LANGUAGE_OPTIONS,
            state="readonly",
            width=12,
        )
        self.language_combobox.pack(side="left", padx=5)

        self.transcribe_button = tk.Button(toolbar, text="Transcribir", state="disabled")
        self.transcribe_button.pack(side="left")

        paned = ttk.PanedWindow(root, orient="horizontal")
        paned.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        preview_frame = tk.Frame(paned)
        self.preview_label = tk.Label(
            preview_frame, text="Sin imagen cargada", relief="sunken", anchor="center"
        )
        self.preview_label.pack(fill="both", expand=True)
        paned.add(preview_frame, weight=1)

        result_frame = tk.Frame(paned)
        result_frame.columnconfigure(0, weight=1)
        result_frame.rowconfigure(0, weight=1)
        self.result_text = tk.Text(result_frame, state="disabled", wrap="word")
        self.result_text.grid(row=0, column=0, sticky="nsew")
        result_scrollbar = ttk.Scrollbar(result_frame, orient="vertical", command=self.result_text.yview)
        result_scrollbar.grid(row=0, column=1, sticky="ns")
        self.result_text.configure(yscrollcommand=result_scrollbar.set)
        paned.add(result_frame, weight=1)

    def set_preview_image(self, photo_image: tk.PhotoImage) -> None:
        """Muestra la imagen recibida en el área de vista previa."""
        self.preview_label.configure(image=photo_image, text="")
        self.preview_label.image = photo_image

    def set_result_text(self, text: str) -> None:
        """Reemplaza el contenido del bloque de resultado con `text`."""
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", tk.END)
        self.result_text.insert("1.0", text)
        self.result_text.configure(state="disabled")

    def get_selected_language(self) -> str:
        """Devuelve la opción de idioma seleccionada actualmente."""
        return self.language_var.get()

    def enable_transcribe_button(self) -> None:
        """Habilita el botón "Transcribir"."""
        self.transcribe_button.configure(state="normal")

    def disable_transcribe_button(self) -> None:
        """Deshabilita el botón "Transcribir"."""
        self.transcribe_button.configure(state="disabled")
