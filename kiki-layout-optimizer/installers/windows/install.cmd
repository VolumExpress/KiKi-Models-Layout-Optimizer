@echo off
setlocal
set "HERE=%~dp0"
set /p DEV="Enable unsigned Adobe CEP developer mode for current user? (y/N): "
if /I "%DEV%"=="y" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%HERE%install.ps1" -EnableUnsignedDev
) else (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%HERE%install.ps1"
)
if errorlevel 1 (echo Installation failed. See README_RU.md & pause & exit /b 1)
pause
