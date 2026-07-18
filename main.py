"""Punto de entrada de la aplicación de escritorio OCR."""

import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from controller.ocr_controller import OcrController
from view.main_window import MainWindow

ICON_PATH = Path(__file__).resolve().parent / "view" / "assets" / "icon.ico"

if sys.platform == "win32":
    import ctypes

    # Sin esto, al correr con `python main.py` Windows agrupa la ventana bajo
    # el ícono de python.exe en la barra de tareas en vez del ícono propio.
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("OcrPy.App")


def main() -> None:
    """Crea y ejecuta la ventana principal de la aplicación."""
    app = QApplication(sys.argv)
    app.setWindowIcon(QIcon(str(ICON_PATH)))
    window = MainWindow()
    controller = OcrController(window.ocr_view)  # referencia viva: sin esto Python lo recolecta y desconecta las señales
    window.show()
    window.raise_()
    window.activateWindow()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
