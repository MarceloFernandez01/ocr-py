"""Pantalla de Configuración (PySide6): opciones de tema y motor OCR."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ENGINE_OPTIONS = ["Tesseract", "Claude Haiku"]
TRANSLATION_ENGINE_OPTIONS = ["Argos Translate", "Claude Haiku (próximamente)"]

ENGINE_COST_NOTICE_TEXT = (
    "Claude Haiku es un servicio pago de Anthropic: cada imagen transcripta "
    "consume tu cuota de la API (estimado ~USD 0.001-0.02 por imagen, según "
    "tamaño y cantidad de texto, y sujeto al pricing vigente)."
)

MASKED_API_KEY_PLACEHOLDER = "••••••••••••"

TRACK_COLOR_OFF = QColor(120, 120, 120)
TRACK_COLOR_ON = QColor(42, 130, 218)
KNOB_COLOR = QColor(255, 255, 255)


class ThemeSwitch(QPushButton):
    """Botón checkable que se dibuja como un deslizador (perilla animada).

    Solo presentación: no contiene lógica de negocio, expone el mismo
    contrato de `QPushButton` checkable (`isChecked`, `clicked`, `toggled`).
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea el switch, deshabilita el pintado nativo y prepara la animación de la perilla."""
        super().__init__(parent)
        self.setObjectName("themeSwitch")
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(46, 24)

        self._knob_position = 0.0  # 0.0 = perilla a la izquierda, 1.0 = a la derecha

        self._animation = QPropertyAnimation(self, b"knobPosition", self)
        self._animation.setDuration(150)
        self._animation.setEasingCurve(QEasingCurve.InOutCubic)

        self.toggled.connect(self._animate_to)

    def _animate_to(self, checked: bool) -> None:
        """Anima la perilla hacia la posición correspondiente al nuevo estado."""
        self._animation.stop()
        self._animation.setStartValue(self._knob_position)
        self._animation.setEndValue(1.0 if checked else 0.0)
        self._animation.start()

    def _get_knob_position(self) -> float:
        return self._knob_position

    def _set_knob_position(self, value: float) -> None:
        self._knob_position = value
        self.update()

    knobPosition = Property(float, _get_knob_position, _set_knob_position)

    def set_checked_silent(self, checked: bool) -> None:
        """Sincroniza estado y perilla sin animar ni emitir señales (para el controller)."""
        self.blockSignals(True)
        self.setChecked(checked)
        self._knob_position = 1.0 if checked else 0.0
        self.blockSignals(False)
        self.update()

    def paintEvent(self, event) -> None:
        """Dibuja el riel (color interpolado según la posición) y la perilla."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        rect = QRectF(self.rect())
        track_color = QColor(
            TRACK_COLOR_OFF.red() + (TRACK_COLOR_ON.red() - TRACK_COLOR_OFF.red()) * self._knob_position,
            TRACK_COLOR_OFF.green() + (TRACK_COLOR_ON.green() - TRACK_COLOR_OFF.green()) * self._knob_position,
            TRACK_COLOR_OFF.blue() + (TRACK_COLOR_ON.blue() - TRACK_COLOR_OFF.blue()) * self._knob_position,
        )
        painter.setPen(Qt.NoPen)
        painter.setBrush(track_color)
        painter.drawRoundedRect(rect, rect.height() / 2, rect.height() / 2)

        knob_diameter = rect.height() - 4
        knob_x = 2 + self._knob_position * (rect.width() - knob_diameter - 4)
        painter.setBrush(KNOB_COLOR)
        painter.drawEllipse(QRectF(knob_x, 2, knob_diameter, knob_diameter))


