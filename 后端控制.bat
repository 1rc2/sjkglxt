@echo off
chcp 65001 >nul
cd /d "%~dp0"
D:\python\python.exe "backend_control.py"
pause
