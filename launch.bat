@echo off
REM RetroViewer Launcher Script for Windows
REM Quick access to all RetroViewer applications

cd /d "%~dp0"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo Error: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check and install dependencies
echo Checking dependencies...
python -c "import vlc, mutagen, tkinter" >nul 2>&1
if errorlevel 1 (
    echo.
    echo WARNING: Missing dependencies detected!
    echo Installing required packages...
    python Utilities\install_dependencies.py
    if errorlevel 1 (
        echo Error: Failed to install dependencies
        pause
        exit /b 1
    )
    echo Dependencies installed successfully
) else (
    echo All dependencies present
)
echo.

REM Check database on startup
if not exist "Database\retroviewer.db" (
    REM Check if there's existing data to migrate
    set HAS_DATA=0
    
    REM Check for old directory structure (at root level)
    if exist "Playlist" set HAS_DATA=1
    if exist "TimeStamps" set HAS_DATA=1
    if exist "Settings" set HAS_DATA=1
    if exist "VideoFiles" set HAS_DATA=1
    if exist "MediaFiles" set HAS_DATA=1
    
    if "!HAS_DATA!"=="1" (
        REM Existing installation - prompt for migration
        echo.
        echo Database Setup Required
        echo ================================
        echo RetroViewer requires a database to function.
        echo This will initialize your database and import any existing data.
        echo.
        echo Options:
        echo   1^) Initialize Database Now
        echo   2^) Cancel
        echo.
        set /p db_choice="Enter choice [1-2]: "
        
        if "!db_choice!"=="1" (
            echo.
            echo Initializing database...
            python Utilities\setup_database.py
            if errorlevel 1 (
                REM Migration was cancelled or failed - exit to prompt
                exit /b 1
            )
            echo.
            pause
        ) else if "!db_choice!"=="2" (
            echo Operation cancelled.
            exit /b 0
        ) else (
            echo Invalid choice. Cancelling.
            exit /b 1
        )
    ) else (
        REM New installation - auto-create database silently
        echo Initializing database for first-time setup...
        python Utilities\setup_database.py --auto
        if errorlevel 1 (
            echo Error: Failed to initialize database
            pause
            exit /b 1
        )
        echo Database initialized successfully
        echo.
    )
)

:menu
cls
echo ================================
echo     RetroViewer Launcher
echo ================================
echo.
echo Select an option:
echo   1) Manager (Recommended)
echo   2) Media Player (Commercials)
echo   3) Feature Player (Movies + Breaks)
echo   4) Stream Server (M3U/XMLTV)
echo   5) Exit
echo.
set /p choice="Enter choice [1-5]: "

if "%choice%"=="1" goto manager
if "%choice%"=="2" goto mediaplayer
if "%choice%"=="3" goto featureplayer
if "%choice%"=="4" goto streamserver
if "%choice%"=="5" goto end
echo Invalid choice
timeout /t 2 >nul
goto menu

:manager
echo.
echo Launching Manager...
python Scripts\Manager.py
goto end

:mediaplayer
echo.
echo Launching Media Player...
python Scripts\MediaPlayer.py
goto end

:featureplayer
echo.
echo Launching Feature Player...
python Scripts\FeaturePlayer.py
goto end

:streamserver
echo.
echo Launching Stream Server...
python Scripts\StreamServer.py
goto end

:end
exit /b 0
