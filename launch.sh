#!/bin/bash
# RetroViewer Launcher Script
# Quick access to all RetroViewer applications

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR" || exit 1

# Check if Python 3 is available
if ! command -v python3 &> /dev/null; then
    echo "Error: Python 3 is not installed"
    exit 1
fi

# Check and install dependencies
check_dependencies() {
    echo "Checking dependencies..."
    if ! python3 -c "import vlc, mutagen, tkinter" &> /dev/null; then
        echo
        echo "⚠️  Missing dependencies detected!"
        echo "Installing required packages..."
        python3 Utilities/install_dependencies.py
        if [ $? -ne 0 ]; then
            echo "Error: Failed to install dependencies"
            read -p "Press Enter to exit..."
            exit 1
        fi
        echo "✓ Dependencies installed successfully"
    else
        echo "✓ All dependencies present"
    fi
    echo
}

# Check if there's existing data that needs migration
has_existing_data() {
    # Check for old directory structure (at root level)
    if [ -d "Playlist" ] || [ -d "TimeStamps" ] || [ -d "Settings" ] || [ -d "VideoFiles" ] || [ -d "MediaFiles" ]; then
        return 0  # Has old data
    fi
    
    return 1  # No old directories
}

# Check if database exists
check_database() {
    if [ ! -f "Database/retroviewer.db" ]; then
        # Check if there's existing data to migrate
        if has_existing_data; then
            # Existing installation - prompt for migration
            echo
            echo "⚠️  Database Setup Required"
            echo "================================"
            echo "RetroViewer requires a database to function."
            echo "This will initialize your database and import any existing data."
            echo
            echo "Options:"
            echo "  1) Initialize Database Now"
            echo "  2) Cancel"
            echo
            read -p "Enter choice [1-2]: " db_choice
            
            case $db_choice in
                1)
                    echo
                    echo "Initializing database..."
                    python3 Utilities/setup_database.py
                    if [ $? -ne 0 ]; then
                        # Migration was cancelled or failed - exit to prompt
                        exit 1
                    fi
                    echo
                    read -p "Press Enter to continue..."
                    return 0
                    ;;
                2)
                    echo "Operation cancelled."
                    exit 0
                    ;;
                *)
                    echo "Invalid choice. Cancelling."
                    exit 1
                    ;;
            esac
        else
            # New installation - auto-create database silently
            echo "Initializing database for first-time setup..."
            python3 Utilities/setup_database.py --auto
            if [ $? -ne 0 ]; then
                echo "Error: Failed to initialize database"
                read -p "Press Enter to exit..."
                exit 1
            fi
            echo "✓ Database initialized successfully"
            echo
        fi
    fi
}

# Check dependencies on startup
check_dependencies

# Check database on startup before showing menu
check_database

# Main menu
echo "================================"
echo "    RetroViewer Launcher"
echo "================================"
echo
echo "Select an option:"
echo "  1) Manager (Recommended)"
echo "  2) Media Player (Commercials)"
echo "  3) Feature Player (Movies + Breaks)"
echo "  4) Stream Server (M3U/XMLTV)"
echo "  5) Exit"
echo
read -p "Enter choice [1-5]: " choice

case $choice in
    1)
        echo
        echo "Launching Manager..."
        python3 Scripts/Manager.py
        ;;
    2)
        echo
        echo "Launching Media Player..."
        python3 Scripts/MediaPlayer.py
        ;;
    3)
        echo
        echo "Launching Feature Player..."
        python3 Scripts/FeaturePlayer.py
        ;;
    4)
        echo
        echo "Launching Stream Server..."
        python3 Scripts/StreamServer.py
        ;;
    5)
        echo "Goodbye!"
        exit 0
        ;;
    *)
        echo "Invalid choice"
        exit 1
        ;;
esac
