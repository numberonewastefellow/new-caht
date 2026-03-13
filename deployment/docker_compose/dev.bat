@echo off
setlocal enabledelayedexpansion

set COMPOSE_CMD=docker compose -f docker-compose.yml -f docker-compose.dev-windows.yml
set INFRA=relational_db index cache inference_model_server indexing_model_server minio code-interpreter smartsearch phoenix
set APP=api_server background web_server nginx

:: Office MCP server (PPT + DOCX + PDF) runs from a separate compose file
set OFFICE_DIR=%~dp0..\..\office-mcp-server
set OFFICE_COMPOSE=docker compose -f "%OFFICE_DIR%\docker-compose.yml"

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
if /i "!_arg!"=="search" set SERVICES=!SERVICES! smartsearch
if /i "!_arg!"=="smartsearch" set SERVICES=!SERVICES! smartsearch
if /i "!_arg!"=="phoenix" set SERVICES=!SERVICES! phoenix
if /i "!_arg!"=="office" set SERVICES=!SERVICES! __OFFICE__
if /i "!_arg!"=="ppt" set SERVICES=!SERVICES! __OFFICE__
if /i "!_arg!"=="docx" set SERVICES=!SERVICES! __OFFICE__
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
        ) else if /i "%~3"=="office" (
            echo Starting Office MCP server with logs...
            call :office_up_log
        ) else if /i "%~3"=="ppt" (
            echo Starting Office MCP server with logs...
            call :office_up_log
        ) else if /i "%~3"=="" (
            echo Starting all services with logs...
            call :office_up
            %COMPOSE_CMD% up
        ) else (
            call :resolve_from 3 %*
            call :handle_office_in_services up_log
            if defined SERVICES (
                echo Starting with logs:!SERVICES!
                %COMPOSE_CMD% up!SERVICES!
            )
        )
    ) else if /i "%~2"=="infra" (
        echo Starting infrastructure services only...
        %COMPOSE_CMD% up -d --wait %INFRA%
    ) else if /i "%~2"=="app" (
        echo Starting app services only...
        %COMPOSE_CMD% up -d --wait %APP%
    ) else if /i "%~2"=="office" (
        echo Starting Office MCP server...
        call :office_up
        call :office_network_connect
    ) else if /i "%~2"=="ppt" (
        echo Starting Office MCP server...
        call :office_up
        call :office_network_connect
    ) else if /i "%~2"=="" (
        echo Starting all services...
        call :office_up
        %COMPOSE_CMD% up -d --wait
        call :office_network_connect
    ) else (
        call :handle_office_in_services up
        if defined SERVICES (
            echo Starting:!SERVICES!
            %COMPOSE_CMD% up -d --wait!SERVICES!
        )
    )
    goto end
)

:: ==================== DOWN ====================
if /i "%~1"=="down" (
    echo Stopping all services...
    %COMPOSE_CMD% down
    echo Stopping Office MCP server...
    %OFFICE_COMPOSE% down
    goto end
)

if /i "%~1"=="down-v" (
    echo Stopping all services and removing volumes...
    %COMPOSE_CMD% down -v
    echo Stopping Office MCP server and removing volumes...
    %OFFICE_COMPOSE% down -v
    goto end
)

:: ==================== BUILD ====================
if /i "%~1"=="build" (
    if /i "%~2"=="" (
        echo Building all services...
        %COMPOSE_CMD% build
        %COMPOSE_CMD% up -d --wait
        echo Building Office MCP server...
        call :office_build
        call :office_network_connect
    ) else if /i "%~2"=="infra" (
        echo Building infrastructure services...
        %COMPOSE_CMD% build %INFRA%
        %COMPOSE_CMD% up -d --wait %INFRA%
    ) else if /i "%~2"=="app" (
        echo Building app services...
        %COMPOSE_CMD% build %APP%
        %COMPOSE_CMD% up -d --wait %APP%
    ) else if /i "%~2"=="office" (
        echo Building Office MCP server...
        call :office_build
        call :office_network_connect
    ) else if /i "%~2"=="ppt" (
        echo Building Office MCP server...
        call :office_build
        call :office_network_connect
    ) else (
        call :handle_office_in_services build
        if defined SERVICES (
            echo Building:!SERVICES!
            %COMPOSE_CMD% build!SERVICES!
            %COMPOSE_CMD% up -d --no-deps!SERVICES!
        )
    )
    goto end
)

