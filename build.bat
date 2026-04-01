@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM variables
set "APP_NAME=Qubify-ITs Prodlendar"
set "PYTHON_EXE=python"
set "REQUIRED_LIBS=plyer tkcalendar"
set "EXE_NAME=Qubify-ITs Prodlendar.exe"
set "DIST_DIR=dist"
set "BUILD_DIR=build"

REM check python
where %PYTHON_EXE% >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download and install Python from https://www.python.org/downloads/
    pause
    exit /b
)

REM check pyinstaller
%PYTHON_EXE% -m PyInstaller --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: PyInstaller is not installed.
    echo Install it with:
    echo   python -m pip install pyinstaller
    pause
    exit /b
)

REM check required libraries
set "MISSING_LIBS="
for %%L in (%REQUIRED_LIBS%) do (
    %PYTHON_EXE% -c "import %%L" 2>nul
    if ERRORLEVEL 1 (
        set "MISSING_LIBS=!MISSING_LIBS! %%L"
    )
)

if defined MISSING_LIBS (
    echo ERROR: The following Python libraries are missing:%MISSING_LIBS%
    echo Install them using:
    for %%L in (%REQUIRED_LIBS%) do (
        echo pip install %%L
    )
    pause
    exit /b
)

REM build exe
echo ==========================================
echo Building %APP_NAME%
echo ==========================================
echo.

%PYTHON_EXE% -m PyInstaller ^
 --onefile ^
 --windowed ^
 --clean ^
 --noconfirm ^
 --hidden-import=plyer ^
 --hidden-import=plyer.platforms ^
 --hidden-import=plyer.platforms.win ^
 --hidden-import=plyer.platforms.win.notification ^
 calendar_app.py

IF NOT EXIST "%DIST_DIR%\calendar_app.exe" (
    echo ERROR: Build failed. EXE not found.
    pause
    exit /b 1
)

REM rename exe
ren "dist\calendar_app.exe" "%EXE_NAME%"

echo.
echo Build completed successfully.
echo.

REM startup
set /p STARTUP=Start %APP_NAME% on Windows startup? (yes/no): 

IF /I "%STARTUP%" NEQ "yes" (
    echo Startup disabled.
    pause
    exit /b
)

echo Enabling startup...

REM create shortcut
set "EXE_PATH=%CD%\%DIST_DIR%\%EXE_NAME%"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LNK_PATH=%STARTUP_DIR%\%EXE_NAME%.lnk"
set "PS_FILE=%TEMP%\create_startup_shortcut.ps1"

REM make sure startup folder exists
if not exist "%STARTUP_DIR%" mkdir "%STARTUP_DIR%"

REM create powershell script
(
echo $w = New-Object -ComObject WScript.Shell
echo $s = $w.CreateShortcut("%LNK_PATH%")
echo $s.TargetPath = "%EXE_PATH%"
echo $s.WorkingDirectory = "%CD%\%DIST_DIR%"
echo $s.Save()
) > "%PS_FILE%"

REM run powershell
powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_FILE%"

REM cleanup
del "%PS_FILE%" >nul 2>&1

IF EXIST "%LNK_PATH%" (
    echo Startup enabled successfully.
) ELSE (
    echo ERROR: Failed to create startup shortcut.
)

echo.
pause
