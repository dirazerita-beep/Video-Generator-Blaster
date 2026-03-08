@echo off
echo ============================================================
echo  Building Video Generator Blaster (Portable EXE)
echo ============================================================
echo.

pip install pyinstaller
if errorlevel 1 (
    echo ERROR: pip install pyinstaller failed.
    pause
    exit /b 1
)

pyinstaller --noconfirm --windowed --name "VideoGeneratorBlaster" ^
    --add-data "assets;assets" ^
    --add-data "third_party;third_party" ^
    --icon "assets/icon.ico" ^
    app/main.py

if errorlevel 1 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo  Build successful!
echo  Portable app is in: dist\VideoGeneratorBlaster\
echo ============================================================
pause
