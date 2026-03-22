@echo off
echo Building FC Squad Downloader...
echo.

REM Install PyInstaller if not installed
pip install pyinstaller --quiet

REM Build the executable
pyinstaller --onefile --windowed --name "FC_Squad_Downloader" main.py

echo.
echo Build complete!
echo Executable: dist\FC_Squad_Downloader.exe
pause