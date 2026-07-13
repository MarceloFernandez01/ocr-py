"""Ventana única de la aplicación (PySide6): aloja el sidebar y el área de contenido."""

from __future__ import annotations

from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QStackedWidget, QWidget

from model.config_model import load_config
from view.metro_style import get_stylesheet
from view.ocr_view import OcrView
from view.settings_view import SettingsView
from view.sidebar_view import SidebarView

FIXED_SIZE = (1000, 500)
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

LIGHT_PALETTE = {
    QPalette.Window: QColor(240, 240, 240),
    QPalette.WindowText: QColor(20, 20, 20),
    QPalette.Base: QColor(255, 255, 255),
    QPalette.AlternateBase: QColor(240, 240, 240),
    QPalette.ToolTipBase: QColor(20, 20, 20),
    QPalette.ToolTipText: QColor(20, 20, 20),
    QPalette.Text: QColor(20, 20, 20),
    QPalette.Button: QColor(240, 240, 240),
    QPalette.ButtonText: QColor(20, 20, 20),
    QPalette.BrightText: QColor(255, 0, 0),
    QPalette.Highlight: QColor(42, 130, 218),
    QPalette.HighlightedText: QColor(255, 255, 255),
}

THEME_PALETTES = {"dark": DARK_PALETTE, "light": LIGHT_PALETTE}


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

        self.sidebar_view = SidebarView()
        self.sidebar_view.setFixedWidth(SIDEBAR_WIDTH)
        self.ocr_view = OcrView()
        self.settings_view = SettingsView()

        separator = QFrame()
        separator.setObjectName("sidebarSeparator")
        separator.setFrameShape(QFrame.VLine)
        separator.setFixedWidth(1)

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.ocr_view)
        self.content_stack.addWidget(self.settings_view)

        central_widget = QWidget()
        central_layout = QHBoxLayout(central_widget)
        central_layout.setSpacing(0)
        central_layout.addWidget(self.sidebar_view)
        central_layout.addWidget(separator)
        central_layout.addWidget(self.content_stack)
        self.setCentralWidget(central_widget)

        self.sidebar_view.ocr_selected.connect(self._show_ocr_view)
        self.sidebar_view.settings_selected.connect(self._show_settings_view)

        from controller.settings_controller import SettingsController

        self.settings_controller = SettingsController(self.settings_view, self)

        config = load_config()
        self.apply_theme(config["theme"])
        self.settings_view.set_theme(config["theme"])

    def apply_theme(self, theme: str) -> None:
        """Aplica la paleta y el stylesheet correspondientes a `theme` sobre toda la ventana."""
        palette = QPalette()
        for role, color in THEME_PALETTES[theme].items():
            palette.setColor(role, color)
        self.setPalette(palette)
        self.setStyleSheet(get_stylesheet(theme))

    def _show_ocr_view(self) -> None:
        """Cambia el contenido de la ventana a la pantalla de OCR."""
        self.content_stack.setCurrentWidget(self.ocr_view)

    def _show_settings_view(self) -> None:
        """Cambia el contenido de la ventana a la pantalla de Configuración."""
        self.content_stack.setCurrentWidget(self.settings_view)
