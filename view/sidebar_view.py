"""Panel lateral (PySide6): menú de opciones de la aplicación, siempre visible."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QPushButton, QVBoxLayout, QWidget


class SidebarView(QWidget):
    """Menú lateral con "OCR de imágenes", "OCR en vivo" y Configuración.

    No contiene lógica de negocio: emite `ocr_selected`/`live_ocr_selected`/
    `settings_selected` al elegir una opción. El botón activo queda resaltado
    vía su estado `checked`, de forma mutuamente excluyente con los demás.
    """

    ocr_selected = Signal()
    live_ocr_selected = Signal()
    settings_selected = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets del menú lateral."""
        super().__init__(parent)

        self.ocr_button = QPushButton("OCR de imágenes")
        self.ocr_button.setObjectName("sidebarTile")
        self.ocr_button.setCheckable(True)
        self.ocr_button.setChecked(True)

        self.live_ocr_button = QPushButton("OCR en vivo")
        self.live_ocr_button.setObjectName("sidebarTile")
        self.live_ocr_button.setCheckable(True)

        self.settings_button = QPushButton("⚙")
        self.settings_button.setObjectName("settingsTile")
        self.settings_button.setCheckable(True)
        self.settings_button.setFixedWidth(48)

        layout = QVBoxLayout(self)
        layout.addWidget(self.ocr_button)
        layout.addWidget(self.live_ocr_button)
        layout.addStretch()
        layout.addWidget(self.settings_button, alignment=Qt.AlignLeft)

        self._exclusive_buttons = (self.ocr_button, self.live_ocr_button, self.settings_button)

        self.ocr_button.clicked.connect(self._on_ocr_button_clicked)
        self.live_ocr_button.clicked.connect(self._on_live_ocr_button_clicked)
        self.settings_button.clicked.connect(self._on_settings_button_clicked)

    def _select_exclusive(self, selected: QPushButton) -> None:
        """Marca `selected` como activo y destilda los demás tiles excluyentes."""
        for button in self._exclusive_buttons:
            button.setChecked(button is selected)

    def _on_ocr_button_clicked(self) -> None:
        """Resalta "OCR de imágenes" y emite `ocr_selected`."""
        self._select_exclusive(self.ocr_button)
        self.ocr_selected.emit()

    def _on_live_ocr_button_clicked(self) -> None:
        """Resalta "OCR en vivo" y emite `live_ocr_selected`."""
        self._select_exclusive(self.live_ocr_button)
        self.live_ocr_selected.emit()

    def _on_settings_button_clicked(self) -> None:
        """Resalta el engranaje y emite `settings_selected`."""
        self._select_exclusive(self.settings_button)
        self.settings_selected.emit()
