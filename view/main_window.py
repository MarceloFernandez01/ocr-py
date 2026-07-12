"""Ventana única de la aplicación (PySide6): aloja el menú de inicio y la pantalla de OCR."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QMainWindow, QStackedWidget, QWidget

from model.config_model import load_config
from view.home_view import HomeView
from view.ocr_view import OcrView

DEFAULT_SIZE = (1200, 900)
MINIMUM_SIZE = (600, 400)

DARK_PALETTE = {
    QPalette.Window: QColor(53, 53, 53),
    QPalette.WindowText: QColor(255, 255, 255),
    QPalette.Base: QColor(35, 35, 35),
    QPalette.AlternateBase: QColor(53, 53, 53),
    QPalette.ToolTipBase: QColor(255, 255, 255),
    QPalette.ToolTipText: QColor(255, 255, 255),
    QPalette.Text: QColor(255, 255, 255),
    QPalette.Button: QColor(53, 53, 53),
    QPalette.ButtonText: QColor(255, 255, 255),
    QPalette.BrightText: QColor(255, 0, 0),
    QPalette.Highlight: QColor(42, 130, 218),
    QPalette.HighlightedText: QColor(35, 35, 35),
}


def apply_dark_theme(widget: QWidget) -> None:
    """Aplica la paleta oscura fija a `widget` (y por herencia, a sus hijos)."""
    palette = QPalette()
    for role, color in DARK_PALETTE.items():
        palette.setColor(role, color)
    widget.setPalette(palette)


class MainWindow(QMainWindow):
    """Ventana principal: contiene un `QStackedWidget` con `HomeView` y `OcrView`.

    Fija el tamaño default/mínimo de la ventana y aplica el tema según
    `config_model.load_config()`. No contiene lógica de negocio.
    """

    def __init__(self) -> None:
        """Crea la ventana, sus pantallas y conecta la navegación entre ellas."""
        super().__init__()
        self.setWindowTitle("OCR")
        self.resize(*DEFAULT_SIZE)
        self.setMinimumSize(*MINIMUM_SIZE)

        config = load_config()
        if config.get("theme", "dark") == "dark":
            apply_dark_theme(self)

        self.home_view = HomeView()
        self.ocr_view = OcrView()

        self.stacked_widget = QStackedWidget()
        self.stacked_widget.addWidget(self.home_view)
        self.stacked_widget.addWidget(self.ocr_view)
        self.setCentralWidget(self.stacked_widget)

        self.home_view.ocr_selected.connect(self._show_ocr_view)
        self.ocr_view.back_requested.connect(self._show_home_view)

    def _show_ocr_view(self) -> None:
        """Cambia el contenido de la ventana a la pantalla de OCR."""
        self.stacked_widget.setCurrentWidget(self.ocr_view)

    def _show_home_view(self) -> None:
        """Cambia el contenido de la ventana al menú de inicio."""
        self.stacked_widget.setCurrentWidget(self.home_view)
