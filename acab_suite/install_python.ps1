# install_python.ps1 - Instala Python en Windows si no está disponible en el PATH.
# Común de la suite — mantener sincronizado con las copias en
# ACAB_inp_file_configurator/install_python.ps1, ACAB_fort_file_analyzer/install_python.ps1
# y COLLAPS_inp_file_configurator/install_python.ps1.
#
# Lo invoca setup.ps1 cuando "python" no se encuentra. Pide confirmación antes
# de instalar nada (modifica el sistema del usuario). Vías, en orden:
#   1. winget (viene preinstalado en Windows 10 2004+ / Windows 11) — instala
#      para el usuario actual, sin necesitar privilegios de administrador.
#   2. Instalador oficial de python.org, descargado y ejecutado en modo
#      silencioso (también solo para el usuario actual).
#   3. Si el usuario rechaza ambas, o ninguna funciona: instrucciones manuales.
#
# Código de salida: 0 si "python" queda disponible en esta sesión; 1 en
# cualquier otro caso (setup.ps1 debe abortar si recibe 1).

$ErrorActionPreference = "Stop"
$PythonVersion = "3.12.8"

function Test-PythonAvailable {
    $cmd = Get-Command python -ErrorAction SilentlyContinue
    if (-not $cmd) { return $false }
    # En Windows, "python" sin Python instalado a veces resuelve al stub de
    # Microsoft Store (abre la tienda y no falla como comando ausente), por
    # eso se comprueba que realmente devuelva versión con código de salida 0.
    try {
        & python --version *> $null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Update-SessionPath {
    # El proceso de PowerShell actual no refresca $env:Path solo tras una
    # instalación; hay que reconstruirlo desde el registro (Machine + User).
    $machine = [System.Environment]::GetEnvironmentVariable("Path", "Machine")
    $user = [System.Environment]::GetEnvironmentVariable("Path", "User")
    $env:Path = "$machine;$user"
}

function Show-ManualGuide {
    Write-Host @"

[install_python] Instalación manual de Python:
  1. Abre https://www.python.org/downloads/
  2. Descarga el instalador de Windows (64-bit) de la última versión 3.x.
  3. Ejecútalo y marca la casilla "Add python.exe to PATH" antes de instalar.
  4. Cierra y vuelve a abrir PowerShell (para que recoja el PATH nuevo).
  5. Ejecuta de nuevo .\setup.ps1

"@ -ForegroundColor Yellow
}

if (Test-PythonAvailable) {
    Write-Host "[install_python] Python ya disponible: $(python --version 2>&1)" -ForegroundColor Green
    exit 0
}

Write-Host "[install_python] Python no encontrado en el PATH." -ForegroundColor Yellow

$winget = Get-Command winget -ErrorAction SilentlyContinue
if ($winget) {
    $confirm = Read-Host "¿Instalar Python $PythonVersion con winget para el usuario actual? (S/N)"
    if ($confirm -match '^[SsYy]') {
        Write-Host "[install_python] Instalando con winget..." -ForegroundColor Cyan
        winget install --id Python.Python.3.12 -e --source winget --scope user `
            --accept-package-agreements --accept-source-agreements
        Update-SessionPath
        if (Test-PythonAvailable) {
            Write-Host "[install_python] Python instalado correctamente: $(python --version 2>&1)" -ForegroundColor Green
            exit 0
        }
        Write-Warning "[install_python] winget terminó pero 'python' no aparece en esta sesión."
        Write-Host "  Cierra y vuelve a abrir PowerShell y ejecuta de nuevo .\setup.ps1" -ForegroundColor Yellow
        exit 1
    }
} else {
    Write-Host "[install_python] winget no está disponible en este equipo." -ForegroundColor Yellow
}

$confirm = Read-Host "¿Descargar e instalar Python $PythonVersion desde python.org? (S/N)"
if ($confirm -notmatch '^[SsYy]') {
    Show-ManualGuide
    exit 1
}

$installerUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$installerPath = Join-Path $env:TEMP "python-$PythonVersion-amd64.exe"
try {
    Write-Host "[install_python] Descargando $installerUrl ..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri $installerUrl -OutFile $installerPath
    Write-Host "[install_python] Instalando (modo silencioso, solo para el usuario actual)..." -ForegroundColor Cyan
    Start-Process -FilePath $installerPath -ArgumentList "/quiet InstallAllUsers=0 PrependPath=1" -Wait
} catch {
    Write-Warning "[install_python] La descarga o instalación automática falló: $($_.Exception.Message)"
    Show-ManualGuide
    exit 1
} finally {
    Remove-Item $installerPath -ErrorAction SilentlyContinue
}

Update-SessionPath
if (Test-PythonAvailable) {
    Write-Host "[install_python] Python instalado correctamente: $(python --version 2>&1)" -ForegroundColor Green
    exit 0
} else {
    Write-Warning "[install_python] La instalación se ejecutó pero 'python' no aparece en el PATH de esta sesión."
    Write-Host "  Cierra y vuelve a abrir PowerShell y ejecuta de nuevo .\setup.ps1" -ForegroundColor Yellow
    exit 1
}
