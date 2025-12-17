# Migration Script Update - December 15, 2025

## Overview
Updated `Utilities/setup_database.py` to handle **two-phase migration** for users upgrading from old RetroViewer versions.

## What Changed

### Phase 1: Directory Structure Migration (NEW)
The migration script now detects and migrates old directory structures to the new Data/ layout:

**Old Layout (Root Level):**
```
RetroViewer/
├── Playlist/
├── TimeStamps/
├── Settings/
├── VideoFiles/
└── MediaFiles/
```

**New Layout (Data/ Directory):**
```
RetroViewer/
└── Data/
    ├── Playlists/
    ├── Timestamps/
    ├── Settings/
    ├── VideoFiles/
    └── MediaFiles/
```

### Phase 2: Database Migration (Enhanced)
After directory migration, the script proceeds with database migration from text files as before.

## Key Features

### 1. Automatic Detection
- Script automatically detects if old directory structure exists
- Prompts user before making any changes
- Shows exactly what will be migrated

### 2. Safe Migration
- Uses `shutil.move()` for efficient file operations
- Handles merging if destination directories already exist
- Preserves existing files in destination (won't overwrite)
- Removes old directories only after successful migration

### 3. User Confirmation
- Always asks for confirmation before directory migration
- Shows clear migration plan before proceeding
- Allows user to cancel at any time

### 4. Error Handling
- Reports any errors during migration
- Shows which files were copied/merged
- Lists any directories that couldn't be removed
- Continues with database migration only if directory migration succeeds

## Implementation Details

### New Functions
1. **`check_old_directory_structure()`**
   - Scans for old directories at root level
   - Returns list of directories that need migration

2. **`migrate_directory_structure()`**
   - Prompts user for confirmation
   - Creates Data/ directory if needed
   - Migrates each directory with merge support
   - Removes old directories after successful migration
   - Returns True/False based on success

### Updated Paths
All path constants now reference both old and new structures:
```python
# New directory structure (Data/)
VIDEO_FOLDER = os.path.join(DATA_DIR, "VideoFiles")
MEDIA_FOLDER = os.path.join(DATA_DIR, "MediaFiles")
PLAYLIST_DIR = os.path.join(DATA_DIR, "Playlists")
TIMESTAMPS_DIR = os.path.join(DATA_DIR, "Timestamps")
SETTINGS_DIR = os.path.join(DATA_DIR, "Settings")

# Old directory structure (root level)
OLD_VIDEO_FOLDER = os.path.join(BASE_DIR, "VideoFiles")
OLD_MEDIA_FOLDER = os.path.join(BASE_DIR, "MediaFiles")
OLD_PLAYLIST_DIR = os.path.join(BASE_DIR, "Playlist")
OLD_TIMESTAMPS_DIR = os.path.join(BASE_DIR, "TimeStamps")
OLD_SETTINGS_DIR = os.path.join(BASE_DIR, "Settings")
```

### Updated main() Flow
```
1. Display migration info
2. Check for old directory structure
3. If old structure found:
   a. Prompt user
   b. Migrate directories to Data/
   c. Remove old directories
   d. Show migration summary
4. Proceed with database migration
5. Show final summary and next steps
```

## Migration Examples

### Example 1: Fresh Installation (No Old Structure)
```
✓ No old directory structure found - already using new Data/ layout
Proceeding with database migration...
```

### Example 2: Old Structure Exists
```
⚠️  OLD DIRECTORY STRUCTURE DETECTED
Found: Playlist/, TimeStamps/, Settings/, VideoFiles/, MediaFiles/

This will migrate your files to the new Data/ structure:
  Playlist/     → Data/Playlists/
  TimeStamps/   → Data/Timestamps/
  Settings/     → Data/Settings/
  VideoFiles/   → Data/VideoFiles/
  MediaFiles/   → Data/MediaFiles/

Proceed with directory migration? (yes/no): yes

✓ Created Data/ directory
Migrating Playlists...
  ✓ Moved: Playlist/ → Data/Playlists/
Migrating Timestamps...
  ✓ Moved: TimeStamps/ → Data/Timestamps/
[...]
✓ Directory structure migration completed successfully!
```

### Example 3: Merge Scenario
```
Migrating Playlists...
  Warning: Data/Playlists/ already exists
  Merging contents from Playlist/...
    Copied: file_list.txt
    Copied: 1990's Christmas.txt
    Skipped (exists): AfternoonPlaylist.txt
```

## Testing Recommendations

### Before Running
1. Backup your RetroViewer directory
2. Note which directories exist at root level
3. Check if Data/ directory already exists

### After Running
1. Verify all files moved to Data/ directory
2. Confirm old directories removed
3. Test database creation/update
4. Use Manager.py Video Scanner tab to verify video scanning
5. Test Media Player and Feature Player

## Backup Location
Backup created before changes: `Backups/20251215_233141_migration_update/`

## Related Files Updated
- `Utilities/setup_database.py` - Main setup & migration script (793 lines)
- `.github/copilot-instructions.md` - Updated migration documentation

## Next Steps for Users

### If Upgrading from Old Version
1. Run: `python3 Utilities/setup_database.py`
2. Follow prompts to migrate directory structure
3. Complete database migration
4. Verify all files in Data/ directory
5. Delete old backup folders if satisfied

### If Fresh Installation
1. Run: `python3 Utilities/setup_database.py`
2. Script will detect no old structure and proceed with database setup
3. Add videos to Data/VideoFiles/
4. Use Manager.py Video Scanner tab to scan videos

## Compatibility

### Supported Upgrade Paths
- Old structure (root level) → New structure (Data/)
- Text files → SQLite database
- Combined migration (both phases)

### Not Breaking Changes
- Existing Data/ structure is preserved
- Database incremental migration still works
- Manual import/export via Manager.py unchanged

## Technical Notes

### Import Changes
Added `shutil` module for safe file operations:
```python
import shutil  # For directory migration
```

### Path Resolution
All relative paths now use `Data/` prefix:
```python
relative_path = os.path.join("Data", "VideoFiles", filename)
```

### Error Recovery
If directory migration fails:
- Old directories are NOT removed
- Database migration is SKIPPED
- User can fix issues and re-run

## Documentation Updates

### Updated Sections
1. Migration Script Maintenance - Added two-phase migration details
2. Migration History - Added new entries for directory migration
3. Critical Implementation Details - Added directory migration first rule

### New Documentation
- This file: `Docs/MIGRATION_SCRIPT_UPDATE.md`
