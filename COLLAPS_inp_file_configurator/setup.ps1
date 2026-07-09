# setup.ps1 - Crea el entorno virtual e instala las dependencias de COLLAPS-Configurator
# Uso:  .\setup.ps1 [-VenvPath <ruta>]
# Por defecto el entorno se crea en .\venv
#
# El bloque de detección/instalación de Python y su companion
# install_python.ps1 son comunes a la suite — mantener sincronizados con las
# copias en ACAB_inp_file_configurator/, ACAB_fort_file_analyzer/ y
# acab_suite/ (el resto del script puede diferir entre apps).

param(
    [string]$VenvPath = ".\venv"
)

$ErrorActionPreference = "Stop"
$ProjectDir = $PSScriptRoot

Write-Host ""
Write-Host "=== COLLAPS-Configurator - Configuración del entorno (Windows) ===" -ForegroundColor Cyan
Write-Host "  Directorio del proyecto : $ProjectDir"
Write-Host "  Entorno virtual         : $VenvPath"
Write-Host ""

# -- 1. Verificar Python (instalar automáticamente si falta) ----------------
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "[1/3] Python no encontrado; lanzando install_python.ps1..." -ForegroundColor Yellow
    & "$PSScriptRoot\install_python.ps1"
    if ($LASTEXITCODE -ne 0) {
        Write-Error "Python no está disponible. Instálalo manualmente desde https://www.python.org (marca 'Add python.exe to PATH'), cierra y reabre PowerShell, y vuelve a ejecutar este script."
        exit 1
    }
    $python = Get-Command python -ErrorAction SilentlyContinue
    if (-not $python) {
        Write-Error "Python se instaló pero no aparece en el PATH de esta sesión. Cierra y reabre PowerShell y vuelve a ejecutar este script."
        exit 1
    }
}
$pyVersion = & python --version 2>&1
Write-Host "[1/3] Python detectado: $pyVersion" -ForegroundColor Green

# -- 2. Crear entorno virtual ------------------------------------------------
if (Test-Path "$VenvPath\Scripts\python.exe") {
    Write-Host "[2/3] El entorno virtual ya existe en '$VenvPath', se omite la creación." -ForegroundColor Yellow
} else {
    Write-Host "[2/3] Creando entorno virtual en '$VenvPath'..." -ForegroundColor Green
    python -m venv $VenvPath
}

# -- 3. Instalar dependencias ------------------------------------------------
Write-Host "[3/3] Instalando dependencias desde requirements.txt..." -ForegroundColor Green
& "$VenvPath\Scripts\pip" install --upgrade pip --quiet
& "$VenvPath\Scripts\pip" install -r "$ProjectDir\requirements.txt"

# -- Resumen -----------------------------------------------------------------
Write-Host ""
Write-Host "=== Entorno listo. Para arrancar la aplicación: ===" -ForegroundColor Cyan
Write-Host "  & '$VenvPath\Scripts\python' '$ProjectDir\app.py'"
Write-Host ""
