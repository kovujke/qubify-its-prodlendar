@echo off
setlocal

echo Building Qubify-IT's Prodlendar...
echo.

C:\Python312\python.exe -m PyInstaller ^
 --onefile ^
 --windowed ^
 --clean ^
 --noconfirm ^
 --hidden-import=plyer ^
 --hidden-import=plyer.platforms ^
 --hidden-import=plyer.platforms.win ^
 --hidden-import=plyer.platforms.win.notification ^
 calendar_app.py

echo.
echo Build finished.
echo.

set /p STARTUP=Start Qubify-IT's Prodlendar on Windows startup? (yes/no): 

if /i "%STARTUP%"=="yes" (
    echo Enabling startup...

    copy /Y "C:\Users\konst\dist\calendar_app.exe" "C:\Users\konst\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Qubify-ITs Prodlendar.exe" >nul

    if exist "C:\Users\konst\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup\Qubify-ITs Prodlendar.exe" (
        echo Startup enabled successfully.
    ) else (
        echo Failed to enable startup.
    )
) else (
    echo Startup disabled.
)

echo.
pause
