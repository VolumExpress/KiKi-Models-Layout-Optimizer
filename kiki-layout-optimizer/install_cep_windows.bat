@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Please run install_windows.bat first - Python environment is missing.
  pause
  exit /b 1
)
echo Installing KiKi CEP BETA. This copies an unsigned extension into your user profile.
echo Developer mode is required for unsigned CEP extensions and is enabled only for your account.
choice /C YN /M "Enable unsigned CEP development mode (CSXS.11 and CSXS.12)"
if errorlevel 2 (
  ".venv\Scripts\python.exe" -m kiki_layout.cep_install
) else (
  ".venv\Scripts\python.exe" -m kiki_layout.cep_install --enable-unsigned-dev
)
if errorlevel 1 echo CEP installation failed. Read docs\cep-beta.md.
pause
