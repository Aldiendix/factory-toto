@echo off
cd /d "%~dp0"
echo Stopping local app on port 8501...
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 8501 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue; Write-Output ('Stopped PID ' + $_.OwningProcess) }"
if errorlevel 1 (
  echo No listener found on port 8501.
) else (
  echo Done.
)
