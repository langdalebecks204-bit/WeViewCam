@echo off
chcp 65001 >nul
title WeViewCam Windows 可执行程序打包 (PyInstaller)

echo ========================================================
echo   WeViewCam Windows EXE 一键编译打包工具
echo ========================================================

cd /d "%~dp0"

pyinstaller --noconfirm WeViewCam.spec

if %errorlevel% equ 0 (
    python pack.py
)
if %errorlevel% equ 0 (
    echo ========================================================
    echo 编译成功！输出目录位于: dist\WeViewCam\WeViewCam.exe
    echo ========================================================
) else (
    echo 编译过程遇到错误，请检查输出。
)
pause
