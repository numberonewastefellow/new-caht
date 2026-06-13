@echo off
setlocal enabledelayedexpansion

REM ===========================================================================
REM Waits for the Vespa -> OpenSearch backfill to finish, then switches the
REM RETRIEVAL engine to OpenSearch via the admin API.
REM
REM Use this AFTER starting both engines (mode [B] in .env:
REM   COMPOSE_PROFILES=s3-filestore,vespa,opensearch
REM   ENABLE_OPENSEARCH_INDEXING_FOR_ONYX=true) and running `dev up`.
REM
REM Requires an ADMIN API key (create one in the UI: Admin ^> API Keys).
REM
REM Usage:
REM   set ONYX_API_KEY=^<key^>
REM   switch-retrieval-to-opensearch.bat            ::  wait + switch to OpenSearch
REM   switch-retrieval-to-opensearch.bat --revert   ::  switch back to Vespa (no wait)
REM
REM Optional env vars:
REM   BASE_URL        (default http://localhost:3000)
REM   POLL_INTERVAL   seconds between status polls (default 10)
REM   TIMEOUT         max seconds to wait for backfill (default 3600)
REM ===========================================================================

if "%BASE_URL%"=="" set "BASE_URL=http://localhost:3000"
if "%POLL_INTERVAL%"=="" set "POLL_INTERVAL=10"
if "%TIMEOUT%"=="" set "TIMEOUT=3600"

set "ENABLE=true"
if /i "%~1"=="--revert" set "ENABLE=false"

if "%ONYX_API_KEY%"=="" (
    echo ERROR: ONYX_API_KEY is not set. Create an admin API key in the UI ^(Admin ^> API Keys^)
    echo        then run:  set ONYX_API_KEY=^<key^> ^&^& switch-retrieval-to-opensearch.bat
    exit /b 1
)

set "STATUS_URL=%BASE_URL%/api/admin/opensearch-migration/status"
set "RETRIEVAL_URL=%BASE_URL%/api/admin/opensearch-migration/retrieval"
set "TMP_STATUS=%TEMP%\onyx_os_migration_status.json"

if /i "%ENABLE%"=="true" (
    echo Waiting for the Vespa -^> OpenSearch backfill to complete...
    echo   status endpoint: %STATUS_URL%
    set /a ELAPSED=0
    :poll
    curl -fsS -H "Authorization: Bearer %ONYX_API_KEY%" "%STATUS_URL%" -o "%TMP_STATUS%" 2>nul
    if exist "%TMP_STATUS%" (
        type "%TMP_STATUS%"
        echo.
        REM 'migration_completed_at' is null until the backfill finishes (Starlette emits compact JSON).
        findstr /C:"\"migration_completed_at\":null" "%TMP_STATUS%" >nul
        if errorlevel 1 (
            echo Backfill complete.
            goto switch
        )
    ) else (
        echo   ...no response yet ^(is the API up and the key valid?^)
    )
    if !ELAPSED! GEQ %TIMEOUT% (
        echo ERROR: timed out after %TIMEOUT%s waiting for the backfill to finish.
        exit /b 1
    )
    timeout /t %POLL_INTERVAL% /nobreak >nul
    set /a ELAPSED+=%POLL_INTERVAL%
    goto poll
)

:switch
echo Setting enable_opensearch_retrieval=%ENABLE% ...
curl -fsS -X PUT -H "Authorization: Bearer %ONYX_API_KEY%" -H "Content-Type: application/json" -d "{\"enable_opensearch_retrieval\": %ENABLE%}" "%RETRIEVAL_URL%"
echo.
echo Current retrieval state:
curl -fsS -H "Authorization: Bearer %ONYX_API_KEY%" "%RETRIEVAL_URL%"
echo.
if /i "%ENABLE%"=="true" (
    echo Done. Retrieval is now served by OpenSearch.
) else (
    echo Done. Retrieval is now served by Vespa.
)
endlocal
