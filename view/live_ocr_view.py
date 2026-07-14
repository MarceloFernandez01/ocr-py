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
    QVBoxLayout,
    QWidget,
)

LANGUAGE_OPTIONS = ["Español", "Inglés", "Ambos"]
TRANSLATION_LANGUAGE_OPTIONS = ["Español", "Inglés"]


class LiveOcrView(QWidget):
    """Vista de contenido de OCR en vivo: selector de idioma, botón "Activar
    selección", miniatura de la última captura y resultado de texto (solo
    lectura, se actualiza sola). No contiene lógica de negocio ni de captura
    de pantalla: solo layout y setters/getters simples.
    """

    activate_selection_clicked = Signal()
    toggle_transcription_clicked = Signal()
    translate_toggled = Signal()

    def __init__(self, parent: QWidget | None = None) -> None:
        """Crea los widgets de la pantalla de OCR en vivo."""
        super().__init__(parent)

        self.language_label = QLabel("Idioma")
        self.language_label.setObjectName("fieldLabel")
        self.language_combobox = QComboBox()
        self.language_combobox.addItems(LANGUAGE_OPTIONS)
        self.language_combobox.setCurrentText("Ambos")
        self.activate_button = QPushButton("Activar selección")
        self.activate_button.clicked.connect(self.activate_selection_clicked)
        self.transcription_button = QPushButton("Iniciar transcripción")
        self.transcription_button.setEnabled(False)
        self.transcription_button.clicked.connect(self.toggle_transcription_clicked)

        language_layout = QVBoxLayout()
        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.language_combobox)

        activate_spacer = QLabel("")
        activate_spacer.setObjectName("fieldLabel")
        activate_layout = QVBoxLayout()
        activate_layout.addWidget(activate_spacer)
        activate_layout.addWidget(self.activate_button)

        transcription_spacer = QLabel("")
        transcription_spacer.setObjectName("fieldLabel")
        transcription_layout = QVBoxLayout()
        transcription_layout.addWidget(transcription_spacer)
        transcription_layout.addWidget(self.transcription_button)

        toolbar = QHBoxLayout()
        toolbar.addLayout(language_layout)
        toolbar.addLayout(activate_layout)
        toolbar.addLayout(transcription_layout)
        toolbar.addStretch()

        self.source_language_label = QLabel("Traducir desde")
        self.source_language_label.setObjectName("fieldLabel")
        self.source_language_combobox = QComboBox()
        self.source_language_combobox.addItems(TRANSLATION_LANGUAGE_OPTIONS)
        source_language_layout = QVBoxLayout()
        source_language_layout.addWidget(self.source_language_label)
        source_language_layout.addWidget(self.source_language_combobox)

        self.target_language_label = QLabel("Traducir a")
        self.target_language_label.setObjectName("fieldLabel")
        self.target_language_combobox = QComboBox()
        self.target_language_combobox.addItems(TRANSLATION_LANGUAGE_OPTIONS)
        self.target_language_combobox.setCurrentText("Inglés")
        target_language_layout = QVBoxLayout()
        target_language_layout.addWidget(self.target_language_label)
        target_language_layout.addWidget(self.target_language_combobox)

        self.translation_button = QPushButton("Activar traducción")
        self.translation_button.setCheckable(True)
        self.translation_button.clicked.connect(self.translate_toggled)

        translation_spacer = QLabel("")
        translation_spacer.setObjectName("fieldLabel")
        translation_layout = QVBoxLayout()
        translation_layout.addWidget(translation_spacer)
        translation_layout.addWidget(self.translation_button)

        translation_toolbar = QHBoxLayout()
        translation_toolbar.addLayout(source_language_layout)
        translation_toolbar.addLayout(target_language_layout)
        translation_toolbar.addLayout(translation_layout)
        translation_toolbar.addStretch()

        self.preview_label = QLabel("Sin captura todavía")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setAlignment(Qt.AlignCenter)
        self.preview_label.setMinimumSize(1, 1)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)

        self.translation_label = QLabel("Traducción")
        self.translation_label.setObjectName("fieldLabel")

        self.translated_text_edit = QTextEdit()
        self.translated_text_edit.setReadOnly(True)

        result_layout = QVBoxLayout()
        result_layout.addWidget(self.result_text)
        result_layout.addWidget(self.translation_label)
        result_layout.addWidget(self.translated_text_edit)

        layout = QGridLayout(self)
        layout.addLayout(toolbar, 0, 0)
        layout.addLayout(translation_toolbar, 0, 1)
        layout.addWidget(self.preview_label, 1, 0)
        layout.addLayout(result_layout, 1, 1)
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

    def enable_transcription_button(self) -> None:
        """Habilita el botón de toggle de transcripción."""
        self.transcription_button.setEnabled(True)

    def disable_transcription_button(self) -> None:
        """Deshabilita el botón de toggle de transcripción."""
        self.transcription_button.setEnabled(False)

    def set_transcription_button_running(self, running: bool) -> None:
        """Actualiza el label del botón de toggle según si el polling corre."""
        self.transcription_button.setText(
            "Pausar transcripción" if running else "Iniciar transcripción"
        )

    def get_source_language(self) -> str:
        """Devuelve la opción de idioma origen de traducción seleccionada actualmente."""
        return self.source_language_combobox.currentText()

    def get_target_language(self) -> str:
        """Devuelve la opción de idioma destino de traducción seleccionada actualmente."""
        return self.target_language_combobox.currentText()

    def set_translation_button_active(self, active: bool) -> None:
        """Actualiza el estado marcado y el label del botón de traducción."""
        self.translation_button.setChecked(active)
        self.translation_button.setText(
            "Desactivar traducción" if active else "Activar traducción"
        )

    def set_translated_text(self, text: str) -> None:
        """Reemplaza el contenido del área de traducción con `text`."""
        self.translated_text_edit.setPlainText(text)

    def clear_translated_text(self) -> None:
        """Vacía el área de traducción."""
        self.translated_text_edit.clear()
