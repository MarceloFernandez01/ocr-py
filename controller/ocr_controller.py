"""Conecta los eventos de la vista con la lógica del Model."""

import os
from tkinter import filedialog

from PIL import Image, ImageTk

from model.config_model import save_tesseract_path
from model.ocr_model import transcribe
from model.tesseract_locator import resolve_tesseract_path
from view.main_view import MainView

PREVIEW_MAX_SIZE = (400, 300)

LANGUAGE_MAP = {
    "Español": "spa",
    "Inglés": "eng",
    "Ambos": "spa+eng",
}


class AppState:
    """Estado en memoria de la app mientras está abierta (no persistido)."""

    def __init__(self) -> None:
        self.image_path: str | None = None
        self.selected_language: str = "Ambos"
        self.tesseract_ready: bool = False


class OcrController:
    """Conecta los botones de la vista con las acciones de carga y transcripción."""

    def __init__(self, view: MainView) -> None:
        """Registra los callbacks de la vista y crea el estado en memoria."""
        self.view = view
        self.state = AppState()

        self.view.open_button.configure(command=self.on_open_image)
        self.view.transcribe_button.configure(command=self.on_transcribe)

    def on_open_image(self) -> None:
        """Abre un diálogo de selección de archivo, carga la imagen y actualiza la vista previa."""
        path = filedialog.askopenfilename(title="Abrir imagen")
        if not path:
            return

        image = Image.open(path)
        image.thumbnail(PREVIEW_MAX_SIZE)
        photo_image = ImageTk.PhotoImage(image)

        self.view.set_preview_image(photo_image)
        self.state.image_path = path
        self.view.enable_transcribe_button()

    def on_transcribe(self) -> None:
        """Transcribe la imagen cargada usando el idioma seleccionado en la vista."""
        self.state.selected_language = self.view.get_selected_language()
        language_code = LANGUAGE_MAP[self.state.selected_language]
        tesseract_path = resolve_tesseract_path()

        if tesseract_path is None:
            tesseract_path = self._prompt_tesseract_path()
            if tesseract_path is None:
                return

        result = transcribe(self.state.image_path, language_code, tesseract_path)
        self.view.set_result_text(result)

    def _prompt_tesseract_path(self) -> str | None:
        """Pide al usuario la ruta del ejecutable de Tesseract y la persiste si es válida."""
        path = filedialog.askopenfilename(
            title="Ubicar tesseract.exe",
            filetypes=[("Ejecutables", "*.exe")],
        )
        if not path or not os.path.exists(path):
            return None

        save_tesseract_path(path)
        return path
