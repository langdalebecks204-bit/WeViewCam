@echo off
chcp 65001 >nul
title WeViewCam 视频监控平台 (Windows)

echo ========================================================
echo   WeViewCam 视频监控与回放客户端 (Windows 版)
echo ========================================================

cd /d "%~dp0"

python main.py

if %errorlevel% neq 0 (
    echo.
    echo 运行发生异常，请检查上述错误日志。
    pause
)