class SettingsView(QWidget):
    """Vista de contenido con las opciones de configuración: toggle de tema
    claro/oscuro, selector de motor OCR (Tesseract/Claude Haiku) con carga de
    API key, y placeholder deshabilitado de motor de traducción. No contiene
    lógica de negocio ni persiste ni llama al SDK `anthropic`/`keyring`
    directamente; emite señales para que el controller decida qué hacer.
    """

    theme_toggled = Signal(str)  # "dark" | "light"
    engine_changed = Signal(str)  # "tesseract" | "claude"
    api_key_submitted = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets de la pantalla de Configuración."""
        super().__init__(parent)

        self._api_key_saved = False

        theme_label = QLabel("Tema")
        self.theme_switch = ThemeSwitch()
        self.theme_switch_label = QLabel("Modo oscuro")

        theme_row = QHBoxLayout()
        theme_row.addWidget(self.theme_switch)
        theme_row.addWidget(self.theme_switch_label)
        theme_row.addStretch()

        engine_label = QLabel("Motor OCR")
        self.engine_combobox = QComboBox()
        self.engine_combobox.addItems(ENGINE_OPTIONS)
        self.engine_combobox.setCurrentIndex(0)

        self.engine_cost_notice = QLabel(ENGINE_COST_NOTICE_TEXT)
        self.engine_cost_notice.setObjectName("fieldLabel")
        self.engine_cost_notice.setWordWrap(True)
        self.engine_cost_notice.setVisible(False)

        api_key_label = QLabel("API key de Anthropic")
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.Password)
        self.api_key_input.setPlaceholderText("sk-ant-...")
        self.api_key_button = QPushButton("Guardar")

        api_key_row = QHBoxLayout()
        api_key_row.addWidget(self.api_key_input)
        api_key_row.addWidget(self.api_key_button)

        self.api_key_container = QWidget()
        api_key_layout = QVBoxLayout(self.api_key_container)
        api_key_layout.setContentsMargins(0, 0, 0, 0)
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addLayout(api_key_row)
        self.api_key_container.setVisible(False)

        translation_engine_label = QLabel("Motor de traducción")
        self.translation_engine_combobox = QComboBox()
        self.translation_engine_combobox.addItems(TRANSLATION_ENGINE_OPTIONS)
        self.translation_engine_combobox.setCurrentIndex(0)
        self.translation_engine_combobox.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addWidget(theme_label)
        layout.addLayout(theme_row)
        layout.addWidget(engine_label)
        layout.addWidget(self.engine_combobox)
        layout.addWidget(self.engine_cost_notice)
        layout.addWidget(self.api_key_container)
        layout.addWidget(translation_engine_label)
        layout.addWidget(self.translation_engine_combobox)
        layout.addStretch()

        self.theme_switch.clicked.connect(self._on_theme_switch_clicked)
        self.engine_combobox.currentIndexChanged.connect(self._on_engine_combobox_changed)
        self.api_key_button.clicked.connect(self._on_api_key_button_clicked)

    def _on_theme_switch_clicked(self) -> None:
        """Actualiza el texto del switch y emite `theme_toggled` con el nuevo tema."""
        checked = self.theme_switch.isChecked()
        theme = "light" if checked else "dark"
        self.theme_switch_label.setText("Modo claro" if checked else "Modo oscuro")
        self.theme_toggled.emit(theme)

    def set_theme(self, theme: str) -> None:
        """Sincroniza el estado visual del switch con el tema actual,
        sin emitir `theme_toggled` (evita loops al llamarse desde el controller).
        """
        checked = theme == "light"
        self.theme_switch.set_checked_silent(checked)
        self.theme_switch_label.setText("Modo claro" if checked else "Modo oscuro")

    def _on_engine_combobox_changed(self, index: int) -> None:
        """Actualiza la visibilidad del aviso de costo y el campo de API key,
        y emite `engine_changed` con el nuevo motor seleccionado.
        """
        engine = "claude" if index == 1 else "tesseract"
        self._update_engine_visibility(engine)
        self.engine_changed.emit(engine)

    def _update_engine_visibility(self, engine: str) -> None:
        """Muestra/oculta el aviso de costo y el campo de API key según el motor."""
        is_claude = engine == "claude"
        self.engine_cost_notice.setVisible(is_claude)
        self.api_key_container.setVisible(is_claude)

    def set_engine_silent(self, engine: str) -> None:
        """Sincroniza el combobox de motor con `engine` sin emitir `engine_changed`
        (evita loops al llamarse desde el controller, ej. al revertir una selección).
        """
        index = 1 if engine == "claude" else 0
        self.engine_combobox.blockSignals(True)
        self.engine_combobox.setCurrentIndex(index)
        self.engine_combobox.blockSignals(False)
        self._update_engine_visibility(engine)

    def _on_api_key_button_clicked(self) -> None:
        """Si la key ya está guardada, habilita el campo para reemplazarla;
        si no, emite `api_key_submitted` con el texto ingresado.
        """
        if self._api_key_saved:
            self.set_api_key_saved(False)
            return

        key = self.api_key_input.text()
        if key:
            self.api_key_submitted.emit(key)

    def set_api_key_saved(self, saved: bool) -> None:
        """Alterna el campo de API key entre estado enmascarado (guardado) y editable.

        `saved=True`: campo de solo lectura mostrando `MASKED_API_KEY_PLACEHOLDER`,
        botón "Cambiar". `saved=False`: campo editable y vacío, botón "Guardar".
        """
        self._api_key_saved = saved
        self.api_key_input.setReadOnly(saved)
        if saved:
            self.api_key_input.setText(MASKED_API_KEY_PLACEHOLDER)
            self.api_key_button.setText("Cambiar")
        else:
            self.api_key_input.clear()
            self.api_key_button.setText("Guardar")
