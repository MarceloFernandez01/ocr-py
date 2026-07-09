"""Conecta los eventos de la vista con la lógica del Model."""

from tkinter import filedialog

from PIL import Image, ImageTk

from view.main_view import MainView

PREVIEW_MAX_SIZE = (400, 300)


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
