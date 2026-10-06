@echo off
cd /d "%~dp0AnalisePorPosicao-Central"
set "PYTHON=%~dp0LP_venv\Scripts\python.exe"
set "URL=http://127.0.0.1:8083/"
powershell -NoProfile -Command "try { $c = New-Object Net.Sockets.TcpClient; $c.Connect('127.0.0.1',8083); $c.Close(); exit 0 } catch { exit 1 }"
if errorlevel 1 (
  start "LP" /MIN "%PYTHON%" "%~dp0AnalisePorPosicao-Central\LP.py"
  timeout /t 8 /nobreak >nul
)
start "" "%URL%"
