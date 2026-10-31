@echo off
setlocal enabledelayedexpansion

:: Isolated flow-nodes preview stack (compose project "flowdev"):
::   web  http://localhost:3091   (image om/om-web-server:flowdev, built from this checkout)
::   api  http://localhost:8091   (om/om-backend:latest with this checkout's backend mounted)
::   DB   flow_dev on the main stack's Postgres; sandbox container flowdev-code-interpreter
::
:: NEVER use dev.bat for this: docker-compose.yml is the "virtualai" project, so
:: dev.bat would rebuild and restart the MAIN stack (port 3000) and migrate the real DB.
:: Requires the main stack running (network virtualai_default). See
:: docs/flow-nodes/HANDOVER.md "Building / running the preview".

set COMPOSE_FILE=%~dp0docker-compose.flow-dev.yml
set REPO_ROOT=%~dp0..\..
if "%FLOWDEV_ENV_FILE%"=="" set FLOWDEV_ENV_FILE=D:/tmp/flowdev.env
if "%FLOWDEV_CI_TOKEN_FILE%"=="" set FLOWDEV_CI_TOKEN_FILE=D:/tmp/flowdev_ci_token.txt
set COMPOSE_CMD=docker compose -p flowdev -f "%COMPOSE_FILE%"

set SANDBOX=flowdev-code-interpreter
set SANDBOX_IMAGE=om/code-interpreter:flowtest-p1b
set EXECUTOR_IMAGE=om/python-executor-sci
set EXECUTOR_TAG=flowtest

if "%~1"=="" goto usage
if /i "%~1"=="status" goto status
if not exist "%FLOWDEV_ENV_FILE%" (
    echo ERROR: FLOWDEV_ENV_FILE "%FLOWDEV_ENV_FILE%" not found.
    echo        It holds the api_server env with POSTGRES_DB=flow_dev and separate Redis DBs.
    exit /b 1
)
if /i "%~1"=="up" goto up
if /i "%~1"=="build-web" goto build_web
if /i "%~1"=="restart-api" goto restart_api
if /i "%~1"=="down" goto down
goto usage

:up
call :ensure_sandbox || exit /b 1
%COMPOSE_CMD% up -d
goto status

:build_web
docker build -t om/om-web-server:flowdev "%REPO_ROOT%\web" || exit /b 1
%COMPOSE_CMD% up -d --force-recreate --no-deps flow_web
goto status

:restart_api
:: The API runs this checkout's backend code (mounted); a restart picks up changes.
docker restart flowdev-flow_api-1
goto status

:down
%COMPOSE_CMD% down
docker rm -f %SANDBOX% >nul 2>&1
echo flowdev stack stopped (DB flow_dev is kept).
goto :eof

:status
docker ps -a --filter "name=flowdev" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
goto :eof

:ensure_sandbox
docker inspect %SANDBOX% >nul 2>&1 && (docker start %SANDBOX% >nul & exit /b 0)
if not exist "%FLOWDEV_CI_TOKEN_FILE%" (
    echo ERROR: sandbox token file "%FLOWDEV_CI_TOKEN_FILE%" not found.
    exit /b 1
)
set /p CI_TOKEN=<"%FLOWDEV_CI_TOKEN_FILE%"
docker run -d --name %SANDBOX% --network virtualai_default --user root ^
    -v //var/run/docker.sock:/var/run/docker.sock ^
    -e CODE_INTERPRETER_API_TOKEN=!CI_TOKEN! ^
    -e PYTHON_EXECUTOR_DOCKER_IMAGE=%EXECUTOR_IMAGE% ^
    -e PYTHON_EXECUTOR_DOCKER_TAG=%EXECUTOR_TAG% ^
    --entrypoint python %SANDBOX_IMAGE% ^
    -m uvicorn app.main:app --host 0.0.0.0 --port 8000 >nul || exit /b 1
echo started %SANDBOX%
exit /b 0

:usage
echo Usage: flowdev.bat ^<command^>
echo.
echo   up           Start the preview (sandbox, API on 8091, web on 3091)
echo   build-web    Rebuild the web image from this checkout and restart web (3091)
echo   restart-api  Restart the API to pick up backend code changes
echo   down         Stop the preview (keeps the flow_dev database)
echo   status       Show the flowdev containers
echo.
echo Env: FLOWDEV_ENV_FILE (default D:/tmp/flowdev.env),
echo      FLOWDEV_CI_TOKEN_FILE (default D:/tmp/flowdev_ci_token.txt)
echo.
echo Do NOT use dev.bat in this checkout for the preview: it targets the main "virtualai" stack.
goto :eof
