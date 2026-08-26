"""Ventana única de la aplicación (PySide6): aloja el sidebar y el área de contenido."""

from __future__ import annotations

import keyring
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QFrame, QHBoxLayout, QMainWindow, QMessageBox, QStackedWidget, QVBoxLayout, QWidget

from model.claude_usage_model import load_spend
from model.config_model import KEYRING_SERVICE, KEYRING_USERNAME, load_config
from view.live_ocr_view import LiveOcrView
from view.metro_style import get_stylesheet
from view.ocr_view import OcrView
from view.plugins_view import PluginsView
from view.settings_view import SettingsView
from view.sidebar_view import SidebarView
from view.spend_meter_view import BAR_HEIGHT_PX, SpendMeterView

CONTENT_FIXED_SIZE = (1200, 600)
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
    """Ventana principal: sidebar fijo a la izquierda y stack de contenido a la
    derecha, con una barra de gasto de Claude opcional debajo (visible solo
    con motor Claude y API key guardada, ver `refresh_spend_meter()`).

    Tamaño fijo (`setFixedSize`, ajustado según la barra de gasto) y aplica el
    tema según `config_model.load_config()`. No contiene lógica de negocio.
    """

    def __init__(self) -> None:
        """Crea la ventana, el sidebar, el área de contenido y la barra de gasto, y los conecta."""
        super().__init__()
        self.setWindowTitle("OCR")
        self._spend_budget_alert_shown = False

        self.sidebar_view = SidebarView()
        self.sidebar_view.setFixedWidth(SIDEBAR_WIDTH)
        self.ocr_view = OcrView()
        self.live_ocr_view = LiveOcrView()
        self.settings_view = SettingsView()
        self.plugins_view = PluginsView()

        separator = QFrame()
        separator.setObjectName("sidebarSeparator")
        separator.setFrameShape(QFrame.VLine)
        separator.setFixedWidth(1)

        self.content_stack = QStackedWidget()
        self.content_stack.addWidget(self.ocr_view)
        self.content_stack.addWidget(self.live_ocr_view)
        self.content_stack.addWidget(self.settings_view)
        self.content_stack.addWidget(self.plugins_view)

        content_row = QWidget()
        content_row.setFixedHeight(CONTENT_FIXED_SIZE[1])
        content_row_layout = QHBoxLayout(content_row)
        content_row_layout.setContentsMargins(0, 0, 0, 0)
        content_row_layout.setSpacing(0)
        content_row_layout.addWidget(self.sidebar_view)
        content_row_layout.addWidget(separator)
        content_row_layout.addWidget(self.content_stack)

        self.spend_meter_view = SpendMeterView()
        self.spend_meter_view.setVisible(False)

        central_widget = QWidget()
        central_layout = QVBoxLayout(central_widget)
        central_layout.setContentsMargins(0, 0, 0, 0)
        central_layout.setSpacing(0)
        central_layout.addWidget(content_row)
        central_layout.addWidget(self.spend_meter_view)
        self.setCentralWidget(central_widget)

        self.sidebar_view.ocr_selected.connect(self._show_ocr_view)
        self.sidebar_view.live_ocr_selected.connect(self._show_live_ocr_view)
        self.sidebar_view.settings_selected.connect(self._show_settings_view)
        self.sidebar_view.plugins_selected.connect(self._show_plugins_view)

        from controller.live_ocr_controller import LiveOcrController
        from controller.settings_controller import SettingsController

        self.settings_controller = SettingsController(self.settings_view, self)
        self.live_ocr_controller = LiveOcrController(self.live_ocr_view, self)

        config = load_config()
        self.apply_theme(config["theme"])
        self.settings_view.set_theme(config["theme"])
        self.refresh_spend_meter()

    def apply_theme(self, theme: str) -> None:
        """Aplica la paleta y el stylesheet correspondientes a `theme` sobre toda la ventana."""
        palette = QPalette()
        for role, color in THEME_PALETTES[theme].items():
            palette.setColor(role, color)
        self.setPalette(palette)
        self.setStyleSheet(get_stylesheet(theme))
        self.sidebar_view.set_theme(theme)

    def refresh_spend_meter(self) -> None:
        """Actualiza visibilidad y contenido de la barra de gasto de Claude.

        Visible solo con `engine == "claude"` y API key guardada en el
        keyring. Ajusta el alto fijo de la ventana para que el área de
        contenido conserve siempre su tamaño (`CONTENT_FIXED_SIZE`). Con la
        barra visible, avisa una única vez (hasta volver a estar dentro del
        presupuesto) al superar `claude_monthly_budget_usd`.
        """
        config = load_config()
        engine = config.get("engine", "tesseract")
        visible = engine == "claude" and self._has_saved_claude_api_key()

        self.spend_meter_view.setVisible(visible)
        content_width, content_height = CONTENT_FIXED_SIZE
        self.setFixedSize(content_width, content_height + (BAR_HEIGHT_PX if visible else 0))

        if not visible:
            return

        spend = load_spend()
        budget = config.get("claude_monthly_budget_usd", 5.0)
        self.spend_meter_view.set_spend(spend["usd"], spend["calls"], budget)

        over_budget = spend["usd"] > budget
        self.spend_meter_view.set_over_budget(over_budget)
        if over_budget and not self._spend_budget_alert_shown:
            self._spend_budget_alert_shown = True
            QMessageBox.warning(
                self,
                "Presupuesto de Claude superado",
                f"El consumo de Claude Haiku este mes (${spend['usd']:.2f}) superó el "
                f"presupuesto configurado (${budget:.2f}). Las transcripciones siguen funcionando con normalidad.",
            )
        elif not over_budget:
            self._spend_budget_alert_shown = False

    @staticmethod
    def _has_saved_claude_api_key() -> bool:
        """Indica si hay una API key de Anthropic guardada en el keyring del SO."""
        try:
            return keyring.get_password(KEYRING_SERVICE, KEYRING_USERNAME) is not None
        except Exception:
            return False

    def _show_ocr_view(self) -> None:
        """Cambia el contenido de la ventana a la pantalla de OCR, deteniendo OCR en vivo."""
        self.live_ocr_controller.stop()
        self.content_stack.setCurrentWidget(self.ocr_view)

    def _show_live_ocr_view(self) -> None:
        """Cambia el contenido de la ventana a la pantalla de OCR en vivo."""
        self.content_stack.setCurrentWidget(self.live_ocr_view)

    def _show_settings_view(self) -> None:
        """Cambia el contenido de la ventana a la pantalla de Configuración, deteniendo OCR en vivo."""
        self.live_ocr_controller.stop()
        self.content_stack.setCurrentWidget(self.settings_view)

    def _show_plugins_view(self) -> None:
        """Cambia el contenido de la ventana a la pantalla de Plugins, sin detener OCR en vivo."""
        self.content_stack.setCurrentWidget(self.plugins_view)
