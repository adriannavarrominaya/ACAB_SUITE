
$py = "C:\venv\acab-venv\Scripts\python"
$roots = "C:\trabajo\Jose\git\ACAB_SUITE\ACAB_fort_file_analyzer",
         "C:\trabajo\Jose\git\ACAB_SUITE\ACAB_inp_file_configurator",
         "C:\trabajo\Jose\git\ACAB_SUITE\COLLAPS_inp_file_configurator"
# Scripts que exigen argumentos (fichero de referencia) para no confundir
# "sin argumentos" (código 2, imprime __doc__) con un fallo real.
$extraArgs = @{ "test_parser_robustness.py" = @("examples\Inp5\exp1.inp.5") }
$gtotal = 0; $fallos = 0
foreach ($r in $roots) {
  Push-Location $r
  Write-Host "== $(Split-Path $r -Leaf) ==" -ForegroundColor Cyan
  foreach ($f in Get-ChildItem tools\test_*.py -ErrorAction SilentlyContinue) {
    $args = @("tools\$($f.Name)")
    if ($extraArgs.ContainsKey($f.Name)) { $args += $extraArgs[$f.Name] }
    $out = & $py @args 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { $fallos++; Write-Host "[FALLO] $($f.Name)" -ForegroundColor Red }
    if ($out -match "(\d+)\s+pasados") { $n=[int]$Matches[1]; $gtotal+=$n; "{0,-38}{1,5}" -f $f.Name, $n }
  }
  foreach ($f in Get-ChildItem tools\test_*.js -ErrorAction SilentlyContinue) {
    $out = node "tools\$($f.Name)" 2>&1 | Out-String
    if ($LASTEXITCODE -ne 0) { $fallos++; Write-Host "[FALLO] $($f.Name)" -ForegroundColor Red }
    if ($out -match "(\d+)\s+(pasados|passed|passing)") { $n=[int]$Matches[1]; $gtotal+=$n; "{0,-38}{1,5}" -f $f.Name, $n }
  }
  Pop-Location
}
Write-Host "TOTAL: $gtotal tests pasados; scripts con fallo: $fallos"