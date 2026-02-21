@echo off
setlocal enabledelayedexpansion

set COMPOSE_CMD=docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml
set INFRA=relational_db index cache inference_model_server indexing_model_server minio code-interpreter
set APP=api_server background web_server nginx

if "%~1"=="" goto usage

:: Resolve service names from arguments 2..N into SERVICES variable
set SERVICES=
set _i=2
:resolve_args
call set "_arg=%%%_i%%%"
if "!_arg!"=="" goto resolve_done
if /i "!_arg!"=="api" set SERVICES=!SERVICES! api_server
if /i "!_arg!"=="web" set SERVICES=!SERVICES! web_server
if /i "!_arg!"=="background" set SERVICES=!SERVICES! background
if /i "!_arg!"=="model" set SERVICES=!SERVICES! inference_model_server indexing_model_server
if /i "!_arg!"=="nginx" set SERVICES=!SERVICES! nginx
if /i "!_arg!"=="db" set SERVICES=!SERVICES! relational_db
if /i "!_arg!"=="cache" set SERVICES=!SERVICES! cache
if /i "!_arg!"=="vespa" set SERVICES=!SERVICES! index
if /i "!_arg!"=="minio" set SERVICES=!SERVICES! minio
set /a _i+=1
goto resolve_args
:resolve_done

:: ==================== UP ====================
if /i "%~1"=="up" (
    if /i "%~2"=="log" (
        if /i "%~3"=="infra" (
            echo Starting infrastructure with logs...
            %COMPOSE_CMD% up %INFRA%
        ) else if /i "%~3"=="app" (
            echo Starting app services with logs...
            %COMPOSE_CMD% up %APP%
        ) else if /i "%~3"=="" (
            echo Starting all services with logs...
            %COMPOSE_CMD% up
        ) else (
            call :resolve_from 3 %*
            echo Starting with logs:!SERVICES!
            %COMPOSE_CMD% up!SERVICES!
        )
    ) else if /i "%~2"=="infra" (
        echo Starting infrastructure services only...
        %COMPOSE_CMD% up -d --wait %INFRA%
    ) else if /i "%~2"=="app" (
        echo Starting app services only...
        %COMPOSE_CMD% up -d --wait %APP%
    ) else if /i "%~2"=="" (
        echo Starting all services...
        %COMPOSE_CMD% up -d --wait
    ) else (
        echo Starting:!SERVICES!
        %COMPOSE_CMD% up -d --wait!SERVICES!
    )
    goto end
)

:: ==================== DOWN ====================
if /i "%~1"=="down" (
    echo Stopping all services...
    %COMPOSE_CMD% down
    goto end
)

if /i "%~1"=="down-v" (
    echo Stopping all services and removing volumes...
    %COMPOSE_CMD% down -v
    goto end
)

:: ==================== BUILD ====================
if /i "%~1"=="build" (
    if /i "%~2"=="" (
        echo Building all services...
        %COMPOSE_CMD% up -d --build --wait
    ) else if /i "%~2"=="infra" (
        echo Building infrastructure services...
        %COMPOSE_CMD% up -d --build --wait %INFRA%
    ) else if /i "%~2"=="app" (
        echo Building app services...
        %COMPOSE_CMD% up -d --build --wait %APP%
    ) else (
        echo Building:!SERVICES!
        %COMPOSE_CMD% build!SERVICES!
        %COMPOSE_CMD% up -d --no-deps!SERVICES!
    )
    goto end
)

:: ==================== RESTART ====================
if /i "%~1"=="restart" (
    if /i "%~2"=="" (
        echo Restarting all services...
        %COMPOSE_CMD% restart
    ) else if /i "%~2"=="infra" (
        echo Restarting infrastructure services...
        %COMPOSE_CMD% restart %INFRA%
    ) else if /i "%~2"=="app" (
        echo Restarting app services...
        %COMPOSE_CMD% restart %APP%
    ) else (
        echo Restarting:!SERVICES!
        %COMPOSE_CMD% restart!SERVICES!
    )
    goto end
)

