@echo off
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
pause