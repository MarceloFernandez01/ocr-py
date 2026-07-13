"""Ventana única de la aplicación (PySide6): aloja el sidebar y el área de contenido."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from model.config_model import load_config
from view.ocr_view import OcrView
from view.sidebar_view import SidebarView

FIXED_SIZE = (1200, 900)
SIDEBAR_WIDTH = 200

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
    """Ventana principal: sidebar fijo a la izquierda y stack de contenido a la derecha.

    Tamaño fijo (`setFixedSize`) y aplica el tema según
    `config_model.load_config()`. No contiene lógica de negocio.
    """

    def __init__(self) -> None:
        """Crea la ventana, el sidebar y el área de contenido, y los conecta."""
        super().__init__()
        self.setWindowTitle("OCR")
        self.setFixedSize(*FIXED_SIZE)

        config = load_config()
        if config.get("theme", "dark") == "dark":
            apply_dark_theme(self)

        self.sidebar_view = SidebarView()
        self.sidebar_view.setFixedWidth(SIDEBAR_WIDTH)
        self.ocr_view = OcrView()

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.ocr_view)

        central_widget = QWidget()
        central_layout = QHBoxLayout(central_widget)
        central_layout.addWidget(self.sidebar_view)
        central_layout.addWidget(self.content_stack)
        self.setCentralWidget(central_widget)

        self.sidebar_view.ocr_selected.connect(self._show_ocr_view)

    def _show_ocr_view(self) -> None:
        """Cambia el contenido de la ventana a la pantalla de OCR."""
        self.content_stack.setCurrentWidget(self.ocr_view)
