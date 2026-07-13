"""Pantalla de Configuración (PySide6): opciones de tema y motor OCR."""

from __future__ import annotations

from PySide6.QtCore import Property, QEasingCurve, QPropertyAnimation, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QPainter
from PySide6.QtWidgets import (
    QComboBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

ENGINE_OPTIONS = ["Tesseract", "Claude Haiku (próximamente)"]

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
    claro/oscuro y placeholder deshabilitado del motor OCR. No contiene
    lógica de negocio ni persiste nada directamente; emite `theme_toggled`
    para que el controller decida qué hacer.
    """

    theme_toggled = Signal(str)  # "dark" | "light"

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets de la pantalla de Configuración."""
        super().__init__(parent)

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
        self.engine_combobox.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addWidget(theme_label)
        layout.addLayout(theme_row)
        layout.addWidget(engine_label)
        layout.addWidget(self.engine_combobox)
        layout.addStretch()

        self.theme_switch.clicked.connect(self._on_theme_switch_clicked)

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
