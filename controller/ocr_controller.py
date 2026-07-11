"""Conecta los eventos de la vista con la lógica del Model."""

import os
import threading
import time
from tkinter import filedialog, messagebox

from PIL import Image, ImageTk

from model.config_model import save_tesseract_path
from model.ocr_model import transcribe_large_image
from model.tesseract_locator import resolve_tesseract_path
from view.main_view import MainView

PREVIEW_MAX_SIZE = (400, 300)
COUNTER_INTERVAL_MS = 200

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
        self.transcription_in_progress: bool = False


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

        try:
            image = Image.open(path)
            image.thumbnail(PREVIEW_MAX_SIZE)
            photo_image = ImageTk.PhotoImage(image)
        except Exception as error:
            messagebox.showerror("Error al cargar la imagen", str(error))
            return

        self.view.set_preview_image(photo_image)
        self.state.image_path = path
        self.view.enable_transcribe_button()

    def on_transcribe(self) -> None:
        """Transcribe la imagen cargada usando el idioma seleccionado en la vista."""
        if self.state.transcription_in_progress:
            return

        self.state.selected_language = self.view.get_selected_language()
        language_code = LANGUAGE_MAP[self.state.selected_language]
        tesseract_path = resolve_tesseract_path()

        if tesseract_path is None:
            tesseract_path = self._prompt_tesseract_path()
            if tesseract_path is None:
                return

        self._start_transcription(language_code, tesseract_path)

    def _start_transcription(self, language_code: str, tesseract_path: str | None) -> None:
        """Lanza la transcripción en un hilo aparte y arranca el contador de segundos en vivo."""
        self.state.transcription_in_progress = True
        self.view.disable_transcribe_button()
        self._transcription_result: str | None = None
        self._transcription_error: Exception | None = None
        self._transcription_start = time.monotonic()

        thread = threading.Thread(
            target=self._run_transcription,
            args=(language_code, tesseract_path),
            daemon=True,
        )
        thread.start()
        self._poll_transcription(thread)

    def _run_transcription(self, language_code: str, tesseract_path: str | None) -> None:
        """Corre en el hilo secundario: transcribe y guarda el resultado o el error."""
        try:
            self._transcription_result = transcribe_large_image(self.state.image_path, language_code, tesseract_path)
        except Exception as error:
            self._transcription_error = error

    def _poll_transcription(self, thread: threading.Thread) -> None:
        """Actualiza el contador de segundos cada `COUNTER_INTERVAL_MS` mientras el hilo sigue vivo."""
        if thread.is_alive():
            elapsed = int(time.monotonic() - self._transcription_start)
            self.view.set_result_text(f"Procesando... {elapsed}s")
            self.view.root.after(COUNTER_INTERVAL_MS, lambda: self._poll_transcription(thread))
            return

        if self._transcription_error is not None:
            messagebox.showerror("Error al transcribir", str(self._transcription_error))
        else:
            self.view.set_result_text(self._transcription_result)

        self.state.transcription_in_progress = False
        self.view.enable_transcribe_button()

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
