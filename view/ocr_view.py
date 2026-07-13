"""Pantalla de OCR de imágenes (PySide6): reemplaza a la MainView de Tkinter."""

from __future__ import annotations

from PySide6.QtCore import Qt
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


class OcrView(QWidget):
    """Construye y expone los widgets de la pantalla de OCR.

    No contiene lógica de negocio: solo layout y setters/getters simples,
    con el mismo contrato que exponía `MainView` (Tkinter). El Controller
    conecta los eventos con el Model.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets de la pantalla de OCR."""
        super().__init__(parent)

        self.open_button = QPushButton("Abrir imagen")
        self.language_combobox = QComboBox()
        self.language_combobox.addItems(LANGUAGE_OPTIONS)
        self.language_combobox.setCurrentText("Ambos")
        self.transcribe_button = QPushButton("Transcribir")
        self.transcribe_button.setEnabled(False)

        left_toolbar = QHBoxLayout()
        left_toolbar.addWidget(self.open_button)
        left_toolbar.addStretch()

        right_toolbar = QHBoxLayout()
        right_toolbar.addWidget(self.language_combobox)
        right_toolbar.addWidget(self.transcribe_button)
        right_toolbar.addStretch()

        self.preview_label = QLabel("Sin imagen cargada")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(1, 1)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)

        layout = QGridLayout(self)
        layout.addLayout(left_toolbar, 0, 0)
        layout.addLayout(right_toolbar, 0, 1)
        layout.addWidget(self.preview_label, 1, 0)
        layout.addWidget(self.result_text, 1, 1)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)

    def set_preview_image(self, pixmap: QPixmap) -> None:
        """Muestra la imagen recibida en el área de vista previa."""
        self.preview_label.setPixmap(pixmap)
        self.preview_label.setText("")

    def set_result_text(self, text: str) -> None:
        """Reemplaza el contenido del bloque de resultado con `text`."""
        self.result_text.setPlainText(text)

    def get_selected_language(self) -> str:
        """Devuelve la opción de idioma seleccionada actualmente."""
        return self.language_combobox.currentText()

    def enable_transcribe_button(self) -> None:
        """Habilita el botón "Transcribir"."""
        self.transcribe_button.setEnabled(True)

    def disable_transcribe_button(self) -> None:
        """Deshabilita el botón "Transcribir"."""
        self.transcribe_button.setEnabled(False)
