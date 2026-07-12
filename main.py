"""Punto de entrada de la aplicación de escritorio OCR."""

import sys

from PySide6.QtWidgets import QApplication

from controller.ocr_controller import OcrController
from view.main_window import MainWindow


def main() -> None:
    """Crea y ejecuta la ventana principal de la aplicación."""
    app = QApplication(sys.argv)
    window = MainWindow()
    controller = OcrController(window.ocr_view)  # referencia viva: sin esto Python lo recolecta y desconecta las señales
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