:: ==================== RESTART ====================
if /i "%~1"=="restart" (
    if /i "%~2"=="" (
        echo Restarting all services...
        %COMPOSE_CMD% restart
        %OFFICE_COMPOSE% restart
    ) else if /i "%~2"=="infra" (
        echo Restarting infrastructure services...
        %COMPOSE_CMD% restart %INFRA%
    ) else if /i "%~2"=="app" (
        echo Restarting app services...
        %COMPOSE_CMD% restart %APP%
    ) else if /i "%~2"=="office" (
        echo Restarting Office MCP server...
        %OFFICE_COMPOSE% restart
    ) else if /i "%~2"=="ppt" (
        echo Restarting Office MCP server...
        %OFFICE_COMPOSE% restart
    ) else (
        call :handle_office_in_services restart
        if defined SERVICES (
            echo Restarting:!SERVICES!
            %COMPOSE_CMD% restart!SERVICES!
        )
    )
    goto end
)

:: ==================== STOP ====================
if /i "%~1"=="stop" (
    if /i "%~2"=="" (
        echo Stopping all services...
        %COMPOSE_CMD% stop
        %OFFICE_COMPOSE% stop
    ) else if /i "%~2"=="infra" (
        echo Stopping infrastructure services...
        %COMPOSE_CMD% stop %INFRA%
    ) else if /i "%~2"=="app" (
        echo Stopping app services...
        %COMPOSE_CMD% stop %APP%
    ) else if /i "%~2"=="office" (
        echo Stopping Office MCP server...
        %OFFICE_COMPOSE% stop
    ) else if /i "%~2"=="ppt" (
        echo Stopping Office MCP server...
        %OFFICE_COMPOSE% stop
    ) else (
        call :handle_office_in_services stop
        if defined SERVICES (
            echo Stopping:!SERVICES!
            %COMPOSE_CMD% stop!SERVICES!
        )
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
    ) else if /i "%~2"=="office" (
        %OFFICE_COMPOSE% logs -f --tail=100
    ) else if /i "%~2"=="ppt" (
        %OFFICE_COMPOSE% logs -f --tail=100
    ) else (
        call :handle_office_in_services logs
        if defined SERVICES (
            %COMPOSE_CMD% logs -f --tail=100!SERVICES!
        )
    )
    goto end
)

:: ==================== PS ====================
if /i "%~1"=="ps" (
    echo === Onyx Services ===
    %COMPOSE_CMD% ps
    echo.
    echo === Office MCP Server ===
    %OFFICE_COMPOSE% ps
    goto end
)

goto usage

:: ==================== HELPERS ====================

:: Resolve service names starting from arg position %1
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
if /i "!_arg!"=="search" set SERVICES=!SERVICES! smartsearch
if /i "!_arg!"=="smartsearch" set SERVICES=!SERVICES! smartsearch
if /i "!_arg!"=="phoenix" set SERVICES=!SERVICES! phoenix
if /i "!_arg!"=="office" set SERVICES=!SERVICES! __OFFICE__
if /i "!_arg!"=="ppt" set SERVICES=!SERVICES! __OFFICE__
if /i "!_arg!"=="docx" set SERVICES=!SERVICES! __OFFICE__
set /a _i+=1
goto resolve_from_loop

:: Handle Office MCP server when mixed with other services
:: Checks if __OFFICE__ is in SERVICES, runs Office compose separately, removes __OFFICE__ from SERVICES
:handle_office_in_services
set _office_action=%~1
set _has_office=
set _clean_services=
for %%s in (!SERVICES!) do (
    if /i "%%s"=="__OFFICE__" (
        set _has_office=1
    ) else (
        set _clean_services=!_clean_services! %%s
    )
)
set SERVICES=!_clean_services!
if defined _has_office (
    if /i "!_office_action!"=="up" (
        echo Starting Office MCP server...
        call :office_up
        call :office_network_connect
    ) else if /i "!_office_action!"=="up_log" (
        echo Starting Office MCP server...
        call :office_up_log
    ) else if /i "!_office_action!"=="build" (
        echo Building Office MCP server...
        call :office_build
        call :office_network_connect
    ) else if /i "!_office_action!"=="restart" (
        echo Restarting Office MCP server...
        %OFFICE_COMPOSE% restart
    ) else if /i "!_office_action!"=="stop" (
        echo Stopping Office MCP server...
        %OFFICE_COMPOSE% stop
    ) else if /i "!_office_action!"=="logs" (
        echo Office MCP server logs:
        %OFFICE_COMPOSE% logs -f --tail=100
    )
)
goto :eof

