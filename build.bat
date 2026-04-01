@echo off
setlocal EnableExtensions EnableDelayedExpansion

REM ===============================
REM VARIABLES
REM ===============================
set "APP_NAME=Qubify-ITs Prodlendar"
set "PYTHON_EXE=python"
set "REQUIRED_LIBS=plyer tkcalendar pystray PIL"
set "EXE_NAME=Qubify-ITs Prodlendar.exe"
set "DIST_DIR=dist"
set "BUILD_DIR=build"

REM ===============================
REM CHECK PYTHON
REM ===============================
where %PYTHON_EXE% >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Download and install Python from https://www.python.org/downloads/
    pause
    exit /b
)

REM ===============================
REM CHECK PYINSTALLER
REM ===============================
%PYTHON_EXE% -m PyInstaller --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: PyInstaller is not installed.
    echo Install it with:
    echo   python -m pip install pyinstaller
    pause
    exit /b
)

REM ===============================
REM CHECK REQUIRED LIBRARIES
REM ===============================
set "MISSING_LIBS="
for %%L in (%REQUIRED_LIBS%) do (
    %PYTHON_EXE% -c "import %%L" 2>nul
    if ERRORLEVEL 1 (
        set "MISSING_LIBS=!MISSING_LIBS! %%L"
    )
)

if defined MISSING_LIBS (
    echo ERROR: The following Python libraries are missing:%MISSING_LIBS%
    echo Install them in Windows Powershell using:
    echo pip install plyer
    echo pip install tkcalendar
    echo pip install pystray
    echo pip install pillow
    pause
    exit /b
)

REM ===============================
REM BUILD EXE
REM ===============================
echo ==========================================
echo Building %APP_NAME%
echo ==========================================
echo.

%PYTHON_EXE% -m PyInstaller ^
 --onefile ^
 --windowed ^
 --clean ^
 --noconfirm ^
 --icon="icon.ico" ^
 --add-data "icon.ico;." ^
 --add-data "icon.png;." ^
 --hidden-import=plyer ^
 --hidden-import=plyer.platforms ^
 --hidden-import=plyer.platforms.win ^
 --hidden-import=plyer.platforms.win.notification ^
 --hidden-import=pystray ^
 --hidden-import=PIL ^
 --hidden-import=PIL.Image ^
 --hidden-import=PIL.ImageDraw ^
 --hidden-import=PIL.ImageTk ^
 calendar_app.py

IF NOT EXIST "%DIST_DIR%\calendar_app.exe" (
    echo ERROR: Build failed. EXE not found.
    pause
    exit /b 1
)

REM ===============================
REM RENAME EXE
REM ===============================
ren "dist\calendar_app.exe" "%EXE_NAME%"

echo.
echo Build completed successfully.
echo.

REM ===============================
REM STARTUP PROMPT
REM ===============================
set /p STARTUP=Start %APP_NAME% on Windows startup? (yes/no): 

IF /I "%STARTUP%" NEQ "yes" (
    echo Startup disabled.
    pause
    exit /b
)

echo Enabling startup...

REM ===============================
REM CREATE STARTUP SHORTCUT
REM ===============================
set "EXE_PATH=%CD%\%DIST_DIR%\%EXE_NAME%"
set "STARTUP_DIR=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "LNK_PATH=%STARTUP_DIR%\%EXE_NAME%.lnk"
set "PS_FILE=%TEMP%\create_startup_shortcut.ps1"

if not exist "%STARTUP_DIR%" mkdir "%STARTUP_DIR%"

echo $w = New-Object -ComObject WScript.Shell > "%PS_FILE%"
echo $s = $w.CreateShortcut("%LNK_PATH%"^) >> "%PS_FILE%"
echo $s.TargetPath = "%EXE_PATH%" >> "%PS_FILE%"
echo $s.WorkingDirectory = "%CD%\%DIST_DIR%" >> "%PS_FILE%"
echo $s.Save(^) >> "%PS_FILE%"

powershell -NoProfile -ExecutionPolicy Bypass -File "%PS_FILE%"

del "%PS_FILE%" >nul 2>&1

IF EXIST "%LNK_PATH%" (
    echo Startup enabled successfully.
) ELSE (
    echo ERROR: Failed to create startup shortcut.
)

echo.
pause
