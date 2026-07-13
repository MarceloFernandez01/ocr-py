"""Panel lateral (PySide6): menú de opciones de la aplicación, siempre visible."""

from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class SidebarView(QWidget):
    """Menú lateral con la opción "OCR de imágenes" y placeholders deshabilitados.

    No contiene lógica de negocio: emite `ocr_selected` al elegir la opción
    habilitada. El botón activo queda resaltado vía su estado `checked`.
    """

    ocr_selected = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets del menú lateral."""
        super().__init__(parent)

        self.ocr_button = QPushButton("OCR de imágenes")
        self.ocr_button.setObjectName("sidebarTile")
        self.ocr_button.setCheckable(True)
        self.ocr_button.setChecked(True)

        self.live_ocr_button = QPushButton("OCR en vivo")
        self.live_ocr_button.setObjectName("sidebarTile")
        self.live_ocr_button.setEnabled(False)

        layout = QVBoxLayout(self)
        layout.addWidget(self.ocr_button)
        layout.addWidget(self.live_ocr_button)
        layout.addStretch()

        self.ocr_button.clicked.connect(self._on_ocr_button_clicked)

    def _on_ocr_button_clicked(self) -> None:
        """Evita que el botón quede sin seleccionar y emite `ocr_selected`."""
        self.ocr_button.setChecked(True)
        self.ocr_selected.emit()
