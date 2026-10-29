@echo off
chcp 65001 > nul
title INOOS - Automatización Informe de Junta Directiva
echo ======================================================================
echo    INSTITUTO NACIONAL DE ONCOLOGÍA Y OPORTUNIDAD EN SALUD (INOOS)
echo       Plataforma Automatizada de Informes de Junta Directiva
echo ======================================================================
echo.

:: 1. Detectar ejecutable de Python disponible (Priorizar Python 3.13 instalado)
if exist "%LOCALAPPDATA%\Programs\Python\Python313\python.exe" (
    set "PYTHON_EXE=%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
) else if exist ".venv\Scripts\python.exe" (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
) else (
    set "PYTHON_EXE=python"
)

echo [*] Utilizando motor Python: %PYTHON_EXE%
echo [*] Iniciando servidor web en puerto libre (por defecto 5050)...
echo [*] Abriendo navegador automáticamente...
echo.

:: 2. Ejecutar la aplicación en puerto 5050 (con auto-fallback si está ocupado) y abrir navegador
"%PYTHON_EXE%" app.py --port 5050 --open

pause

