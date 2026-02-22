@echo off
title VirtualAI - Agent Creator Menu
color 0A

:MENU
cls
echo.
echo  ============================================
echo       VirtualAI Agent Creator
echo  ============================================
echo.
echo   1. List all assistants
echo   2. List available tools
echo   3. Create assistants from assistants\ folder
echo   4. Import from Open WebUI (preview)
echo   5. Import from Open WebUI (create directly)
echo   6. Export all assistants to JSON
echo   7. Delete an assistant by ID
echo   8. Exit
echo.
set /p choice="  Select option [1-8]: "

if "%choice%"=="1" goto LIST
if "%choice%"=="2" goto TOOLS
if "%choice%"=="3" goto CREATE
if "%choice%"=="4" goto IMPORT_PREVIEW
if "%choice%"=="5" goto IMPORT_CREATE
if "%choice%"=="6" goto EXPORT
if "%choice%"=="7" goto DELETE
if "%choice%"=="8" goto EXIT

echo.
echo  Invalid option. Try again.
timeout /t 2 >nul
goto MENU

:LIST
cls
echo.
echo  --- Listing all assistants ---
echo.
python create_assistants.py --list
echo.
pause
goto MENU

:TOOLS
cls
echo.
echo  --- Available Tools ---
echo.
python create_assistants.py --list-tools
echo.
pause
goto MENU

:CREATE
cls
echo.
echo  --- Creating assistants from assistants\ folder ---
echo.
set /p force="  Skip existing duplicates? [Y/n]: "
if /i "%force%"=="n" (
    python create_assistants.py --force
) else (
    python create_assistants.py
)
echo.
pause
goto MENU

:IMPORT_PREVIEW
cls
echo.
echo  --- Open WebUI Import Preview ---
echo.
python import_open_webui.py
echo.
pause
goto MENU

:IMPORT_CREATE
cls
echo.
echo  --- Importing Open WebUI assistants to VirtualAI ---
echo.
set /p force2="  Skip existing duplicates? [Y/n]: "
if /i "%force2%"=="n" (
    python import_open_webui.py --create --force
) else (
    python import_open_webui.py --create
)
echo.
pause
goto MENU

:EXPORT
cls
echo.
set /p outfile="  Export filename [assistants/backup.json]: "
if "%outfile%"=="" set outfile=assistants\backup.json
echo.
echo  --- Exporting to %outfile% ---
echo.
python create_assistants.py --export "%outfile%"
echo.
pause
goto MENU

:DELETE
cls
echo.
echo  --- Current assistants ---
echo.
python create_assistants.py --list
echo.
set /p delid="  Enter assistant ID to delete (or 'c' to cancel): "
if /i "%delid%"=="c" goto MENU
echo.
python create_assistants.py --delete %delid%
echo.
pause
goto MENU

:EXIT
echo.
echo  Goodbye!
echo.
exit /b 0
