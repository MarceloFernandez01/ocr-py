"""Skin visual estilo Metro (PySide6): solo presentación, sin lógica de negocio.

Expone `METRO_STYLESHEET`, la única fuente de QSS del look metro, para ser
aplicado una sola vez a nivel `QApplication`/`MainWindow`. No importa
`pytesseract` ni contiene reglas de negocio (respeta MVC).
"""

from __future__ import annotations

ACCENT = "rgb(42, 130, 218)"
FONT_FAMILY = "Segoe UI"

METRO_STYLESHEET = f"""
* {{
    font-family: "{FONT_FAMILY}";
}}

QWidget {{
    background-color: rgb(53, 53, 53);
    color: white;
    border: none;
}}

QMainWindow, QStackedWidget {{
    background-color: rgb(53, 53, 53);
}}

QPushButton {{
    background-color: rgb(68, 68, 68);
    color: white;
    border: none;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: normal;
}}

QPushButton:hover:enabled {{
    background-color: {ACCENT};
}}

QPushButton:pressed:enabled {{
    background-color: rgb(30, 100, 170);
}}

QPushButton:disabled {{
    background-color: rgb(53, 53, 53);
    color: rgb(130, 130, 130);
}}

QPushButton#sidebarTile {{
    text-align: left;
    padding: 12px 16px;
    font-size: 14px;
    font-weight: 300;
    background-color: rgb(53, 53, 53);
}}

QPushButton#sidebarTile:hover:enabled {{
    background-color: {ACCENT};
}}

QPushButton#sidebarTile:checked {{
    background-color: {ACCENT};
    color: white;
}}

QPushButton#sidebarTile:disabled {{
    background-color: rgb(53, 53, 53);
    color: rgb(130, 130, 130);
}}

QComboBox {{
    background-color: rgb(68, 68, 68);
    color: white;
    border: none;
    padding: 6px 10px;
    font-size: 13px;
}}

QComboBox:hover {{
    background-color: rgb(80, 80, 80);
}}

QComboBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox QAbstractItemView {{
    background-color: rgb(68, 68, 68);
    color: white;
    selection-background-color: {ACCENT};
    border: none;
}}

QLabel {{
    background-color: transparent;
    font-size: 13px;
}}

QTextEdit {{
    background-color: rgb(35, 35, 35);
    color: white;
    border: 1px solid rgb(80, 80, 80);
    font-size: 13px;
}}

QTextEdit:focus {{
    border: 1px solid {ACCENT};
}}
"""
