# ======================================================================
# INOOS - Launcher Automatizado del Informe de Junta Directiva
# ======================================================================
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host "   INSTITUTO NACIONAL DE ONCOLOGÍA Y OPORTUNIDAD EN SALUD (INOOS)     " -ForegroundColor Cyan
Write-Host "      Plataforma Automatizada de Informes de Junta Directiva         " -ForegroundColor Cyan
Write-Host "======================================================================" -ForegroundColor Cyan
Write-Host ""

$realPython = "$env:LOCALAPPDATA\Programs\Python\Python313\python.exe"
if (Test-Path $realPython) {
    $pythonExe = $realPython
} elseif (Test-Path ".venv\Scripts\python.exe") {
    $pythonExe = ".venv\Scripts\python.exe"
} else {
    $pythonExe = "python"
}

Write-Host "[*] Motor Python detectado: $pythonExe" -ForegroundColor Green
Write-Host "[*] Iniciando servidor web en puerto libre (5050)..." -ForegroundColor Yellow
Write-Host "[*] Tu navegador se abrirá automáticamente en breve." -ForegroundColor Yellow
Write-Host ""

& $pythonExe app.py --port 5050 --open

