@echo off
chcp 65001 >nul
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo [提示] 请右键此文件，选择 "以管理员身份运行"
    echo.
    pause
    exit /b 1
)
echo ============================================
echo  安装开机自启 - 手机远程启动助手
echo ============================================
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup_helper.ps1"
if %errorlevel% neq 0 (
    echo.
    echo [失败] 注册出错，请确认 setup_helper.ps1 存在
) else (
    echo.
    echo [完成] 开机自启已安装：电脑开机/登录后，MySQL 和后端会自动运行
)
echo.
pause
