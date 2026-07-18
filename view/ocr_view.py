"""Pantalla de OCR de imágenes (PySide6): reemplaza a la MainView de Tkinter."""

from __future__ import annotations

from PySide6.QtCore import Qt, QRect, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QRubberBand,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

LANGUAGE_OPTIONS = ["Español", "Inglés", "Ambos"]


class OcrView(QWidget):
    """Construye y expone los widgets de la pantalla de OCR.

    No contiene lógica de negocio: solo layout y setters/getters simples,
    con el mismo contrato que exponía `MainView` (Tkinter). El Controller
    conecta los eventos con el Model.
    """

    crop_toggled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets de la pantalla de OCR."""
        super().__init__(parent)

        self.open_button = QPushButton("Abrir imagen")
        self.crop_button = QPushButton("Quitar recorte")
        self.crop_button.setObjectName("cropButton")
        self.crop_button.setEnabled(False)
        self.reset_zoom_button = QPushButton("Restablecer zoom")
        self.reset_zoom_button.setObjectName("resetZoomButton")
        self.language_label = QLabel("Idioma")
        self.language_label.setObjectName("fieldLabel")
        self.language_combobox = QComboBox()
        self.language_combobox.addItems(LANGUAGE_OPTIONS)
        self.language_combobox.setCurrentText("Ambos")
        self.transcribe_button = QPushButton("Transcribir")
        self.transcribe_button.setEnabled(False)

        open_spacer = QLabel("")
        open_spacer.setObjectName("fieldLabel")
        open_layout = QVBoxLayout()
        open_layout.addWidget(open_spacer)
        open_layout.addWidget(self.open_button)

        crop_spacer = QLabel("")
        crop_spacer.setObjectName("fieldLabel")
        crop_layout = QVBoxLayout()
        crop_layout.addWidget(crop_spacer)
        crop_layout.addWidget(self.crop_button)

        reset_zoom_spacer = QLabel("")
        reset_zoom_spacer.setObjectName("fieldLabel")
        reset_zoom_layout = QVBoxLayout()
        reset_zoom_layout.addWidget(reset_zoom_spacer)
        reset_zoom_layout.addWidget(self.reset_zoom_button)

        left_toolbar = QHBoxLayout()
        left_toolbar.addLayout(open_layout)
        left_toolbar.addLayout(crop_layout)
        left_toolbar.addLayout(reset_zoom_layout)
        left_toolbar.addStretch()

        language_layout = QVBoxLayout()
        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.language_combobox)

        transcribe_spacer = QLabel("")
        transcribe_spacer.setObjectName("fieldLabel")
        transcribe_layout = QVBoxLayout()
        transcribe_layout.addWidget(transcribe_spacer)
        transcribe_layout.addWidget(self.transcribe_button)

        right_toolbar = QHBoxLayout()
        right_toolbar.addLayout(language_layout)
        right_toolbar.addLayout(transcribe_layout)
        right_toolbar.addStretch()

        self.preview_label = QLabel("Sin imagen cargada")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(1, 1)
        self.preview_label.setContextMenuPolicy(Qt.NoContextMenu)

        self.crop_rubber_band = QRubberBand(QRubberBand.Rectangle, self.preview_label)
        self.crop_rubber_band.hide()

        self.zoom_label = QLabel(self.preview_label)
        self.zoom_label.setObjectName("zoomLabel")
        self.zoom_label.hide()

        self.crop_button.clicked.connect(self.crop_toggled.emit)

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

    def update_crop_button(self, has_crop: bool) -> None:
        """Habilita o deshabilita el botón "Quitar recorte" según `has_crop`."""
        self.crop_button.setEnabled(has_crop)

    def show_crop_rect(self, rect: QRect) -> None:
        """Posiciona y muestra el rectángulo de recorte sobre `preview_label`."""
        self.crop_rubber_band.setGeometry(rect)
        self.crop_rubber_band.show()

    def hide_crop_rect(self) -> None:
        """Oculta el rectángulo de recorte."""
        self.crop_rubber_band.hide()

    def set_zoom_label(self, text: str) -> None:
        """Setea el texto del indicador de zoom flotante y lo muestra."""
        self.zoom_label.setText(text)
        self.zoom_label.adjustSize()
        self.position_zoom_label()
        self.zoom_label.show()

    def hide_zoom_label(self) -> None:
        """Oculta el indicador de zoom flotante."""
        self.zoom_label.hide()

    def position_zoom_label(self) -> None:
        """Reposiciona el indicador de zoom en la esquina inferior derecha de `preview_label`."""
        margin = 8
        x = self.preview_label.width() - self.zoom_label.width() - margin
        y = self.preview_label.height() - self.zoom_label.height() - margin
        self.zoom_label.move(max(0, x), max(0, y))
