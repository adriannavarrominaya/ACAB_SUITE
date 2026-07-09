# setup.ps1 - Crea el venv COMPARTIDO de la suite ACAB (las 3 apps) e instala
# sus dependencias. Este es el único setup que hace falta ejecutar para lanzar
# la suite con suite_launcher.py.
#
# Uso:  .\setup.ps1 [-VenvPath <ruta>]
# Por defecto el entorno se crea en C:\venv\acab-venv (ruta documentada en el
# CLAUDE.md de cada app y usada por defecto en suite_config.json).
#
# Tras ejecutarlo: C:\venv\acab-venv\Scripts\python suite_launcher.py
#
# El bloque de detección/instalación de Python y su companion
# install_python.ps1 son comunes a la suite — mantener sincronizados con las
# copias en ACAB_inp_file_configurator/, ACAB_fort_file_analyzer/ y
# COLLAPS_inp_file_configurator/ (el resto del script puede diferir entre apps).

param(
    [string]$VenvPath = "C:\venv\acab-venv"
)

$ErrorActionPreference = "Stop"
$SuiteDir = $PSScriptRoot
$Apps = @(
    "$SuiteDir\..\ACAB_inp_file_configurator",
    "$SuiteDir\..\ACAB_fort_file_analyzer",
    "$SuiteDir\..\COLLAPS_inp_file_configurator"
)

Write-Host ""
Write-Host "=== Suite ACAB - Configuracion del entorno compartido (Windows) ===" -ForegroundColor Cyan
Write-Host "  Entorno virtual : $VenvPath"
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
    Write-Host "[2/3] El entorno virtual ya existe en '$VenvPath', se omite la creacion." -ForegroundColor Yellow
} else {
    Write-Host "[2/3] Creando entorno virtual en '$VenvPath'..." -ForegroundColor Green
    python -m venv $VenvPath
}

# -- 3. Instalar dependencias de las 3 apps ----------------------------------
Write-Host "[3/3] Instalando dependencias de las 3 apps..." -ForegroundColor Green
& "$VenvPath\Scripts\pip" install --upgrade pip --quiet
foreach ($app in $Apps) {
    $req = Join-Path $app "requirements.txt"
    if (Test-Path $req) {
        Write-Host "  -> $req" -ForegroundColor DarkGray
        & "$VenvPath\Scripts\pip" install -r $req
    } else {
        Write-Warning "No se encuentra $req, se omite."
    }
}

# -- Resumen -----------------------------------------------------------------
Write-Host ""
Write-Host "=== Entorno listo. Para arrancar la suite: ===" -ForegroundColor Cyan
Write-Host "  & '$VenvPath\Scripts\python' '$SuiteDir\suite_launcher.py'"
Write-Host ""
Write-Host "  Si suite_config.json no apunta a '$VenvPath\Scripts\python.exe' en la clave" -ForegroundColor DarkGray
Write-Host "  ""python"", corrigela para que el launcher use este venv por defecto." -ForegroundColor DarkGray
Write-Host ""
