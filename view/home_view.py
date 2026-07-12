"""Pantalla de inicio (PySide6): menú de opciones de la aplicación."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class HomeView(QWidget):
    """Menú de inicio con la opción "OCR de imágenes" y placeholders deshabilitados.

    No contiene lógica de negocio: emite `ocr_selected` al elegir la opción
    habilitada. El Controller/`MainWindow` decide a qué pantalla navegar.
    """

    ocr_selected = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets del menú de inicio."""
        super().__init__(parent)

        self.ocr_button = QPushButton("OCR de imágenes")
        self.live_ocr_button = QPushButton("OCR en vivo")
        self.live_ocr_button.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addStretch()
        layout.addWidget(self.ocr_button)
        layout.addWidget(self.live_ocr_button)
        layout.addStretch()

        self.ocr_button.clicked.connect(self.ocr_selected.emit)
