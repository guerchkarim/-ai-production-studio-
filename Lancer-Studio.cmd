@echo off
cd /d "%~dp0"
python scripts\start_studio.py
if errorlevel 1 pause
