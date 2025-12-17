# RetroViewer

**Modified version of the original RetroViewer by [Smashedbrothersgaming](https://geekguilt.com/blogs/news/retro-viewer-wip-release)**

## Table of Contents
- [Overview](#overview)
- [Quick Start](#quick-start)
  - [1. Easy Launch (Recommended)](#1-easy-launch-recommended)
  - [2. Dependencies (Automatic)](#2-dependencies-automatic)
  - [3. Run Manager Directly](#3-run-manager-directly)
  - [4. Run Players Directly](#4-run-players-directly)
  - [5. Docker (StreamServer Only)](#5-docker-streamserver-only)
- [Launchers](#launchers)
- [Data Locations](#data-locations)
  - [Video Files](#video-files)
  - [Database](#database)
  - [Playlists](#playlists)
  - [Settings](#settings)
  - [Timestamps](#timestamps)
- [⚠️ REQUIRED: Database Migration](#️-required-database-migration)
  - [For New Installations](#for-new-installations)
  - [For Existing Installations (Upgrading)](#for-existing-installations-upgrading)
  - [After Migration](#after-migration)
- [Path Updates](#path-updates)
- [Archive](#archive)

## Overview
```
RetroViewer/
├── Scripts/                     # All Python scripts
│   ├── Manager.py               # Main management interface (7 tabs)
│   ├── MediaPlayer.py           # Commercial player
│   ├── FeaturePlayer.py         # Feature movies with commercial breaks
│   ├── StreamServer.py          # IPTV/EPG streaming server
│   └── db_helper.py             # Database operations
│
├── Utilities/                   # Utility scripts
│   ├── install_dependencies.py  # Dependency installer
│   ├── setup_database.py        # Database setup & migration utility
│   └── cache_durations.py       # Video duration caching utility
│
├── Data/                        # All user data files
│   ├── VideoFiles/              # Commercial video files (.mp4)
│   ├── MediaFiles/              # Feature movie files (.mp4)
│   ├── Playlists/               # [RETIRED] Old playlist text files
│   ├── Settings/                # [RETIRED] Old settings text files
│   └── Timestamps/              # [RETIRED] Old timestamp text files
│
├── Database/                    # SQLite database
│   ├── retroviewer.db           # Main database file (REQUIRED)
│   └── database_schema.sql      # Schema definition
│
├── Migration Logs/              # Migration log files
│   ├── setup_database_*.log     # Main migration logs
│   └── missing_videos_*.txt     # Missing video reports
│
├── Archive/                     # Archived files
│   ├── migration_*/             # Old directories/scripts from migration
│   └── Standalone Tools/        # Legacy standalone scripts
│
├── Docs/                        # Documentation
├── Docker/                      # Docker configuration for StreamServer
│
├── README.md                    # This file
├── launch.sh                    # Launcher script (Linux/Mac)
├── launch.bat                   # Launcher script (Windows Batch)
├── launch.ps1                   # Launcher script (Windows PowerShell)
└── requirements.txt             # Python dependencies
```

## Quick Start

### 1. Easy Launch (Recommended)

Use the launcher scripts for your platform:

**Linux/Mac:**
```bash
./launch.sh
```

**Windows (PowerShell - Recommended):**
```powershell
.\launch.ps1
```

**Windows (Batch):**
```batch
launch.bat
```

The launcher automatically:
- **Checks and installs dependencies** on startup
- **Checks for database** before launching players
- **Prompts migration** if database missing

Menu options:
1. Manager (Recommended)
2. Media Player (Commercials)
3. Feature Player (Movies + Breaks)
4. Exit

### 2. Dependencies (Automatic)

**Dependencies are installed automatically** when you run any launcher!

The launcher checks for required packages and installs them if missing:
- `python-vlc` - Video playback
- `mutagen` - MP4 metadata
- `tkinter` - GUI framework (system package on Linux)

Manual installation (if needed):
```bash
python3 Utilities/install_dependencies.py
# or
pip install -r requirements.txt
```

### 3. Run Manager Directly

```bash
cd Scripts
python3 Manager.py
```

Manager provides 7 tabs:
- **Video Metadata** - Edit video metadata, filter, export playlists, view duration
- **Video Scanner** - Scan VideoFiles directory and sync database
- **Playlists** - Create/edit playlists, reorder videos
- **Tags & Genres** - Manage tags and genres
- **Commercial Breaks** - Set timestamps for feature movies
- **Now Playing** - Manage feature movie queue
- **Settings** - Configure application settings

### 4. Run Players Directly
```bash
cd Scripts
python3 MediaPlayer.py           # Commercial player
python3 FeaturePlayer.py         # Feature movies with breaks
```

### 5. Docker (StreamServer Only)

For running the IPTV/EPG StreamServer in a container:

```bash
cd Docker
docker-compose up -d
# Access at http://localhost:5000
```

See [docker/README.md](docker/README.md) for full documentation.

**Note:** GUI applications (Manager, Media Player, Feature Player) should run directly on your host system, not in Docker.

## Launchers

Three launcher scripts are provided for easy access:

| Launcher | Platform | Description |
|----------|----------|-------------|
| `launch.sh` | Linux/Mac | Bash script with interactive menu |
| `launch.bat` | Windows | Batch file for Command Prompt |
| `launch.ps1` | Windows | PowerShell script (recommended for Windows) |

**Launcher Features:**
- ✓ Automatic dependency checking and installation
- ✓ Database validation before launching players
- ✓ Automatic migration prompt if database missing

**Menu Options:**
1. Manager (Recommended) - Full management interface
2. Media Player - Play commercial videos
3. Feature Player - Play movies with commercial breaks
4. Exit

## Data Locations

### Video Files
- **Commercials**: `Data/VideoFiles/` - Short commercial clips (.mp4)
- **Movies**: `Data/MediaFiles/` - Full-length feature movies (.mp4)

### Database
- **Location**: `Database/retroviewer.db`
- **Schema**: `Database/database_schema.sql`

### Playlists
- **Storage**: Database (playlists and playlist_videos tables)
- **Text Files**: RETIRED - no longer used by the system

### Settings
- **Storage**: Database (settings table)
- **Text Files**: RETIRED - no longer used by the system

### Timestamps
- **Storage**: Database (timestamps and commercial_breaks tables)
- **Text Files**: RETIRED - no longer used by the system

## ⚠️ REQUIRED: Database Migration

**⚠️ CRITICAL:** RetroViewer now REQUIRES the SQLite database to function.
Text files are NO LONGER supported for automatic operations.

### For New Installations:
1. Database will be created automatically on first run
2. Use Manager.py to populate data

### For Existing Installations (Upgrading):
**Migration happens automatically!** When you launch any player without a database, you'll be prompted:

```
⚠️  Database Setup Required
RetroViewer requires a database to function.

Options:
  1) Initialize Database Now
  2) Cancel
```

Or run manually:
```bash
python3 Utilities/setup_database.py
```

This is a **ONE-TIME** process that:
- **Phase 1: Directory Migration**
  - Migrates old directory structure to new Data/ layout
  - Archives old directories to Archive/migration_*/ folder
  - Moves old Python scripts to archive
- **Phase 2: Database Migration**
  - Converts all playlist .txt files to database
  - Converts all timestamp .txt files to database
  - Converts all settings .txt files to database
  - Creates "All Videos" master playlist
  - Extracts tags and genres for filtering
- **Phase 3: Cleanup**
  - Moves log files to Migration Logs/ folder
  - Creates detailed missing videos report
  - After migration, **text files are NO LONGER USED**

### After Migration:
- ✓ Database is the ONLY data source
- ✓ Players read ONLY from database (no text file fallback)
- ✓ Old directories archived in Archive/migration_*/ folder
- ✓ Old scripts archived (FeaturePlayer.v2.py, Media Player.py, etc.)
- ✓ Migration logs saved to Migration Logs/ folder
- ✓ Missing videos report generated for reference
- ✓ Manager.py can still IMPORT from .txt files if needed (one-way)
- ✗ System will NOT create or update .txt files automatically
- ✗ file_list playlist retired (replaced by "All Videos")

## Path Updates

All scripts now reference:
- `Scripts/` for Python files
- `Data/` for video/playlist/settings data
- `Database/` for SQLite database

**Important**: Run scripts from `Scripts/` directory or they will calculate paths incorrectly.

## Archive

Standalone tools moved to `Archive/Standalone Tools/`:
- Meta Editor.v2.py → Now in Manager.py (Video Metadata tab)
- ReadFileName.py → Now in Manager.py (Video Scanner tab)
- FeaturePlayer.v2.py → Updated copy now in Scripts/FeaturePlayer.py
- Media Player.py → Update copy now in Scripts/MediaPlayer.py
