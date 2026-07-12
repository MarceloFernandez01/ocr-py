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
        root.columnconfigure(1, weight=1)
        root.rowconfigure(1, weight=1)
        root.rowconfigure(2, weight=1)

        self.open_button = tk.Button(root, text="Abrir imagen")
        self.open_button.grid(row=0, column=0, padx=5, pady=5, sticky="w")

        self.language_var = tk.StringVar(value="Ambos")
        self.language_combobox = ttk.Combobox(
            root,
            textvariable=self.language_var,
            values=LANGUAGE_OPTIONS,
            state="readonly",
        )
        self.language_combobox.grid(row=0, column=1, padx=5, pady=5, sticky="w")

        self.preview_label = tk.Label(root, text="Sin imagen cargada", relief="sunken", width=50, height=25)
        self.preview_label.grid(row=1, column=0, rowspan=2, padx=5, pady=5, sticky="nsew")

        self.transcribe_button = tk.Button(root, text="Transcribir", state="disabled")
        self.transcribe_button.grid(row=1, column=1, padx=5, pady=5, sticky="w")

        self.result_text = tk.Text(root, state="disabled", width=60, height=25)
        self.result_text.grid(row=2, column=1, padx=5, pady=5, sticky="nsew")

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
