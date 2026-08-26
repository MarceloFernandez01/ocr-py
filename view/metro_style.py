"""Skin visual estilo Metro (PySide6): solo presentación, sin lógica de negocio.

Expone `METRO_STYLESHEET_DARK` y `METRO_STYLESHEET_LIGHT`, las fuentes de QSS
del look metro para cada tema, junto con `get_stylesheet(theme)` para
seleccionar la variante correspondiente. Aplicado a nivel `QApplication`/
`MainWindow`. No importa `pytesseract` ni contiene reglas de negocio
(respeta MVC).
"""

from __future__ import annotations

from pathlib import Path

ACCENT = "rgb(42, 130, 218)"
FONT_FAMILY = "Segoe UI"

_ASSETS_DIR = Path(__file__).resolve().parent / "assets"
_CHEVRON_DOWN_DARK = (_ASSETS_DIR / "chevron_down_dark.png").as_posix()
_CHEVRON_DOWN_LIGHT = (_ASSETS_DIR / "chevron_down_light.png").as_posix()

METRO_STYLESHEET_DARK = f"""
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

QPushButton#translationButton:checked {{
    background-color: {ACCENT};
    color: white;
}}

QPushButton#resetZoomButton {{
    background-color: rgb(68, 68, 68);
    color: white;
    border: none;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: normal;
}}

QPushButton#settingsTile {{
    text-align: center;
    padding: 9px 0px;
    font-size: 20px;
    font-weight: 300;
    background-color: rgb(53, 53, 53);
}}

QPushButton#settingsTile:hover:enabled {{
    background-color: {ACCENT};
}}

QPushButton#settingsTile:checked {{
    background-color: {ACCENT};
    color: white;
}}

QComboBox {{
    background-color: rgb(68, 68, 68);
    color: white;
    border: none;
    padding: 6px 24px 6px 10px;
    font-size: 13px;
}}

QComboBox:hover {{
    background-color: rgb(80, 80, 80);
}}

QComboBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox:disabled {{
    background-color: rgb(60, 60, 60);
    color: rgb(150, 150, 150);
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 24px;
    border: none;
    background-color: transparent;
}}

QComboBox::down-arrow {{
    image: url({_CHEVRON_DOWN_DARK});
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: rgb(68, 68, 68);
    color: white;
    selection-background-color: {ACCENT};
    border: none;
    outline: none;
}}

QPushButton#themeSwitch {{
    background-color: transparent;
    border: none;
    padding: 0px;
}}

QPushButton#overlayCloseButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 2px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
}}

QPushButton#overlayCloseButton:hover {{
    background-color: rgb(200, 60, 60);
}}

QPushButton#overlayToggleButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 2px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
}}

QPushButton#overlayToggleButton:hover {{
    background-color: rgb(70, 150, 230);
}}

QPushButton#overlayToggleButton:disabled {{
    background-color: rgb(100, 100, 100);
}}

QPushButton#overlayTranslateButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 2px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
}}

QPushButton#overlayTranslateButton:hover:enabled {{
    background-color: rgb(70, 150, 230);
}}

QPushButton#overlayTranslateButton:checked {{
    background-color: rgb(30, 100, 170);
}}

QPushButton#overlayTranslateButton:disabled {{
    background-color: rgb(100, 100, 100);
}}

QLabel#liveStatusLabel {{
    color: {ACCENT};
    font-weight: bold;
}}

QLabel#hotkeyWarningLabel {{
    color: rgb(200, 60, 60);
    font-weight: bold;
}}

QFrame#sidebarSeparator {{
    background-color: rgb(80, 80, 80);
}}

QLabel#sidebarLogo {{
    background-color: transparent;
}}

QLabel {{
    background-color: transparent;
    font-size: 13px;
}}

QLabel#previewLabel {{
    background-color: rgb(35, 35, 35);
    border: 1px solid rgb(80, 80, 80);
}}

QLabel#zoomLabel {{
    background-color: rgba(20, 20, 20, 180);
    color: white;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: bold;
}}

QRubberBand {{
    background-color: rgba(42, 130, 218, 60);
    border: 2px solid {ACCENT};
}}

QLabel#fieldLabel {{
    font-size: 11px;
    color: rgb(180, 180, 180);
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

QScrollBar:vertical {{
    background-color: rgb(35, 35, 35);
    width: 12px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: rgb(80, 80, 80);
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: rgb(110, 110, 110);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
    border: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: rgb(35, 35, 35);
    height: 12px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background-color: rgb(80, 80, 80);
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: rgb(110, 110, 110);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
    border: none;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

QWidget#spendMeter {{
    background-color: rgb(45, 45, 45);
    border-top: 1px solid rgb(80, 80, 80);
}}

QProgressBar#spendMeterBar {{
    background-color: rgb(35, 35, 35);
    border: none;
    border-radius: 3px;
    max-height: 6px;
}}

QProgressBar#spendMeterBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}

QProgressBar#spendMeterBar[overBudget="true"]::chunk {{
    background-color: rgb(200, 60, 60);
}}

QLabel#spendMeterLabel {{
    font-size: 12px;
    color: rgb(200, 200, 200);
}}

QScrollArea#pluginsScrollArea {{
    background-color: transparent;
    border: none;
}}

QLabel#pluginsCorruptBanner {{
    background-color: rgba(200, 60, 60, 50);
    border: 1px solid rgb(200, 60, 60);
    border-radius: 4px;
    padding: 10px;
    color: rgb(255, 210, 210);
    font-weight: bold;
}}

QFrame#pluginRow {{
    background-color: rgb(45, 45, 45);
    border: 1px solid rgb(80, 80, 80);
    border-radius: 4px;
    padding: 10px;
}}

QLabel#pluginName {{
    font-size: 15px;
    font-weight: 600;
}}

QLabel#pluginEssentialBadge {{
    background-color: {ACCENT};
    color: white;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}

QLabel#pluginDescription {{
    font-size: 12px;
    color: rgb(190, 190, 190);
}}

QLabel#pluginCapabilities {{
    font-size: 11px;
    color: rgb(150, 150, 150);
}}

QLabel#pluginStatus {{
    font-size: 12px;
    font-weight: bold;
}}

QLabel#pluginStatus[state="active"] {{
    color: rgb(120, 200, 120);
}}

QLabel#pluginStatus[state="disabled"] {{
    color: rgb(180, 180, 180);
}}

QLabel#pluginStatus[state="error"] {{
    color: rgb(230, 100, 100);
}}

QPushButton#pluginSettingsToggle {{
    background-color: transparent;
    color: {ACCENT};
    text-align: left;
    padding: 4px 0px;
    font-size: 12px;
    font-weight: bold;
}}

QPushButton#pluginSettingsToggle:hover {{
    color: rgb(120, 180, 240);
}}

QWidget#pluginSettingsAccordion {{
    background-color: rgb(40, 40, 40);
    border: 1px solid rgb(70, 70, 70);
    border-radius: 4px;
    padding: 8px;
}}
"""

