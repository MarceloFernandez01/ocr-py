"""Pantalla de OCR de imágenes (PySide6): reemplaza a la MainView de Tkinter."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

LANGUAGE_OPTIONS = ["Español", "Inglés", "Ambos"]


class OcrView(QWidget):
    """Construye y expone los widgets de la pantalla de OCR.

    No contiene lógica de negocio: solo layout y setters/getters simples,
    con el mismo contrato que exponía `MainView` (Tkinter), más el botón
    "Volver". El Controller conecta los eventos con el Model.
    """

    back_requested = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets de la pantalla de OCR."""
        super().__init__(parent)

        toolbar = QHBoxLayout()
        self.back_button = QPushButton("Volver")
        self.open_button = QPushButton("Abrir imagen")
        self.language_combobox = QComboBox()
        self.language_combobox.addItems(LANGUAGE_OPTIONS)
        self.language_combobox.setCurrentText("Ambos")
        self.transcribe_button = QPushButton("Transcribir")
        self.transcribe_button.setEnabled(False)

        toolbar.addWidget(self.back_button)
        toolbar.addWidget(self.open_button)
        toolbar.addWidget(self.language_combobox)
        toolbar.addWidget(self.transcribe_button)
        toolbar.addStretch()

        content = QHBoxLayout()

        self.preview_label = QLabel("Sin imagen cargada")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setFrameShape(QFrame.Panel)
        self.preview_label.setFrameShadow(QFrame.Sunken)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)

        content.addWidget(self.preview_label, 1)
        content.addWidget(self.result_text, 1)

        layout = QVBoxLayout(self)
        layout.addLayout(toolbar)
        layout.addLayout(content)

        self.back_button.clicked.connect(self.back_requested.emit)

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
