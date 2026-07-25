# -*- mode: python ; coding: utf-8 -*-
"""Spec de PyInstaller para OCR-Py.

Genera un único ejecutable Windows (onefile) con Tesseract-OCR embebido
(solo spa/eng, sin herramientas de entrenamiento ni el resto de idiomas)
para que la app no dependa de nada instalado en la máquina destino.

Uso: python -m PyInstaller --noconfirm --clean OCR-Py.spec
(o el wrapper build.ps1 en la raíz del repo).
"""

import os
import shutil
from pathlib import Path

from PyInstaller.utils.hooks import copy_metadata

# --- Localizar Tesseract-OCR en tiempo de build ---------------------------
# Prioridad: variable de entorno > PATH > ubicación default de instalación.


def _find_tesseract_dir() -> Path:
    env_dir = os.environ.get("OCRPY_TESSERACT_DIR")
    if env_dir and (Path(env_dir) / "tesseract.exe").exists():
        return Path(env_dir)

    which_path = shutil.which("tesseract")
    if which_path:
        return Path(which_path).resolve().parent

    default_dir = Path(r"C:\Program Files\Tesseract-OCR")
    if (default_dir / "tesseract.exe").exists():
        return default_dir

    raise SystemExit(
        "No se encontró Tesseract-OCR para embeber en el build. "
        "Instálalo, agrégalo al PATH, o definí la variable de entorno "
        "OCRPY_TESSERACT_DIR apuntando a su carpeta de instalación."
    )


_TESSERACT_DIR = _find_tesseract_dir()
_TESSDATA_LANGS = ["spa.traineddata", "eng.traineddata"]

tesseract_datas = [(str(_TESSERACT_DIR / "tesseract.exe"), "tesseract")]
tesseract_datas += [
    (str(dll), "tesseract") for dll in _TESSERACT_DIR.glob("*.dll")
]
tesseract_datas += [
    (str(_TESSERACT_DIR / "tessdata" / lang), "tesseract/tessdata")
    for lang in _TESSDATA_LANGS
]
for doc_name in ("LICENSE", "AUTHORS"):
    doc_path = _TESSERACT_DIR / "doc" / doc_name
    if doc_path.exists():
        tesseract_datas.append((str(doc_path), "tesseract"))

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('view/assets', 'view/assets'),
        ('logo', 'logo'),
        *tesseract_datas,
        *copy_metadata('keyring'),
    ],
    hiddenimports=[
        'keyring.backends.Windows',
        'win32ctypes.core',
        'win32ctypes.core.ctypes',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='OCR-Py',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['view/assets/icon.ico'],
)
