@echo off
setlocal
cd /d "%~dp0"
if exist ".venv\Scripts\python.exe" goto dependencies
py -3.13 -m venv .venv
if errorlevel 1 goto failure
:dependencies
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto failure
".venv\Scripts\python.exe" app.py
if errorlevel 1 goto failure
exit /b 0
:failure
echo Firecube could not start. Copy the error above for diagnosis.
pause
exit /b 1
