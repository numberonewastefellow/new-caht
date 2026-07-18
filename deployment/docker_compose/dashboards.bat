@echo off
setlocal

:: ============================================================================
::  VirtualAI - OpenSearch Dashboards helper (Windows)
::  Native equivalent of opensearch_dashboards\import_dashboards.sh
::
::  Imports the "VirtualAI - Files & Chunks" dashboard (index-pattern,
::  visualizations, saved search) into the running OpenSearch Dashboards.
::  Uses overwrite=true, so it is idempotent - re-running just updates them.
:: ============================================================================

set "DASH_DIR=%~dp0opensearch_dashboards"
set "NDJSON=%DASH_DIR%\files_and_chunks.ndjson"
set "BUILDER=%DASH_DIR%\build_ndjson.py"

:: Connection defaults (override by setting the env var before calling)
if not defined DASH_URL    set "DASH_URL=http://localhost:5601"
if not defined DASH_USER   set "DASH_USER=admin"
if not defined DASH_PASS   set "DASH_PASS=StrongPassword123!"
if not defined DASH_TENANT set "DASH_TENANT=global"

:: Resolve command (default: import)
set "CMD=%~1"
if "%CMD%"=="" set "CMD=import"

if /i "%CMD%"=="help"   goto usage
if /i "%CMD%"=="/?"     goto usage
if /i "%CMD%"=="-h"     goto usage
if /i "%CMD%"=="--help" goto usage
if /i "%CMD%"=="build"  goto build
if /i "%CMD%"=="deploy" goto deploy
if /i "%CMD%"=="import" goto import
goto usage

:: ==================== BUILD (regenerate NDJSON only) ====================
:build
echo Regenerating saved objects (build_ndjson.py) ...
python "%BUILDER%"
if errorlevel 1 (
    echo [ERROR] Failed to regenerate NDJSON. Is Python installed and on PATH?
    goto end
)
goto end

:: ==================== DEPLOY (regenerate + import) ====================
:deploy
echo Regenerating saved objects (build_ndjson.py) ...
python "%BUILDER%"
if errorlevel 1 (
    echo [ERROR] Failed to regenerate NDJSON. Is Python installed and on PATH?
    goto end
)
goto do_import

:: ==================== IMPORT (default) ====================
:import
:: Auto-generate the NDJSON if it is missing
if not exist "%NDJSON%" (
    echo Saved-objects file not found, generating it ...
    python "%BUILDER%"
    if errorlevel 1 (
        echo [ERROR] Could not generate NDJSON. Is Python installed and on PATH?
        goto end
    )
)
goto do_import

:do_import
if not exist "%NDJSON%" (
    echo [ERROR] Saved-objects file not found: %NDJSON%
    echo         Generate it first:  dashboards.bat build
    goto end
)

set "TENANT_HEADER="
if not "%DASH_TENANT%"=="" set "TENANT_HEADER=-H "securitytenant: %DASH_TENANT%""

echo Importing files_and_chunks.ndjson into %DASH_URL% (tenant: %DASH_TENANT%) ...
curl -sf -u "%DASH_USER%:%DASH_PASS%" ^
  -H "osd-xsrf: true" ^
  %TENANT_HEADER% ^
  -X POST "%DASH_URL%/api/saved_objects/_import?overwrite=true" ^
  --form "file=@%NDJSON%;type=application/ndjson"
if errorlevel 1 (
    echo.
    echo [ERROR] Import failed. Is OpenSearch Dashboards up at %DASH_URL% ^(and are the credentials right^)?
    goto end
)
echo.
echo Done. Open %DASH_URL% -^> menu, Dashboard -^> "VirtualAI - Files ^& Chunks".
echo If you don't see it, switch tenant to 'Global' (top-right user menu -^> Switch tenants).
goto end

:: ==================== USAGE ====================
:usage
echo.
echo   VirtualAI Dashboards Helper
echo   ==========================
echo.
echo   Usage: dashboards.bat [command]
echo.
echo   Commands:
echo     import    (default) Import files_and_chunks.ndjson into OpenSearch Dashboards
echo     build     Regenerate files_and_chunks.ndjson from build_ndjson.py
echo     deploy    Regenerate the NDJSON, then import it
echo     help      Show this help
echo.
echo   Env overrides (set before calling):
echo     DASH_URL     (default http://localhost:5601)
echo     DASH_USER    (default admin)
echo     DASH_PASS    (default StrongPassword123!)
echo     DASH_TENANT  (default global; set empty for your private tenant)
echo.
echo   Examples:
echo     dashboards.bat                 Import into the running OpenSearch Dashboards
echo     dashboards.bat deploy          Rebuild the NDJSON, then import
echo     set DASH_URL=http://host:5601 ^&^& dashboards.bat
echo.

:end
endlocal
