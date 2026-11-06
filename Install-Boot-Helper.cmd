@echo off
setlocal
cd /d "%~dp0"
py -3.13 observer_control.py install-boot-helper
pause
