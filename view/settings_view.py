"""Pantalla de Configuración (PySide6): opciones de tema y motor OCR."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QDoubleValidator, QKeySequence, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QLineEdit,
    QPushButton,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from model.config_model import load_config
from model.plugin_registry import list_providers

ENGINE_COST_NOTICE_TEXT = (
    "Claude Haiku es un servicio pago de Anthropic: cada imagen transcripta "
    "consume la cuota de la API. Consultar el pricing vigente en "
    "anthropic.com antes de usarlo."
)

LIVE_CLAUDE_COST_NOTICE_TEXT = (
    "Con OCR en vivo, cada cambio de texto detectado genera una llamada "
    "paga a Claude Haiku, sujeta al cooldown configurado más abajo."
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
    claro/oscuro, selector de motor OCR y de motor de traducción (ambos
    alimentados desde `model/plugin_registry.list_providers`) con carga de
    API key para Claude, control de confianza mínima por palabra para el
    filtro de ruido de Tesseract, sensibilidad del filtro de cambio de texto
    y de píxeles en OCR en vivo, interruptor y controles de Claude en OCR en
    vivo (cooldown, presupuesto mensual), y atajos globales de OCR en vivo
    (pausar/reanudar, cerrar overlay).
    No contiene lógica de negocio ni persiste ni llama al SDK
    `anthropic`/`keyring` directamente; emite señales para que el controller
    decida qué hacer.
    """

    theme_toggled = Signal(str)  # "dark" | "light"
    engine_changed = Signal(str)  # id del plugin de OCR
    translation_engine_changed = Signal(str)  # id del plugin de traducción
    api_key_submitted = Signal(str)
    min_word_confidence_changed = Signal(int)
    live_claude_toggled = Signal(bool)
    text_similarity_threshold_changed = Signal(int)
    pixel_change_sensitivity_changed = Signal(int)
    claude_cooldown_changed = Signal(int)
    claude_budget_changed = Signal(float)
    hotkey_toggle_changed = Signal(str)
    hotkey_close_changed = Signal(str)

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
        for plugin in list_providers("ocr"):
            self.engine_combobox.addItem(plugin.name, plugin.id)
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

        initial_config = load_config()

        min_word_confidence_label = QLabel("Filtrar ruido (confianza mínima)")
        initial_min_word_confidence = initial_config.get("min_word_confidence", 95)
        self.min_word_confidence_slider = QSlider(Qt.Horizontal)
        self.min_word_confidence_slider.setRange(0, 100)
        self.min_word_confidence_slider.setValue(initial_min_word_confidence)
        self.min_word_confidence_value_label = QLabel(str(initial_min_word_confidence))

        min_word_confidence_row = QHBoxLayout()
        min_word_confidence_row.addWidget(self.min_word_confidence_slider)
        min_word_confidence_row.addWidget(self.min_word_confidence_value_label)

        text_similarity_threshold_label = QLabel("Sensibilidad al cambio de texto")
        initial_text_similarity_threshold = initial_config.get("text_similarity_threshold", 90)
        self.text_similarity_threshold_slider = QSlider(Qt.Horizontal)
        self.text_similarity_threshold_slider.setRange(0, 100)
        self.text_similarity_threshold_slider.setValue(initial_text_similarity_threshold)
        self.text_similarity_threshold_value_label = QLabel(str(initial_text_similarity_threshold))

        text_similarity_threshold_row = QHBoxLayout()
        text_similarity_threshold_row.addWidget(self.text_similarity_threshold_slider)
        text_similarity_threshold_row.addWidget(self.text_similarity_threshold_value_label)

        pixel_change_sensitivity_label = QLabel("Sensibilidad al cambio de imagen")
        initial_pixel_change_sensitivity = initial_config.get("pixel_change_sensitivity", 2)
        self.pixel_change_sensitivity_slider = QSlider(Qt.Horizontal)
        self.pixel_change_sensitivity_slider.setRange(0, 100)
        self.pixel_change_sensitivity_slider.setValue(initial_pixel_change_sensitivity)
        self.pixel_change_sensitivity_value_label = QLabel(str(initial_pixel_change_sensitivity))

        pixel_change_sensitivity_row = QHBoxLayout()
        pixel_change_sensitivity_row.addWidget(self.pixel_change_sensitivity_slider)
        pixel_change_sensitivity_row.addWidget(self.pixel_change_sensitivity_value_label)

        self.live_claude_switch = ThemeSwitch()
        self.live_claude_switch_label = QLabel("Usar Claude también en OCR en vivo")
        initial_live_claude_enabled = initial_config.get("live_claude_enabled", False)
        self.live_claude_switch.set_checked_silent(initial_live_claude_enabled)

        live_claude_row = QHBoxLayout()
        live_claude_row.addWidget(self.live_claude_switch)
        live_claude_row.addWidget(self.live_claude_switch_label)
        live_claude_row.addStretch()

        self.live_claude_cost_notice = QLabel(LIVE_CLAUDE_COST_NOTICE_TEXT)
        self.live_claude_cost_notice.setObjectName("fieldLabel")
        self.live_claude_cost_notice.setWordWrap(True)

        self.live_claude_container = QWidget()
        live_claude_layout = QVBoxLayout(self.live_claude_container)
        live_claude_layout.setContentsMargins(0, 0, 0, 0)
        live_claude_layout.addLayout(live_claude_row)
        live_claude_layout.addWidget(self.live_claude_cost_notice)
        self.live_claude_container.setVisible(False)

        claude_cooldown_label = QLabel("Tiempo mínimo entre llamadas a Claude (s)")
        initial_claude_cooldown_seconds = initial_config.get("claude_cooldown_seconds", 10)
        self.claude_cooldown_slider = QSlider(Qt.Horizontal)
        self.claude_cooldown_slider.setRange(1, 120)
        self.claude_cooldown_slider.setValue(initial_claude_cooldown_seconds)
        self.claude_cooldown_value_label = QLabel(str(initial_claude_cooldown_seconds))

        claude_cooldown_row = QHBoxLayout()
        claude_cooldown_row.addWidget(self.claude_cooldown_slider)
        claude_cooldown_row.addWidget(self.claude_cooldown_value_label)

        self.claude_cooldown_container = QWidget()
        claude_cooldown_layout = QVBoxLayout(self.claude_cooldown_container)
        claude_cooldown_layout.setContentsMargins(0, 0, 0, 0)
        claude_cooldown_layout.addWidget(claude_cooldown_label)
        claude_cooldown_layout.addLayout(claude_cooldown_row)
        self.claude_cooldown_container.setVisible(False)

        claude_budget_label = QLabel("Presupuesto mensual (USD)")
        initial_claude_monthly_budget_usd = initial_config.get("claude_monthly_budget_usd", 5.0)
        self.claude_budget_input = QLineEdit(str(initial_claude_monthly_budget_usd))
        self.claude_budget_input.setValidator(QDoubleValidator(0.0, 1_000_000.0, 2, self.claude_budget_input))

        self.claude_budget_container = QWidget()
        claude_budget_layout = QVBoxLayout(self.claude_budget_container)
        claude_budget_layout.setContentsMargins(0, 0, 0, 0)
        claude_budget_layout.addWidget(claude_budget_label)
        claude_budget_layout.addWidget(self.claude_budget_input)
        self.claude_budget_container.setVisible(False)

        hotkeys_label = QLabel("OCR en vivo · atajos globales")

        hotkey_toggle_label = QLabel("Atajo pausar/reanudar")
        initial_hotkey_toggle = initial_config.get("hotkey_toggle", "Ctrl+Shift+P")
        self.hotkey_toggle_edit = QKeySequenceEdit(QKeySequence(initial_hotkey_toggle))

        hotkey_close_label = QLabel("Atajo cerrar overlay")
        initial_hotkey_close = initial_config.get("hotkey_close", "Ctrl+Shift+Q")
        self.hotkey_close_edit = QKeySequenceEdit(QKeySequence(initial_hotkey_close))

        hotkeys_row = QHBoxLayout()
        hotkey_toggle_layout = QVBoxLayout()
        hotkey_toggle_layout.addWidget(hotkey_toggle_label)
        hotkey_toggle_layout.addWidget(self.hotkey_toggle_edit)
        hotkey_close_layout = QVBoxLayout()
        hotkey_close_layout.addWidget(hotkey_close_label)
        hotkey_close_layout.addWidget(self.hotkey_close_edit)
        hotkeys_row.addLayout(hotkey_toggle_layout)
        hotkeys_row.addLayout(hotkey_close_layout)
        hotkeys_row.addStretch()

        self.hotkey_warning_label = QLabel("")
        self.hotkey_warning_label.setObjectName("hotkeyWarningLabel")
        self.hotkey_warning_label.setWordWrap(True)
        self.hotkey_warning_label.setVisible(False)

        translation_engine_label = QLabel("Motor de traducción")
        self.translation_engine_combobox = QComboBox()
        for plugin in list_providers("translation"):
            self.translation_engine_combobox.addItem(plugin.name, plugin.id)
        self.translation_engine_combobox.setCurrentIndex(0)

        layout = QVBoxLayout(self)
        layout.addWidget(theme_label)
        layout.addLayout(theme_row)
        layout.addWidget(engine_label)
        layout.addWidget(self.engine_combobox)
        layout.addWidget(self.engine_cost_notice)
        layout.addWidget(self.api_key_container)
        layout.addWidget(min_word_confidence_label)
        layout.addLayout(min_word_confidence_row)
        layout.addWidget(text_similarity_threshold_label)
        layout.addLayout(text_similarity_threshold_row)
        layout.addWidget(pixel_change_sensitivity_label)
        layout.addLayout(pixel_change_sensitivity_row)
        layout.addWidget(self.live_claude_container)
        layout.addWidget(self.claude_cooldown_container)
        layout.addWidget(self.claude_budget_container)
        layout.addWidget(hotkeys_label)
        layout.addLayout(hotkeys_row)
        layout.addWidget(self.hotkey_warning_label)
        layout.addWidget(translation_engine_label)
        layout.addWidget(self.translation_engine_combobox)
        layout.addStretch()

        self.theme_switch.clicked.connect(self._on_theme_switch_clicked)
        self.engine_combobox.currentIndexChanged.connect(self._on_engine_combobox_changed)
        self.translation_engine_combobox.currentIndexChanged.connect(self._on_translation_engine_combobox_changed)
        self.api_key_button.clicked.connect(self._on_api_key_button_clicked)
        self.min_word_confidence_slider.valueChanged.connect(self._on_min_word_confidence_changed)
        self.text_similarity_threshold_slider.valueChanged.connect(self._on_text_similarity_threshold_changed)
        self.pixel_change_sensitivity_slider.valueChanged.connect(self._on_pixel_change_sensitivity_changed)
        self.live_claude_switch.clicked.connect(self._on_live_claude_switch_clicked)
        self.claude_cooldown_slider.valueChanged.connect(self._on_claude_cooldown_changed)
        self.claude_budget_input.editingFinished.connect(self._on_claude_budget_changed)
        self.hotkey_toggle_edit.editingFinished.connect(self._on_hotkey_toggle_edit_finished)
        self.hotkey_close_edit.editingFinished.connect(self._on_hotkey_close_edit_finished)

    def _on_min_word_confidence_changed(self, value: int) -> None:
        """Actualiza la etiqueta con el valor numérico y emite `min_word_confidence_changed`."""
        self.min_word_confidence_value_label.setText(str(value))
        self.min_word_confidence_changed.emit(value)

    def _on_text_similarity_threshold_changed(self, value: int) -> None:
        """Actualiza la etiqueta con el valor numérico y emite `text_similarity_threshold_changed`."""
        self.text_similarity_threshold_value_label.setText(str(value))
        self.text_similarity_threshold_changed.emit(value)

    def _on_pixel_change_sensitivity_changed(self, value: int) -> None:
        """Actualiza la etiqueta con el valor numérico y emite `pixel_change_sensitivity_changed`."""
        self.pixel_change_sensitivity_value_label.setText(str(value))
        self.pixel_change_sensitivity_changed.emit(value)

    def _on_live_claude_switch_clicked(self) -> None:
        """Emite `live_claude_toggled` con el nuevo estado del interruptor."""
        self.live_claude_toggled.emit(self.live_claude_switch.isChecked())

    def _on_claude_cooldown_changed(self, value: int) -> None:
        """Actualiza la etiqueta con el valor numérico y emite `claude_cooldown_changed`."""
        self.claude_cooldown_value_label.setText(str(value))
        self.claude_cooldown_changed.emit(value)

    def _on_claude_budget_changed(self) -> None:
        """Emite `claude_budget_changed` con el monto ingresado, si es un número válido."""
        text = self.claude_budget_input.text().replace(",", ".")
        try:
            value = float(text)
        except ValueError:
            return
        self.claude_budget_changed.emit(value)

    def _on_hotkey_toggle_edit_finished(self) -> None:
        """Emite `hotkey_toggle_changed` con la combinación ingresada."""
        self.hotkey_toggle_changed.emit(self.hotkey_toggle_edit.keySequence().toString())

    def _on_hotkey_close_edit_finished(self) -> None:
        """Emite `hotkey_close_changed` con la combinación ingresada."""
        self.hotkey_close_changed.emit(self.hotkey_close_edit.keySequence().toString())

    def set_hotkey_toggle_silent(self, sequence_text: str) -> None:
        """Sincroniza el campo de atajo de pausar/reanudar sin emitir `hotkey_toggle_changed`
        (usado por el controller para revertir tras una validación o un registro fallidos).
        """
        self.hotkey_toggle_edit.blockSignals(True)
        self.hotkey_toggle_edit.setKeySequence(QKeySequence(sequence_text))
        self.hotkey_toggle_edit.blockSignals(False)

    def set_hotkey_close_silent(self, sequence_text: str) -> None:
        """Sincroniza el campo de atajo de cerrar overlay sin emitir `hotkey_close_changed`
        (usado por el controller para revertir tras una validación o un registro fallidos).
        """
        self.hotkey_close_edit.blockSignals(True)
        self.hotkey_close_edit.setKeySequence(QKeySequence(sequence_text))
        self.hotkey_close_edit.blockSignals(False)

    def set_hotkey_warning(self, message: str) -> None:
        """Muestra `message` bajo los campos de atajos; una cadena vacía lo oculta."""
        self.hotkey_warning_label.setText(message)
        self.hotkey_warning_label.setVisible(bool(message))

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
        y emite `engine_changed` con el id del plugin de OCR seleccionado.
        """
        engine = self.engine_combobox.itemData(index)
        self._update_engine_visibility(engine)
        self.engine_changed.emit(engine)

    def _on_translation_engine_combobox_changed(self, index: int) -> None:
        """Emite `translation_engine_changed` con el id del plugin de traducción seleccionado."""
        self.translation_engine_changed.emit(self.translation_engine_combobox.itemData(index))

    def _update_engine_visibility(self, engine: str) -> None:
        """Muestra/oculta el aviso de costo, el campo de API key y los controles
        exclusivos de Claude en OCR en vivo (interruptor, cooldown, presupuesto)
        según el motor.
        """
        is_claude = engine == "claude"
        self.engine_cost_notice.setVisible(is_claude)
        self.api_key_container.setVisible(is_claude)
        self.live_claude_container.setVisible(is_claude)
        self.claude_cooldown_container.setVisible(is_claude)
        self.claude_budget_container.setVisible(is_claude)

    def set_engine_silent(self, engine: str) -> None:
        """Sincroniza el combobox de motor con el id `engine` sin emitir `engine_changed`
        (evita loops al llamarse desde el controller, ej. al revertir una selección).
        """
        index = self.engine_combobox.findData(engine)
        if index == -1:
            index = 0
        self.engine_combobox.blockSignals(True)
        self.engine_combobox.setCurrentIndex(index)
        self.engine_combobox.blockSignals(False)
        self._update_engine_visibility(engine)

    def set_translation_engine_silent(self, plugin_id: str) -> None:
        """Sincroniza el combobox de motor de traducción con el id `plugin_id`
        sin emitir `translation_engine_changed`.
        """
        index = self.translation_engine_combobox.findData(plugin_id)
        if index == -1:
            index = 0
        self.translation_engine_combobox.blockSignals(True)
        self.translation_engine_combobox.setCurrentIndex(index)
        self.translation_engine_combobox.blockSignals(False)

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
