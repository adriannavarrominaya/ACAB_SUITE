
$py = "C:\venv\acab-venv\Scripts\python"
$roots = "C:\git\ACAB_SUITE\ACAB_fort_file_analyzer",
         "C:\git\ACAB_SUITE\ACAB_inp_file_configurator",
         "C:\git\ACAB_SUITE\COLLAPS_inp_file_configurator"

# Scripts que exigen argumentos (fichero de referencia) para no confundir
# "sin argumentos" (código 2, imprime __doc__) con un fallo real.
$extraArgs = @{ "test_parser_robustness.py" = @("examples\Inp5\exp1.inp.5") }

# Scripts obligatorios según el CLAUDE.md de cada repo ("## Tests") que no
# encajan en el patrón tools\test_*.py y el glob no recoge.
$extraPyScripts = @{
  "ACAB_inp_file_configurator" = @(
    @{ Name = "regression_roundtrip.py"
       Args = @("examples\Inp5\exp1.inp.5", "examples\Inp5\exp2.inp.5",
                "examples\Inp5\exp3.inp.5", "examples\Inp5\exp4.inp.5") }
  )
}

# Los scripts propios de la suite imprimen "N pasados"; los de
# inp_file_configurator/COLLAPS usan unittest ("Ran N tests") o, en JS, una
# línea "OK   <caso>" por aserción. Sin ninguno de esos patrones (pero exit 0)
# se marca "OK" sin número.
function Contar-Pasados([string]$out) {
  if ($out -match "(\d+)\s+(pasados|passed|passing)") { return [int]$Matches[1] }
  if ($out -match "Ran (\d+) tests?") { return [int]$Matches[1] }
  $okLines = ([regex]::Matches($out, "(?m)^OK\s")).Count
  if ($okLines -gt 0) { return $okLines }
  return $null
}

$gtotal = 0; $fallos = 0

function Ejecutar([string]$nombre, [string]$exe, [string[]]$cliArgs) {
  $out = & $exe @cliArgs 2>&1 | Out-String
  if ($LASTEXITCODE -ne 0) {
    $script:fallos++
    Write-Host "[FALLO] $nombre" -ForegroundColor Red
    return
  }
  $n = Contar-Pasados $out
  if ($n) { $script:gtotal += $n; "{0,-38}{1,5}" -f $nombre, $n }
  else { "{0,-38}{1,5}" -f $nombre, "OK" }
}

foreach ($r in $roots) {
  Push-Location $r
  $repo = Split-Path $r -Leaf
  Write-Host "== $repo ==" -ForegroundColor Cyan

  foreach ($f in Get-ChildItem tools\test_*.py -ErrorAction SilentlyContinue) {
    $cliArgs = @("tools\$($f.Name)")
    if ($extraArgs.ContainsKey($f.Name)) { $cliArgs += $extraArgs[$f.Name] }
    Ejecutar $f.Name $py $cliArgs
  }
  if ($extraPyScripts.ContainsKey($repo)) {
    foreach ($extra in $extraPyScripts[$repo]) {
      Ejecutar $extra.Name $py (@("tools\$($extra.Name)") + $extra.Args)
    }
  }
  foreach ($f in Get-ChildItem tools\test_*.js -ErrorAction SilentlyContinue) {
    Ejecutar $f.Name "node" @("tools\$($f.Name)")
  }

  Pop-Location
}
Write-Host "TOTAL: $gtotal tests pasados; scripts con fallo: $fallos"