:: Office MCP server operations
:office_up
%OFFICE_COMPOSE% up -d
goto :eof

:office_up_log
%OFFICE_COMPOSE% up
goto :eof

:office_build
%OFFICE_COMPOSE% up -d --build
goto :eof

:: Connect Office container to the main compose network (required for inter-container DNS)
:: Auto-detects the network name (virtualai_default or onyx_default)
:office_network_connect
echo Connecting Office MCP server to main network...
set _net=
docker network inspect virtualai_default >nul 2>nul
if !errorlevel! equ 0 (
    set _net=virtualai_default
) else (
    docker network inspect onyx_default >nul 2>nul
    if !errorlevel! equ 0 (
        set _net=onyx_default
    )
)
if not defined _net (
    echo   Main network does not exist yet — skipping. Run 'dev up' first.
    goto :eof
)
docker network connect !_net! office-mcp-server 2>nul
if !errorlevel! equ 0 (
    echo   Connected office-mcp-server to !_net! network
) else (
    echo   office-mcp-server already connected to !_net! network
)
goto :eof

:: ==================== USAGE ====================
:usage
echo.
echo   Onyx Dev Helper
echo   ===============
echo.
echo   Usage: dev.bat [command] [services...]
echo.
echo   Commands:
echo     up                    Start all services (detached), including MCP servers
echo     up log                Start all with live logs (foreground)
echo     up log app            Start app services with live logs
echo     up log infra          Start infra with live logs
echo     up log office         Start Office MCP server with live logs
echo     up log api            Start api_server with live logs
echo     up infra              Start infrastructure only (db, vespa, redis, models, minio)
echo     up app                Start app only (api, background, web, nginx)
echo     up office             Start Office MCP server only (PPT + DOCX + PDF)
echo     up api web ...        Start specific services
echo     down                  Stop all services (including MCP servers)
echo     down-v                Stop all services and remove volumes
echo     build                 Build and start all services (including MCP servers)
echo     build infra           Build and start infrastructure only
echo     build app             Build and start app services only
echo     build api             Build and start api_server only
echo     build web             Build and start web_server only
echo     build office          Build and start Office MCP server only
echo     build web api         Build and start both web + api
echo     build background      Build and start background worker
echo     build model           Build and start model servers
echo     restart               Restart all services (including MCP servers)
echo     restart infra         Restart infrastructure only
echo     restart app           Restart app services only
echo     restart api           Restart api_server
echo     restart web           Restart web_server
echo     restart office        Restart Office MCP server
echo     restart api web       Restart both api + web
echo     stop                  Stop all services (without removing)
echo     stop app              Stop app services only
echo     stop api              Stop api_server only
echo     stop office           Stop Office MCP server only
echo     stop web              Stop web_server only
echo     logs                  Tail logs for all services
echo     logs app              Tail logs for app services
echo     logs infra            Tail logs for infrastructure
echo     logs api              Tail logs for api_server
echo     logs web              Tail logs for web_server
echo     logs office           Tail logs for Office MCP server
echo     ps                    Show running containers (all + MCP)
echo.
echo   Groups:
echo     infra      = db, vespa, redis, model servers, minio, code-interpreter, smartsearch, phoenix
echo     app        = api_server, background, web_server, nginx
echo     search     = smartsearch (Perplexica AI web search)
echo     phoenix    = Phoenix LLM observability (dashboard at http://localhost:3000/phoenix/)
echo     office     = Office MCP server (PPT + DOCX + PDF generation via MCP)
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
echo     search     = smartsearch (Perplexica AI web search)
echo     smartsearch = smartsearch (alias for search)
echo     phoenix    = phoenix (LLM observability, http://localhost:3000/phoenix/)
echo     office     = office-mcp-server (PPT + DOCX + PDF, separate compose)
echo     ppt        = alias for office
echo     docx       = alias for office
echo.
echo   Notes:
echo     The Office MCP server runs from office-mcp-server/docker-compose.yml
echo     (separate compose project). On 'dev up' and 'dev build', it is auto-started
echo     and connected to the onyx_default Docker network so the API server can
echo     reach it at http://office-mcp-server:8100/mcp.
echo     It provides 91 tools: 37 PPT (ppt_*) + 54 DOCX (docx_*) including PDF.
echo.

:end
endlocal
