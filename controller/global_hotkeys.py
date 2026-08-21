"""Registro de atajos globales de Windows para OCR en vivo, vía `RegisterHotKey`
(API de `user32.dll`, accedida con `ctypes`) y un filtro de eventos nativos de Qt
para capturar el mensaje `WM_HOTKEY`. Sin dependencia externa nueva.
"""

from __future__ import annotations

import ctypes
import sys

from PySide6.QtCore import QAbstractNativeEventFilter, QObject, Signal

from model.hotkey_model import parse_virtual_key

HOTKEY_TOGGLE_ID = 1
HOTKEY_CLOSE_ID = 2

WM_HOTKEY = 0x0312
# Offset usado para "probar" una combinación nueva bajo un id temporal antes de
# tocar el registro vigente, de forma que si Windows la rechaza la combinación
# anterior sigue activa (ver GlobalHotkeyManager.register).
_PROBE_ID_OFFSET = 1000


class GlobalHotkeyManager(QObject, QAbstractNativeEventFilter):
    """Envuelve `RegisterHotKey`/`UnregisterHotKey` de `user32.dll` e instala un
    `QAbstractNativeEventFilter` sobre la aplicación activa para capturar `WM_HOTKEY`
    y emitir `triggered(hotkey_id)`. En un sistema operativo distinto de Windows,
    `register()` devuelve `False` siempre sin intentar cargar `ctypes.windll`
    (que no existe fuera de Windows); la aplicación sigue funcionando con los
    botones de la GUI.
    """

    triggered = Signal(int)

    def __init__(self, parent: QObject | None = None) -> None:
        """Instala el filtro de eventos nativos sobre `QApplication`, solo en Windows."""
        QObject.__init__(self, parent)
        QAbstractNativeEventFilter.__init__(self)
        self._is_windows = sys.platform == "win32"
        self._registered_sequences: dict[int, str] = {}

        if self._is_windows:
            from PySide6.QtWidgets import QApplication

            QApplication.instance().installNativeEventFilter(self)

    def register(self, hotkey_id: int, sequence_text: str) -> bool:
        """Registra `sequence_text` bajo `hotkey_id`.

        Antes de tocar el registro vigente de `hotkey_id`, prueba `sequence_text`
        bajo un id temporal: si Windows la rechaza (ej. otra aplicación ya la
        tiene tomada), devuelve `False` sin alterar la combinación anterior.
        Si `sequence_text` ya es la combinación vigente de `hotkey_id`, no hace
        nada y devuelve `True`.
        """
        if not self._is_windows:
            return False

        try:
            modifiers, virtual_key = parse_virtual_key(sequence_text)
        except ValueError:
            return False

        if self._registered_sequences.get(hotkey_id) == sequence_text:
            return True

        user32 = ctypes.windll.user32
        probe_id = hotkey_id + _PROBE_ID_OFFSET
        if not user32.RegisterHotKey(None, probe_id, modifiers, virtual_key):
            return False
        user32.UnregisterHotKey(None, probe_id)

        if hotkey_id in self._registered_sequences:
            user32.UnregisterHotKey(None, hotkey_id)

        success = bool(user32.RegisterHotKey(None, hotkey_id, modifiers, virtual_key))
        if success:
            self._registered_sequences[hotkey_id] = sequence_text
        return success

    def unregister(self, hotkey_id: int) -> None:
        """Libera la combinación registrada bajo `hotkey_id`, si existía."""
        if not self._is_windows or hotkey_id not in self._registered_sequences:
            return
        ctypes.windll.user32.UnregisterHotKey(None, hotkey_id)
        del self._registered_sequences[hotkey_id]

    def nativeEventFilter(self, event_type, message):
        """Intercepta `WM_HOTKEY` en el bucle de eventos nativo y emite `triggered`."""
        if event_type in (b"windows_generic_MSG", "windows_generic_MSG"):
            from ctypes import wintypes

            msg = wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY:
                self.triggered.emit(msg.wParam)
        return False, 0
