# Migration Notes - File Path Changes

**Date:** December 15, 2025  
**Issue:** File paths needed to be relative, not absolute

## Problem
Initial migration stored absolute paths in the database (e.g., `/workspaces/RetroViewer - .053/VideoFiles/video.mp4`). This made the application non-portable - moving the folder would break all file references.

## Solution
All file paths are now stored as **relative paths** in the database:
- Video files: `VideoFiles/filename.mp4`
- Feature movies: `MediaFiles/filename.mp4`

## Implementation Details

### Database Storage
- `videos.file_path` stores paths like: `VideoFiles/640x480.mp4`
- `feature_movies.file_path` stores paths like: `MediaFiles/Frosty The Snowman (1989 Print).mp4`

### Path Resolution
When Python scripts need to access files, they convert relative paths to absolute:
```python
# In db_helper.py
def get_absolute_path(relative_path):
    """Convert relative path to absolute path."""
    if os.path.isabs(relative_path):
        return relative_path
    return os.path.join(SCRIPT_DIR, relative_path)
```

### Updated Scripts
All Python scripts have been updated to handle relative paths:

1. **setup_database.py**
   - Lines 87-95: Stores `os.path.join("VideoFiles", filename)` for videos
   - Lines 230-241: Stores `os.path.join("MediaFiles", filename)` for feature movies

2. **db_helper.py**
   - Added `get_absolute_path()` helper function (lines 12-16)
   - Updated `scan_and_sync_videos()` to store relative paths (line 290-295)

3. **MediaPlayer.py**
   - Already uses `script_dir` to build video paths
   - Constructs full paths with `os.path.join(video_folder, video_name)`

4. **FeaturePlayer.py**
   - Already uses `script_dir` to build media paths
   - Constructs full paths with `os.path.join(media_folder, filename)`

5. **Video Scanner (in Manager.py)**
   - Uses `db_helper.scan_and_sync_videos()` which stores relative paths

6. **Meta Editor.v2.py**
   - Loads from database with relative paths
   - Updates both MP4 files and database

## Benefits
1. **Portability:** Application can be moved to any directory
2. **Cross-platform:** Works on Windows, Linux, macOS with different path separators
3. **Maintainability:** Easier to manage and debug
4. **Flexibility:** Database can be shared between different installations

## Migration
Database has been re-migrated with relative paths. All 442 videos and 2 feature movies now use relative paths.

## Verification
```bash
# Check sample paths in database
python3 << 'EOF'
import sqlite3
conn = sqlite3.connect('retroviewer.db')
cursor = conn.cursor()
cursor.execute("SELECT file_path FROM videos LIMIT 3")
for row in cursor.fetchall():
    print(row[0])
conn.close()
EOF
```

Expected output:
```
VideoFiles/640x480.mp4
VideoFiles/7 Up - 7 Up for the Holidays, 1991.mp4
VideoFiles/7UP - Christmas with Spot, 1988.mp4
```
