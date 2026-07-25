# Regenera dist/OCR-Py.exe a partir del código actual.
# Uso: ./build.ps1

$ErrorActionPreference = "Stop"

function Find-TesseractDir {
    if ($env:OCRPY_TESSERACT_DIR -and (Test-Path (Join-Path $env:OCRPY_TESSERACT_DIR "tesseract.exe"))) {
        return $env:OCRPY_TESSERACT_DIR
    }
    $cmd = Get-Command tesseract -ErrorAction SilentlyContinue
    if ($cmd) {
        return Split-Path $cmd.Source -Parent
    }
    $defaultDir = "C:\Program Files\Tesseract-OCR"
    if (Test-Path (Join-Path $defaultDir "tesseract.exe")) {
        return $defaultDir
    }
    return $null
}

Write-Host "Verificando PyInstaller..."
$pyinstaller = python -m PyInstaller --version 2>$null
if (-not $?) {
    Write-Error "PyInstaller no está instalado. Ejecuta: pip install -r requirements-dev.txt"
    exit 1
}
Write-Host "PyInstaller $pyinstaller"

Write-Host "Verificando Tesseract-OCR..."
$tesseractDir = Find-TesseractDir
if (-not $tesseractDir) {
    Write-Error "No se encontró Tesseract-OCR (PATH ni 'C:\Program Files\Tesseract-OCR'). Instálalo o definí OCRPY_TESSERACT_DIR."
    exit 1
}
Write-Host "Tesseract embebido desde: $tesseractDir"

Write-Host "Limpiando build/ y dist/ previos..."
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }
if (Test-Path "dist") { Remove-Item -Recurse -Force "dist" }

Write-Host "Compilando..."
python -m PyInstaller --noconfirm --clean OCR-Py.spec
if (-not $?) {
    Write-Error "El build falló."
    exit 1
}

$exePath = Join-Path (Get-Location) "dist\OCR-Py.exe"
if (Test-Path $exePath) {
    $sizeMb = "{0:N1}" -f ((Get-Item $exePath).Length / 1MB)
    Write-Host ""
    Write-Host "Build listo: $exePath ($sizeMb MB)"
    Write-Host "config.json se crea junto al .exe la primera vez que se usa la app."
} else {
    Write-Error "El build terminó pero no se encontró $exePath"
    exit 1
}
