# RetroViewer Launcher Script for PowerShell
# Quick access to all RetroViewer applications

# Get script directory and stay in root folder
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Check if Python is available
try {
    $null = python --version
} catch {
    Write-Host "Error: Python is not installed or not in PATH" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Check and install dependencies
Write-Host "Checking dependencies..." -ForegroundColor Cyan
try {
    $null = python -c "import vlc, mutagen, tkinter" 2>&1
    Write-Host "✓ All dependencies present" -ForegroundColor Green
} catch {
    Write-Host ""
    Write-Host "⚠️  Missing dependencies detected!" -ForegroundColor Yellow
    Write-Host "Installing required packages..." -ForegroundColor Yellow
    python Utilities\install_dependencies.py
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error: Failed to install dependencies" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    Write-Host "✓ Dependencies installed successfully" -ForegroundColor Green
}
Write-Host ""

# Function to check if there's existing data that needs migration
function Test-HasExistingData {
    # Check for old directory structure (at root level)
    if ((Test-Path "Playlist") -or (Test-Path "TimeStamps") -or (Test-Path "Settings") -or (Test-Path "VideoFiles") -or (Test-Path "MediaFiles")) {
        return $true
    }
    
    return $false
}

# Check database on startup
if (-not (Test-Path "Database\retroviewer.db")) {
    # Check if there's existing data to migrate
    if (Test-HasExistingData) {
        # Existing installation - prompt for migration
        Write-Host ""
        Write-Host "⚠️  Database Setup Required" -ForegroundColor Yellow
        Write-Host "================================" -ForegroundColor Cyan
        Write-Host "RetroViewer requires a database to function."
        Write-Host "This will initialize your database and import any existing data."
        Write-Host ""
        Write-Host "Options:"
        Write-Host "  1) Initialize Database Now" -ForegroundColor Green
        Write-Host "  2) Cancel" -ForegroundColor Red
        Write-Host ""
        $dbChoice = Read-Host "Enter choice [1-2]"
        
        switch ($dbChoice) {
            '1' {
                Write-Host ""
                Write-Host "Initializing database..." -ForegroundColor Green
                python Utilities\setup_database.py
                Write-Host ""
                Read-Host "Press Enter to continue"
            }
            '2' {
                Write-Host "Operation cancelled." -ForegroundColor Red
                exit 0
            }
            default {
                Write-Host "Invalid choice. Cancelling." -ForegroundColor Red
                exit 1
            }
        }
    } else {
        # New installation - auto-create database silently
        Write-Host "Initializing database for first-time setup..." -ForegroundColor Cyan
        python Utilities\setup_database.py --auto
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Error: Failed to initialize database" -ForegroundColor Red
            Read-Host "Press Enter to exit"
            exit 1
        }
        Write-Host "✓ Database initialized successfully" -ForegroundColor Green
        Write-Host ""
    }
}

function Show-Menu {
    Clear-Host
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host "    RetroViewer Launcher" -ForegroundColor Cyan
    Write-Host "================================" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "Select an option:"
    Write-Host "  1) Manager (Recommended)" -ForegroundColor Green
    Write-Host "  2) Media Player (Commercials)"
    Write-Host "  3) Feature Player (Movies + Breaks)"
    Write-Host "  4) Stream Server (M3U/XMLTV)"
    Write-Host "  5) Exit" -ForegroundColor Red
    Write-Host ""
}

do {
    Show-Menu
    $choice = Read-Host "Enter choice [1-5]"
    
    switch ($choice) {
        '1' {
            Write-Host ""
            Write-Host "Launching Manager..." -ForegroundColor Green
            python Scripts\Manager.py
            break
        }
        '2' {
            Write-Host ""
            Write-Host "Launching Media Player..." -ForegroundColor Green
            python Scripts\MediaPlayer.py
            break
        }
        '3' {
            Write-Host ""
            Write-Host "Launching Feature Player..." -ForegroundColor Green
            python Scripts\FeaturePlayer.py
            break
        }
        '4' {
            Write-Host ""
            Write-Host "Launching Stream Server..." -ForegroundColor Green
            python Scripts\StreamServer.py
            break
        }
        '5' {
            Write-Host "Goodbye!" -ForegroundColor Cyan
            exit 0
        }
        default {
            Write-Host "Invalid choice" -ForegroundColor Red
            Start-Sleep -Seconds 2
        }
    }
} while ($choice -ne '1' -and $choice -ne '2' -and $choice -ne '3' -and $choice -ne '4' -and $choice -ne '5')
