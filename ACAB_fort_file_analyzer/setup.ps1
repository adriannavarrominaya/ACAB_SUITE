# setup.ps1 — Configura el entorno virtual e instala dependencias
# Uso:  .\setup.ps1
# Tras la instalación ejecuta:  python app.py
#
# El bloque de detección/instalación de Python y su companion
# install_python.ps1 son comunes a la suite — mantener sincronizados con las
# copias en ACAB_inp_file_configurator/, COLLAPS_inp_file_configurator/ y
# acab_suite/ (el resto del script puede diferir entre apps).

$ErrorActionPreference = "Stop"
$VenvDir = "venv"

Write-Host "===================================================" -ForegroundColor Cyan
Write-Host "  ACAB Fort File Analyzer - Instalacion" -ForegroundColor Cyan
Write-Host "===================================================" -ForegroundColor Cyan

# -- 0. Verificar Python (instalar automáticamente si falta) -----------------
$python = Get-Command python -ErrorAction SilentlyContinue
if (-not $python) {
    Write-Host "`n[0/3] Python no encontrado; lanzando install_python.ps1..." -ForegroundColor Yellow
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

# Create virtual environment if it doesn't exist
if (-not (Test-Path $VenvDir)) {
    Write-Host "`n[1/3] Creando entorno virtual en '$VenvDir'..." -ForegroundColor Yellow
    python -m venv $VenvDir
} else {
    Write-Host "`n[1/3] Entorno virtual '$VenvDir' ya existe." -ForegroundColor Green
}

# Activate
Write-Host "[2/3] Activando entorno virtual..." -ForegroundColor Yellow
& "$VenvDir\Scripts\Activate.ps1"

# Install dependencies
Write-Host "[3/3] Instalando dependencias desde requirements.txt..." -ForegroundColor Yellow
pip install --upgrade pip --quiet
pip install -r requirements.txt

Write-Host "`n===================================================" -ForegroundColor Green
Write-Host "  Instalacion completada." -ForegroundColor Green
Write-Host "  Para iniciar la aplicacion:" -ForegroundColor Green
Write-Host "    python app.py" -ForegroundColor White
Write-Host "  Abre en el navegador: http://127.0.0.1:5000" -ForegroundColor White
Write-Host "===================================================" -ForegroundColor Green
