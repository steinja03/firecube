@echo off
setlocal
cd /d "%~dp0"
py -3.13 trial_wizard.py --restore
pause
