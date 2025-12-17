# Archive Directory

## ⚠️ WARNING: DO NOT USE THESE SCRIPTS

This directory contains archived versions of standalone tools that have been **superseded** by the unified Manager.py interface.

### Archived Tools

These scripts are **outdated** and use **old directory paths** that no longer match the current RetroViewer structure:

- **Meta Editor.v2.py** - Video metadata editor (now integrated as Manager Tab 1)
- **ReadFileName.py** - Video file scanner (now integrated as Manager Tab 3)

### Why They're Archived

1. **Outdated paths**: Reference old `Playlist/`, `VideoFiles/`, etc. instead of `Data/` subdirectories
2. **Functionality integrated**: All features now available in Manager.py with better UI
3. **Database-first**: New system uses SQLite database, these use text files

### Use Manager.py Instead

All functionality from these archived tools is now available in the unified Manager application:

```bash
# Launch Manager from root directory
./launch.sh    # Linux/Mac
./launch.ps1   # Windows PowerShell
./launch.bat   # Windows Command Prompt

# Or run directly
python3 Scripts/Manager.py
```

### Manager Features

- **Tab 1: Video Metadata** - Edit tags, titles, years, genres (replaces Meta Editor.v2.py)
- **Tab 2: Playlists** - Create and manage playlists
- **Tab 3: Video Scanner** - Scan VideoFiles directory (replaces ReadFileName.py)
- **Tab 4: Tags & Genres** - Manage tag/genre lists
- **Tab 5: Commercial Breaks** - Create timestamps for feature movies

---

**These archived scripts are kept for reference only. Do not run them.**
