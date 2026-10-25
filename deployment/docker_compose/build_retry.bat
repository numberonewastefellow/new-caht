@echo off
setlocal enabledelayedexpansion
REM Build compose services, retrying on transient network failures (npm / pip registry timeouts).
REM Usage: build_retry.bat "<compose args, e.g. -p virtualai -f docker-compose.yml>" service [service ...]
REM Env:   BUILD_ATTEMPTS (default 3), BUILD_RETRY_DELAY seconds (default 15)
if "%~2"=="" (echo usage: %~nx0 "compose args" service [service ...] & exit /b 2)
if "%BUILD_ATTEMPTS%"=="" set BUILD_ATTEMPTS=3
if "%BUILD_RETRY_DELAY%"=="" set BUILD_RETRY_DELAY=15
set COMPOSE_ARGS=%~1
shift
:next_service
if "%~1"=="" exit /b 0
set SVC=%~1
set N=1
:attempt
docker compose %COMPOSE_ARGS% build %SVC%
if not errorlevel 1 goto built
if !N! GEQ %BUILD_ATTEMPTS% (echo build of %SVC% failed after %BUILD_ATTEMPTS% attempts 1>&2 & exit /b 1)
echo build of %SVC% failed (attempt !N!/%BUILD_ATTEMPTS%), retrying in %BUILD_RETRY_DELAY%s... 1>&2
set /a N+=1
timeout /t %BUILD_RETRY_DELAY% /nobreak >nul
goto attempt
:built
shift
goto next_service
