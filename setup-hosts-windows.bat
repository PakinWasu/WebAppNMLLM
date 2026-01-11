@echo off
REM Script to add mnp.local to Windows hosts file
REM Run as Administrator

echo ========================================
echo Setup mnp.local in Windows hosts file
echo ========================================
echo.

set HOSTS_FILE=C:\Windows\System32\drivers\etc\hosts
set SERVER_IP=10.4.15.53
set DOMAIN=mnp.local

echo Checking if entry already exists...
findstr /C:"%DOMAIN%" %HOSTS_FILE% >nul
if %errorlevel% == 0 (
    echo Entry already exists in hosts file.
    echo.
    type %HOSTS_FILE% | findstr /C:"%DOMAIN%"
    echo.
    echo No changes needed.
    pause
    exit /b
)

echo.
echo Adding entry to hosts file...
echo %SERVER_IP%    %DOMAIN% >> %HOSTS_FILE%
echo %SERVER_IP%    www.%DOMAIN% >> %HOSTS_FILE%

if %errorlevel% == 0 (
    echo.
    echo ✅ Successfully added to hosts file!
    echo.
    echo Flushing DNS cache...
    ipconfig /flushdns
    echo.
    echo ✅ DNS cache flushed!
    echo.
    echo You can now access: http://%DOMAIN%
) else (
    echo.
    echo ❌ Error: Could not write to hosts file.
    echo.
    echo Please run this script as Administrator:
    echo 1. Right-click on this file
    echo 2. Select "Run as administrator"
)

echo.
pause

