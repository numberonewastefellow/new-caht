@echo off
setlocal

:: Creates a certificate this machine trusts for https://localhost, using mkcert.
:: Let's Encrypt can't issue for localhost; init-letsencrypt.sh is the production path.
:: The files stay on this machine: deployment/data/sslcerts/ is gitignored.

set CERT_DIR=%~dp0..\data\sslcerts
:: Browsers use the Windows store. Without this, mkcert also tries Java's keystore when Java
:: is installed, which needs admin rights and fails the install.
set TRUST_STORES=system

call :find_mkcert
if errorlevel 1 (
    echo mkcert not found, installing it with winget...
    winget install --id FiloSottile.mkcert --exact --accept-source-agreements --accept-package-agreements
    if errorlevel 1 exit /b 1
    call :find_mkcert
    if errorlevel 1 (
        echo mkcert is installed but not on PATH yet. Open a new terminal and run this again.
        exit /b 1
    )
)

echo.
echo Adding the mkcert certificate authority to this machine's trusted list.
echo Windows may ask you to confirm: choose Yes.
mkcert -install
if errorlevel 1 exit /b 1

if not exist "%CERT_DIR%" mkdir "%CERT_DIR%"
mkcert -cert-file "%CERT_DIR%\ssl.crt" -key-file "%CERT_DIR%\ssl.key" localhost 127.0.0.1 ::1
if errorlevel 1 exit /b 1

echo.
echo Certificate created in %CERT_DIR%
goto :eof

:find_mkcert
where mkcert >nul 2>&1 && exit /b 0
:: winget changes PATH for new terminals only, so look where it installs packages.
for /d %%d in ("%LOCALAPPDATA%\Microsoft\WinGet\Packages\FiloSottile.mkcert_*") do set "PATH=%%~d;%PATH%"
where mkcert >nul 2>&1
exit /b %errorlevel%
