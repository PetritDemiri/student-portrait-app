@echo off
setlocal
cd /d "%~dp0"
title Foto Nxenesit - build

if not exist "foto_nxenesit.py" goto :nosource
if not exist "requirements.txt" goto :nosource

echo Looking for Python...
rem Ask Python for the full path of python.exe. The .exe is written out on purpose:
rem a plain py could pick up a file called py.py and open it in an editor instead.
set "PY="
for /f "delims=" %%P in ('py.exe -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%P"
if not defined PY for /f "delims=" %%P in ('python.exe -c "import sys; print(sys.executable)" 2^>nul') do set "PY=%%P"
if not defined PY goto :nopython
if not exist "%PY%" goto :nopython
echo Using %PY%
"%PY%" -c "import tkinter" >nul 2>nul || goto :notk

echo.
echo Installing customtkinter and PyInstaller...
"%PY%" -m pip install --upgrade -r requirements.txt || goto :failed

echo.
echo Building FotoNxenesit.exe - this takes about a minute...
"%PY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name FotoNxenesit --collect-data customtkinter --add-data "tests;tests" foto_nxenesit.py || goto :failed

echo.
echo Done: "%~dp0dist\FotoNxenesit.exe"
start "" "%~dp0dist"
pause
exit /b 0

:nosource
echo foto_nxenesit.py or requirements.txt was not found. Keep build.bat in the project folder.
goto :failed

:nopython
echo Python was not found. Install it from https://www.python.org/downloads/
echo and tick "Add python.exe to PATH" in the installer.
goto :failed

:notk
echo This Python has no Tcl/Tk, which the program needs.
echo Run the Python installer again, choose Modify and tick "tcl/tk and IDLE".
goto :failed

:failed
echo.
echo The build did not finish.
pause
exit /b 1
