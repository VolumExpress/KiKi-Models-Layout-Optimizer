@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" py -3 -m venv .venv
if not exist ".venv\Scripts\python.exe" (
  echo Python 3.10 or newer is required. Install it from python.org.
  pause
  exit /b 1
)
.venv\Scripts\python.exe -m pip install -e .
if errorlevel 1 (echo Install failed & pause & exit /b 1)
echo.
echo Python installed. Now run install_cep_windows.bat and restart Illustrator.
echo Open Window ^> Extensions (Legacy) ^> KiKi Layout Optimizer (v0.7.1 Beta).
pause
