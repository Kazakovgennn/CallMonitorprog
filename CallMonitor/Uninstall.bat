@echo off
chcp 65001 >nul
title CallMonitor Uninstall

schtasks /delete /tn "CallMonitor" /f

if %errorlevel% equ 0 (
    echo Task "CallMonitor" removed.
) else (
    echo Task not found or already removed.
)

pause