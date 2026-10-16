@echo off
setlocal enabledelayedexpansion
title bytesint.xyz - OSINT Platform

echo ========================================================
echo        bytesint.xyz - OSINT Platform Launcher
echo ========================================================
echo.

:: Verifica se node e npm sono nel PATH, altrimenti usa la cartella di Laragon
where node >nul 2>&1
if errorlevel 1 (
    echo [INFO] Configurazione percorso Node.js...
    set "PATH=C:\laragon\bin\nodejs\node-v22;%PATH%"
)

where node >nul 2>&1
if errorlevel 1 (
    echo [ERRORE] Node.js non trovato. Assicurati che Node.js sia installato.
    pause
    exit /b 1
)

:: Verifica se node_modules esiste
if not exist "node_modules\" (
    echo [INFO] Cartella node_modules mancante. Installazione dipendenze in corso...
    call npm install
    if errorlevel 1 (
        echo [ERRORE] Errore durante npm install.
        pause
        exit /b 1
    )
)

:: Libera la porta 5173 se gia occupata da un processo precedente
powershell -NoProfile -Command "Get-NetTCPConnection -LocalPort 5173 -State Listen -ErrorAction SilentlyContinue | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }" >nul 2>&1

echo [OK] Dominio di Produzione: https://bytesint.xyz
echo [OK] Server Locale di Sviluppo: http://localhost:5173
echo.
echo Premi CTRL+C nella finestra per arrestare il server locale.
echo.

call npm run dev -- --open

if errorlevel 1 (
    echo.
    echo [ERRORE] Il server si e' interrotto con un errore.
    pause
)