METRO_STYLESHEET_LIGHT = f"""
* {{
    font-family: "{FONT_FAMILY}";
}}

QWidget {{
    background-color: rgb(240, 240, 240);
    color: rgb(20, 20, 20);
    border: none;
}}

QMainWindow, QStackedWidget {{
    background-color: rgb(240, 240, 240);
}}

QPushButton {{
    background-color: rgb(225, 225, 225);
    color: rgb(20, 20, 20);
    border: none;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: normal;
}}

QPushButton:hover:enabled {{
    background-color: {ACCENT};
    color: white;
}}

QPushButton:pressed:enabled {{
    background-color: rgb(30, 100, 170);
    color: white;
}}

QPushButton:disabled {{
    background-color: rgb(240, 240, 240);
    color: rgb(160, 160, 160);
}}

QPushButton#sidebarTile {{
    text-align: left;
    padding: 12px 16px;
    font-size: 14px;
    font-weight: 300;
    background-color: rgb(240, 240, 240);
    color: rgb(20, 20, 20);
}}

QPushButton#sidebarTile:hover:enabled {{
    background-color: {ACCENT};
    color: white;
}}

QPushButton#sidebarTile:checked {{
    background-color: {ACCENT};
    color: white;
}}

QPushButton#sidebarTile:disabled {{
    background-color: rgb(240, 240, 240);
    color: rgb(160, 160, 160);
}}

QPushButton#translationButton:checked {{
    background-color: {ACCENT};
    color: white;
}}

QPushButton#resetZoomButton {{
    background-color: rgb(225, 225, 225);
    color: rgb(20, 20, 20);
    border: none;
    padding: 8px 16px;
    font-size: 13px;
    font-weight: normal;
}}

QPushButton#settingsTile {{
    text-align: center;
    padding: 9px 0px;
    font-size: 20px;
    font-weight: 300;
    background-color: rgb(240, 240, 240);
    color: rgb(20, 20, 20);
}}

QPushButton#settingsTile:hover:enabled {{
    background-color: {ACCENT};
    color: white;
}}

QPushButton#settingsTile:checked {{
    background-color: {ACCENT};
    color: white;
}}

QComboBox {{
    background-color: rgb(255, 255, 255);
    color: rgb(20, 20, 20);
    border: 1px solid rgb(200, 200, 200);
    padding: 6px 24px 6px 10px;
    font-size: 13px;
}}

QComboBox:hover {{
    background-color: rgb(230, 230, 230);
}}

QComboBox:focus {{
    border: 1px solid {ACCENT};
}}

QComboBox:disabled {{
    background-color: rgb(225, 225, 225);
    color: rgb(110, 110, 110);
}}

QComboBox::drop-down {{
    subcontrol-origin: padding;
    subcontrol-position: center right;
    width: 24px;
    border: none;
    background-color: transparent;
}}

QComboBox::down-arrow {{
    image: url({_CHEVRON_DOWN_LIGHT});
    width: 10px;
    height: 10px;
}}

QComboBox QAbstractItemView {{
    background-color: rgb(255, 255, 255);
    color: rgb(20, 20, 20);
    selection-background-color: {ACCENT};
    border: 1px solid rgb(200, 200, 200);
    outline: none;
}}

QPushButton#themeSwitch {{
    background-color: transparent;
    border: none;
    padding: 0px;
}}

QPushButton#overlayCloseButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 2px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
}}

QPushButton#overlayCloseButton:hover {{
    background-color: rgb(200, 60, 60);
}}

QPushButton#overlayToggleButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 2px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
}}

QPushButton#overlayToggleButton:hover {{
    background-color: rgb(70, 150, 230);
}}

QPushButton#overlayToggleButton:disabled {{
    background-color: rgb(100, 100, 100);
}}

QPushButton#overlayTranslateButton {{
    background-color: {ACCENT};
    color: white;
    border: none;
    border-radius: 2px;
    padding: 0px;
    font-size: 14px;
    font-weight: bold;
}}

QPushButton#overlayTranslateButton:hover:enabled {{
    background-color: rgb(70, 150, 230);
}}

QPushButton#overlayTranslateButton:checked {{
    background-color: rgb(30, 100, 170);
}}

QPushButton#overlayTranslateButton:disabled {{
    background-color: rgb(100, 100, 100);
}}

QLabel#liveStatusLabel {{
    color: {ACCENT};
    font-weight: bold;
}}

QLabel#hotkeyWarningLabel {{
    color: rgb(200, 60, 60);
    font-weight: bold;
}}

QFrame#sidebarSeparator {{
    background-color: rgb(200, 200, 200);
}}

QLabel#sidebarLogo {{
    background-color: transparent;
}}

QLabel {{
    background-color: transparent;
    font-size: 13px;
}}

QLabel#previewLabel {{
    background-color: rgb(255, 255, 255);
    border: 1px solid rgb(200, 200, 200);
}}

QLabel#zoomLabel {{
    background-color: rgba(20, 20, 20, 180);
    color: white;
    border-radius: 6px;
    padding: 4px 10px;
    font-size: 12px;
    font-weight: bold;
}}

QRubberBand {{
    background-color: rgba(42, 130, 218, 60);
    border: 2px solid {ACCENT};
}}

QLabel#fieldLabel {{
    font-size: 11px;
    color: rgb(100, 100, 100);
}}

QTextEdit {{
    background-color: rgb(255, 255, 255);
    color: rgb(20, 20, 20);
    border: 1px solid rgb(200, 200, 200);
    font-size: 13px;
}}

QTextEdit:focus {{
    border: 1px solid {ACCENT};
}}

QScrollBar:vertical {{
    background-color: rgb(255, 255, 255);
    width: 12px;
    margin: 0px;
}}

QScrollBar::handle:vertical {{
    background-color: rgb(200, 200, 200);
    min-height: 24px;
}}

QScrollBar::handle:vertical:hover {{
    background-color: rgb(160, 160, 160);
}}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
    border: none;
}}

QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
    background: none;
}}

QScrollBar:horizontal {{
    background-color: rgb(255, 255, 255);
    height: 12px;
    margin: 0px;
}}

QScrollBar::handle:horizontal {{
    background-color: rgb(200, 200, 200);
    min-width: 24px;
}}

QScrollBar::handle:horizontal:hover {{
    background-color: rgb(160, 160, 160);
}}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
    border: none;
}}

QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {{
    background: none;
}}

QWidget#spendMeter {{
    background-color: rgb(230, 230, 230);
    border-top: 1px solid rgb(200, 200, 200);
}}

QProgressBar#spendMeterBar {{
    background-color: rgb(255, 255, 255);
    border: 1px solid rgb(200, 200, 200);
    border-radius: 3px;
    max-height: 6px;
}}

QProgressBar#spendMeterBar::chunk {{
    background-color: {ACCENT};
    border-radius: 3px;
}}

QProgressBar#spendMeterBar[overBudget="true"]::chunk {{
    background-color: rgb(200, 60, 60);
}}

QLabel#spendMeterLabel {{
    font-size: 12px;
    color: rgb(80, 80, 80);
}}

QScrollArea#pluginsScrollArea {{
    background-color: transparent;
    border: none;
}}

QLabel#pluginsCorruptBanner {{
    background-color: rgba(200, 60, 60, 30);
    border: 1px solid rgb(200, 60, 60);
    border-radius: 4px;
    padding: 10px;
    color: rgb(150, 20, 20);
    font-weight: bold;
}}

QFrame#pluginRow {{
    background-color: rgb(255, 255, 255);
    border: 1px solid rgb(200, 200, 200);
    border-radius: 4px;
    padding: 10px;
}}

QLabel#pluginName {{
    font-size: 15px;
    font-weight: 600;
    color: rgb(20, 20, 20);
}}

QLabel#pluginEssentialBadge {{
    background-color: {ACCENT};
    color: white;
    border-radius: 8px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: bold;
}}

QLabel#pluginDescription {{
    font-size: 12px;
    color: rgb(90, 90, 90);
}}

QLabel#pluginCapabilities {{
    font-size: 11px;
    color: rgb(120, 120, 120);
}}

QLabel#pluginStatus {{
    font-size: 12px;
    font-weight: bold;
}}

QLabel#pluginStatus[state="active"] {{
    color: rgb(30, 140, 30);
}}

QLabel#pluginStatus[state="disabled"] {{
    color: rgb(110, 110, 110);
}}

QLabel#pluginStatus[state="error"] {{
    color: rgb(190, 40, 40);
}}

QPushButton#pluginSettingsToggle {{
    background-color: transparent;
    color: {ACCENT};
    text-align: left;
    padding: 4px 0px;
    font-size: 12px;
    font-weight: bold;
}}

QPushButton#pluginSettingsToggle:hover {{
    color: rgb(20, 90, 160);
}}

QWidget#pluginSettingsAccordion {{
    background-color: rgb(248, 248, 248);
    border: 1px solid rgb(210, 210, 210);
    border-radius: 4px;
    padding: 8px;
}}
"""


def get_stylesheet(theme: str) -> str:
    """Devuelve el QSS correspondiente al tema pedido.

    Args:
        theme: "dark" o "light".

    Returns:
        `METRO_STYLESHEET_DARK` o `METRO_STYLESHEET_LIGHT` según `theme`.
    """
    return METRO_STYLESHEET_LIGHT if theme == "light" else METRO_STYLESHEET_DARK
