@echo off
title VirtualAI - Workflow Creator Menu
color 0B

:MENU
cls
echo.
echo  ============================================
echo       VirtualAI Workflow Creator
echo  ============================================
echo.
echo   1. List all workflows
echo   2. Create workflows from workflows\ folder
echo   3. Run a workflow (enter ID + message)
echo   4. Generate icons for workflow personas
echo   5. Update workflows from workflows\ folder
echo   6. Delete a workflow by ID
echo   7. Export workflows to JSON
echo   8. Backfill wrapper personas
echo   9. Exit
echo.
set /p choice="  Select option [1-9]: "

if "%choice%"=="1" goto LIST
if "%choice%"=="2" goto CREATE
if "%choice%"=="3" goto RUN
if "%choice%"=="4" goto ICONS
if "%choice%"=="5" goto UPDATE
if "%choice%"=="6" goto DELETE
if "%choice%"=="7" goto EXPORT
if "%choice%"=="8" goto BACKFILL
if "%choice%"=="9" goto EXIT

echo.
echo  Invalid option. Try again.
timeout /t 2 >nul
goto MENU

:LIST
cls
echo.
echo  --- Listing all workflows ---
echo.
python create_workflows.py --list
echo.
pause
goto MENU

:CREATE
cls
echo.
echo  --- Creating workflows from workflows\ folder ---
echo.
set /p force="  Skip existing duplicates? [Y/n]: "
if /i "%force%"=="n" (
    python create_workflows.py --force
) else (
    python create_workflows.py
)
echo.
pause
goto MENU

:RUN
cls
echo.
echo  --- Run a Workflow ---
echo.
python create_workflows.py --list
echo.
set /p runid="  Enter workflow ID to run (or 'c' to cancel): "
if /i "%runid%"=="c" goto MENU
set /p msg="  Enter message: "
echo.
python create_workflows.py --run %runid% "%msg%"
echo.
pause
goto MENU

:ICONS
cls
echo.
echo  --- Generating icons for workflow personas ---
echo.
python generate_icon.py --all-workflows
echo.
pause
goto MENU

:UPDATE
cls
echo.
echo  --- Updating workflows from workflows\ folder ---
echo.
python create_workflows.py --update
echo.
pause
goto MENU

:DELETE
cls
echo.
echo  --- Current workflows ---
echo.
python create_workflows.py --list
echo.
set /p delid="  Enter workflow ID to delete (or 'c' to cancel): "
if /i "%delid%"=="c" goto MENU
echo.
python create_workflows.py --delete %delid%
echo.
pause
goto MENU

:EXPORT
cls
echo.
set /p outfile="  Export filename [workflows/backup.json]: "
if "%outfile%"=="" set outfile=workflows\backup.json
echo.
echo  --- Exporting to %outfile% ---
echo.
python create_workflows.py --export "%outfile%"
echo.
pause
goto MENU

:BACKFILL
cls
echo.
echo  --- Backfilling wrapper personas ---
echo.
python create_workflows.py --backfill-personas
echo.
pause
goto MENU

:EXIT
echo.
echo  Goodbye!
echo.
exit /b 0
