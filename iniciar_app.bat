@echo off
setlocal

cd /d "%~dp0"

echo Iniciando TaleWeaver...
echo URL: http://127.0.0.1:3000
echo.

echo Encerrando sessoes anteriores do app na porta 3000...
powershell -NoProfile -ExecutionPolicy Bypass -Command "Get-NetTCPConnection -LocalPort 3000 -State Listen -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object { Stop-Process -Id $_ -Force -ErrorAction SilentlyContinue }"
timeout /t 1 /nobreak >nul
echo.

"C:\Python314\python.exe" -B app.py

echo.
echo O servidor foi encerrado.
pause
