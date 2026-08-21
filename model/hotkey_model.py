"""Traducción y validación de combinaciones de teclas para atajos globales de Windows.

No importa PySide6 ni `ctypes`: solo maneja texto en notación `QKeySequence`
(ej. `"Ctrl+Shift+P"`) y lo traduce a los códigos que espera `RegisterHotKey`
de la API de Windows, sin depender de Qt ni de la biblioteca `ctypes`.
"""

MODIFIER_TOKENS = {"Ctrl", "Alt", "Shift", "Meta"}

# Constantes de modificador de la API de Windows (winuser.h), usadas por
# RegisterHotKey vía ctypes en controller/global_hotkeys.py.
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008

_MODIFIER_TO_MOD = {
    "Ctrl": MOD_CONTROL,
    "Alt": MOD_ALT,
    "Shift": MOD_SHIFT,
    "Meta": MOD_WIN,
}

# Códigos de tecla virtual de Windows (winuser.h) para las teclas finales
# que puede producir un QKeySequenceEdit.
_LETTER_KEYS = {chr(c): 0x41 + (c - ord("A")) for c in range(ord("A"), ord("Z") + 1)}
_DIGIT_KEYS = {str(d): 0x30 + d for d in range(10)}
_FUNCTION_KEYS = {f"F{n}": 0x70 + (n - 1) for n in range(1, 13)}
_NAMED_KEYS = {
    "Space": 0x20,
    "Tab": 0x09,
    "Escape": 0x1B,
    "Esc": 0x1B,
    "Return": 0x0D,
    "Enter": 0x0D,
    "Backspace": 0x08,
    "Delete": 0x2E,
    "Del": 0x2E,
    "Insert": 0x2D,
    "Ins": 0x2D,
    "Home": 0x24,
    "End": 0x23,
    "PageUp": 0x21,
    "PageDown": 0x22,
    "Up": 0x26,
    "Down": 0x28,
    "Left": 0x25,
    "Right": 0x27,
}

VIRTUAL_KEY_MAP = {**_LETTER_KEYS, **_DIGIT_KEYS, **_FUNCTION_KEYS, **_NAMED_KEYS}


def has_modifier(sequence_text: str) -> bool:
    """Indica si `sequence_text` (ej. "Ctrl+Shift+P") incluye al menos un modificador."""
    parts = sequence_text.split("+")
    return any(part in MODIFIER_TOKENS for part in parts)


def parse_virtual_key(sequence_text: str) -> tuple[int, int]:
    """Traduce `sequence_text` a `(modifiers, virtual_key)` para `RegisterHotKey`.

    `modifiers` combina por OR las constantes `MOD_*` de los modificadores
    presentes. Lanza `ValueError` si `sequence_text` no tiene modificador o
    la tecla final no es reconocible.
    """
    parts = [part for part in sequence_text.split("+") if part]
    if not parts:
        raise ValueError(f"Combinación de teclas vacía: {sequence_text!r}")

    *modifier_parts, key_part = parts

    modifiers = 0
    for part in modifier_parts:
        if part not in _MODIFIER_TO_MOD:
            raise ValueError(f"Modificador no reconocido: {part!r}")
        modifiers |= _MODIFIER_TO_MOD[part]

    if not has_modifier(sequence_text):
        raise ValueError(f"La combinación no incluye ningún modificador: {sequence_text!r}")

    virtual_key = VIRTUAL_KEY_MAP.get(key_part)
    if virtual_key is None:
        raise ValueError(f"Tecla no reconocida: {key_part!r}")

    return modifiers, virtual_key
