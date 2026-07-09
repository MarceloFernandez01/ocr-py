"""Punto de entrada de la aplicación de escritorio OCR."""

import tkinter as tk

from view.main_view import MainView


def main() -> None:
    """Crea y ejecuta la ventana principal de la aplicación."""
    root = tk.Tk()
    root.title("OCR")
    MainView(root)
    root.mainloop()


if __name__ == "__main__":
    main()