:: ==================== STOP ====================
if /i "%~1"=="stop" (
    if /i "%~2"=="" (
        echo Stopping all services...
        %COMPOSE_CMD% stop
    ) else if /i "%~2"=="infra" (
        echo Stopping infrastructure services...
        %COMPOSE_CMD% stop %INFRA%
    ) else if /i "%~2"=="app" (
        echo Stopping app services...
        %COMPOSE_CMD% stop %APP%
    ) else (
        echo Stopping:!SERVICES!
        %COMPOSE_CMD% stop!SERVICES!
    )
    goto end
)

:: ==================== LOGS ====================
if /i "%~1"=="logs" (
    if /i "%~2"=="" (
        %COMPOSE_CMD% logs -f --tail=100
    ) else if /i "%~2"=="app" (
        %COMPOSE_CMD% logs -f --tail=100 %APP%
    ) else if /i "%~2"=="infra" (
        %COMPOSE_CMD% logs -f --tail=100 %INFRA%
    ) else (
        %COMPOSE_CMD% logs -f --tail=100!SERVICES!
    )
    goto end
)

:: ==================== PS ====================
if /i "%~1"=="ps" (
    %COMPOSE_CMD% ps
    goto end
)

goto usage

:: ==================== HELPER ====================
:resolve_from
set SERVICES=
set _i=%~1
:resolve_from_loop
call set "_arg=%%%_i%%%"
if "!_arg!"=="" goto :eof
if /i "!_arg!"=="api" set SERVICES=!SERVICES! api_server
if /i "!_arg!"=="web" set SERVICES=!SERVICES! web_server
if /i "!_arg!"=="background" set SERVICES=!SERVICES! background
if /i "!_arg!"=="model" set SERVICES=!SERVICES! inference_model_server indexing_model_server
if /i "!_arg!"=="nginx" set SERVICES=!SERVICES! nginx
if /i "!_arg!"=="db" set SERVICES=!SERVICES! relational_db
if /i "!_arg!"=="cache" set SERVICES=!SERVICES! cache
if /i "!_arg!"=="vespa" set SERVICES=!SERVICES! index
if /i "!_arg!"=="minio" set SERVICES=!SERVICES! minio
set /a _i+=1
goto resolve_from_loop

:: ==================== USAGE ====================
:usage
echo.
echo   Onyx Dev Helper
echo   ===============
echo.
echo   Usage: dev.bat [command] [services...]
echo.
echo   Commands:
echo     up                    Start all services (detached)
echo     up log                Start all with live logs (foreground)
echo     up log app            Start app services with live logs
echo     up log infra          Start infra with live logs
echo     up log api            Start api_server with live logs
echo     up infra              Start infrastructure only (db, vespa, redis, models, minio)
echo     up app                Start app only (api, background, web, nginx)
echo     up api web ...        Start specific services
echo     down                  Stop all services
echo     down-v                Stop all services and remove volumes
echo     build                 Build and start all services
echo     build infra           Build and start infrastructure only
echo     build app             Build and start app services only
echo     build api             Build and start api_server only
echo     build web             Build and start web_server only
echo     build web api         Build and start both web + api
echo     build background      Build and start background worker
echo     build model           Build and start model servers
echo     restart               Restart all services
echo     restart infra         Restart infrastructure only
echo     restart app           Restart app services only
echo     restart api           Restart api_server
echo     restart web           Restart web_server
echo     restart api web       Restart both api + web
echo     stop                  Stop all services (without removing)
echo     stop app              Stop app services only
echo     stop api              Stop api_server only
echo     stop web              Stop web_server only
echo     logs                  Tail logs for all services
echo     logs app              Tail logs for app services
echo     logs infra            Tail logs for infrastructure
echo     logs api              Tail logs for api_server
echo     logs web              Tail logs for web_server
echo     ps                    Show running containers
echo.
echo   Groups:
echo     infra      = db, vespa, redis, model servers, minio, code-interpreter
echo     app        = api_server, background, web_server, nginx
echo.
echo   Service shortcuts:
echo     api        = api_server
echo     web        = web_server
echo     background = background
echo     model      = inference_model_server + indexing_model_server
echo     nginx      = nginx
echo     db         = relational_db
echo     cache      = cache (redis)
echo     vespa      = index (vespa)
echo     minio      = minio
echo.

:end
endlocal
