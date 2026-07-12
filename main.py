"""Punto de entrada de la aplicación de escritorio OCR."""

import tkinter as tk

from controller.ocr_controller import OcrController
from view.main_view import MainView


def main() -> None:
    """Crea y ejecuta la ventana principal de la aplicación."""
    root = tk.Tk()
    root.title("OCR")
    root.geometry("900x600")
    root.minsize(600, 400)
    view = MainView(root)
    OcrController(view)
    root.mainloop()


if __name__ == "__main__":
    main()
