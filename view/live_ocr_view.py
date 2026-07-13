"""Pantalla de OCR en vivo (PySide6): captura y transcribe un segmento de pantalla."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QWidget,
)

LANGUAGE_OPTIONS = ["Español", "Inglés", "Ambos"]


class LiveOcrView(QWidget):
    """Vista de contenido de OCR en vivo: selector de idioma, botón "Activar
    selección", miniatura de la última captura y resultado de texto (solo
    lectura, se actualiza sola). No contiene lógica de negocio ni de captura
    de pantalla: solo layout y setters/getters simples.
    """

    activate_selection_clicked = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets de la pantalla de OCR en vivo."""
        super().__init__(parent)

        self.language_combobox = QComboBox()
        self.language_combobox.addItems(LANGUAGE_OPTIONS)
        self.language_combobox.setCurrentText("Ambos")
        self.activate_button = QPushButton("Activar selección")
        self.activate_button.clicked.connect(self.activate_selection_clicked)

        toolbar = QHBoxLayout()
        toolbar.addWidget(self.language_combobox)
        toolbar.addWidget(self.activate_button)
        toolbar.addStretch()

        self.preview_label = QLabel("Sin captura todavía")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(1, 1)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)

        layout = QGridLayout(self)
        layout.addLayout(toolbar, 0, 0, 1, 2)
        layout.addWidget(self.preview_label, 1, 0)
        layout.addWidget(self.result_text, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

    def set_preview_image(self, pixmap: QPixmap) -> None:
        """Muestra la imagen recibida en el área de miniatura."""
        self.preview_label.setPixmap(pixmap)
        self.preview_label.setText("")

    def set_result_text(self, text: str) -> None:
        """Reemplaza el contenido del bloque de resultado con `text`."""
        self.result_text.setPlainText(text)

    def get_selected_language(self) -> str:
        """Devuelve la opción de idioma seleccionada actualmente."""
        return self.language_combobox.currentText()

    def enable_activate_button(self) -> None:
        """Habilita el botón "Activar selección"."""
        self.activate_button.setEnabled(True)

    def disable_activate_button(self) -> None:
        """Deshabilita el botón "Activar selección"."""
        self.activate_button.setEnabled(False)
