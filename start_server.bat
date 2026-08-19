@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Competition Management System - Mobile API
echo ============================================
echo.
echo [1/2] Checking dependencies...
python -c "import flask, pymysql" >nul 2>&1
if errorlevel 1 (
    echo Installing flask, pymysql ...
    pip install flask pymysql -i https://pypi.tuna.tsinghua.edu.cn/simple
)
echo.
echo [2/2] Starting server ...
echo.
python server.py
pause
