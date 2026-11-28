@echo off
rem  Project Management APP - start here.
rem
rem  Looks for a Python to run with, in this order:
rem      1. runtime\python.exe beside this file   (nothing is installed on this PC)
rem      2. the py launcher                        (a normal Python installation)
rem      3. python on the PATH
rem  and says so plainly if it finds none.

setlocal
cd /d "%~dp0"

if exist "%~dp0runtime\python.exe" (
  "%~dp0runtime\python.exe" "%~dp0PM_APP.py" %*
  goto done
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
  py -3 "%~dp0PM_APP.py" %*
  goto done
)

rem  DO NOT JUST RUN `python`. On Windows 10 and 11 an "app execution alias" for
rem  python.exe exists by DEFAULT at %LOCALAPPDATA%\Microsoft\WindowsApps, and running
rem  it opens the Microsoft Store - on a PC with no Python, which is exactly the PC
rem  this launcher is for. `where` only LOOKS, so the alias is found and skipped
rem  without ever being started.
set "PYEXE="
for /f "delims=" %%p in ('where python 2^>nul') do if not defined PYEXE set "PYEXE=%%p"
if defined PYEXE (
  echo %PYEXE% | find /i "\WindowsApps\" >nul && set "PYEXE="
)
if defined PYEXE (
  "%PYEXE%" "%~dp0PM_APP.py" %*
  goto done
)

echo.
echo   This PC has no Python, and no runtime was supplied beside the application.
echo.
echo   Either is enough:
echo     * ask for the folder that has runtime\ inside it - nothing gets installed
echo     * or ask IT for Python 3.9 or newer
echo.
echo   Nothing has been changed on this PC.
echo.
pause
goto :eof

:done
rem  A non-zero code here is the application failing to START - a stopped application
rem  exits cleanly. Without this the window closes on the message explaining why.
if errorlevel 1 (
  echo.
  echo   The application stopped with an error. The lines above say why.
  echo.
  pause
)
