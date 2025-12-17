# RetroViewer AI Coding Agent Instructions

## Project Overview
RetroViewer is a Python-based retro video/commercial player designed to recreate the TV watching experience with feature films interrupted by period-appropriate commercials. Think streaming service meets 1990s TV nostalgia.

**Core Architecture:**
- **SQLite database** (`retroviewer.db`) - Single source of truth for all metadata, playlists, and settings
- **VLC player** (`python-vlc`) - Video playback engine (planned for replacement)
- **Mutagen library** - MP4 metadata (©nam, ©too, ©day, ©gen atoms)
- **Tkinter** - GUI framework for Manager and player overlays
- **Three modes:** Media Player (commercials), FeaturePlayer (movies + commercial breaks), Manager (management GUI)

**⚠️ CRITICAL: Database is REQUIRED**
RetroViewer now REQUIRES the SQLite database for all operations. Text files are NO LONGER supported.
Run `python3 Utilities/setup_database.py` ONCE to set up database and migrate existing data.
After migration, text files are RETIRED and no longer read or written by the system.

## Critical Architecture Patterns

### 1. Database-Only Design
All application state lives in SQLite. **Text files are NO LONGER USED**.

```python
import db_helper  # Always use this for data access

# Get videos from database (NO text file fallback)
videos = db_helper.get_all_videos()
playlist_videos = db_helper.get_playlist_videos("1990's Christmas")
setting = db_helper.get_setting("active_playlist", "All Videos")
```

**Key Files:**
- `db_helper.py` - Database access layer with 20+ functions (ALWAYS use this, never raw SQL in app code)
- `database_schema.sql` - Schema definition (7 tables)
- `setup_database.py` - Database setup and migration script (handles directory migration + database creation)

**Database-Only Operations:**
- `MediaPlayer.py` - Reads playlists ONLY from database
- `FeaturePlayer.py` - Reads timestamps ONLY from database
- `Manager.py` - All operations use database, can import from text files manually

**Text File Status:**
- ❌ NO automatic reading from text files
- ❌ NO automatic writing to text files
- ✓ Manual import via Manager.py (one-way, user-initiated)
- ✓ Manual export via Manager.py (for archival/backup only)

### 2. Relative Path Storage (Portability)
Database stores **relative paths** (`VideoFiles/video.mp4`), scripts convert to absolute at runtime:

```python
# Database stores: "VideoFiles/Big Lots - Halloween, 1997.mp4"
relative_path = video['file_path']  # from database
absolute_path = db_helper.get_absolute_path(relative_path)  # for file access
```

**Never hardcode absolute paths.** Use `os.path.join(script_dir, "VideoFiles")` pattern.

### 3. Dual Metadata Storage
Video metadata exists in **both** MP4 files and database. When updating:

```python
# Update MP4 file atoms
update_metadata(file_path, title="New Title", tags="Holiday,1990s")

# Update database record
db_helper.update_video_metadata(filename, title="New Title", tags="Holiday,1990s")
```

This ensures consistency and allows filtering without reading every MP4 file.

### 4. MP4 Metadata Atoms
Mutagen uses Apple-style atoms (NOT ID3 tags):
- `©nam` - Title
- `©too` - Tags (comma-separated, used for Manager filtering)
- `©day` - Year (stored as "YYYY" or full date)
- `©gen` - Genre

## Component Relationships

```
Manager.py → GUI for filtering/tagging → Updates MP4 + database
         → Creates new playlists → Manual import/export
         → Adds videos to database manually
                                    ↓
MediaPlayer.py → Reads database playlists → Plays videos from VideoFiles/
                                    ↓
FeaturePlayer.py → Reads feature movies from MediaFiles/ + timestamps
                 → Reads Now Playing queue from database
                 → Inserts commercials from playlists at break points
```

## Key Player Behaviors

### Media Player (Commercials Only)
- Plays videos from selected playlist in order or shuffled
- Separate shuffle setting: `media_player_shuffle` (database)
- Fullscreen with black background, hidden cursor
- Toast notifications for playlist changes (top-right)
- Keyboard shortcuts:
  - `Left/Right` = previous/next video
  - `Up/Down` = previous/next playlist
  - `S` = toggle shuffle
  - `R` = reshuffle order
  - `Esc` = exit

### FeaturePlayer (Movies + Commercial Breaks)
- Plays feature movies from `MediaFiles/` with commercials inserted at timestamps
- Reads commercial break times from `timestamps` table in database
- Reads Now Playing queue from `now_playing_queue` table in database
- Uses `ads_per_break` setting (default: 3 commercials per break)
- Pulls commercials from playlist specified in `feature_playlist` setting
- Separate shuffle setting: `feature_player_shuffle` (database)
- Keyboard shortcuts:
  - `Left/Right` = skip ads (during commercial breaks)
  - `Up/Down` = skip movies (in Now Playing queue)
  - `S` = toggle shuffle
  - `R` = reshuffle order
  - `Esc` = exit

### Manager (GUI)
- **Cannot run in dev container** (requires display)
- Filters by Tags/Year/Genre (case-insensitive substring matching)
- Double-click row to edit metadata inline
- Create playlists from filtered results (database entries)
- Manual import/export for text files (archival/backup only)

## Development Workflows

### Adding New Videos
```bash
# 1. Extract/copy MP4 files to Data/VideoFiles/
# 2. Use Manager.py to add videos to database
#    - Open Manager.py GUI
#    - Use "Import from Files" to scan and add new videos
#    - Videos are added to database with metadata from MP4 files
```

### Testing Database Operations
```python
# Quick validation
import db_helper
print(f"Videos: {len(db_helper.get_all_videos())}")  # Should be 442
print(f"Playlists: {len(db_helper.list_playlists())}")  # Should be 14
```

### Running Players (Requires Display)
```bash
# Media Player (commercials)
python3 MediaPlayer.py

# Feature Player (movies + breaks)
python3 FeaturePlayer.py

# Manager (GUI)
python3 Manager.py
```

### Database Schema Changes
1. Update `database_schema.sql`
2. Update `db_helper.py` functions
3. Update `setup_database.py` if needed
4. Re-run migration or write ALTER TABLE script
5. Update all scripts using affected tables

## Common Patterns

### Playlist Creation
```python
# Use Manager.py or direct database operations
db_helper.create_playlist("Holiday Specials", "Christmas and Halloween content")
# Add videos (position is order in playlist)
for pos, filename in enumerate(filtered_videos, 1):
    db_helper.add_video_to_playlist("Holiday Specials", filename, pos)
# NO automatic text file export - database only
# User can manually export via Manager.py if needed for archival
```

### Settings Management
```python
# All settings are key-value pairs in database
db_helper.set_setting("ads_per_break", "5")
current_playlist = db_helper.get_setting("active_playlist", "All Videos")  # with default

# Separate shuffle settings for each player
media_shuffle = db_helper.get_setting("media_player_shuffle", "OFF")
feature_shuffle = db_helper.get_setting("feature_player_shuffle", "OFF")
```

### Feature Movie + Timestamps
```python
# Load feature movie and commercial break times from database
movie = db_helper.get_feature_movie_by_filename("A Garfield Christmas (1987).mp4")
breaks = db_helper.get_commercial_breaks(movie['id'])  # Returns list of dicts with 'break_time' key
# Access break time: break_data['break_time']
```

## Project Conventions

### File Naming
- Video files: `Product - Description, Year.mp4` (e.g., "McDonald's - Halloween McNugget Buddies, 1993.mp4")
- Playlists: `Descriptive Name.txt` (e.g., "1990's Christmas.txt")
- Feature movies: `Title (Year).mp4` (e.g., "Frosty The Snowman (1989 Print).mp4")

### Code Style
- Use `script_dir = os.path.dirname(os.path.abspath(__file__))` at module level
- Always use `with db_helper.get_db_connection() as conn:` for custom queries
- Window cursor hiding: Try Windows-specific `ctypes` in try/except for cross-platform
- Fullscreen players: `root.attributes("-fullscreen", True)` + `root.config(cursor="none")`

### Dialog Box Centering (REQUIRED)
**All Tkinter popup dialogs MUST be centered in the parent window.**

```python
# Standard pattern for centering dialogs
dialog = tk.Toplevel(self.root)
dialog.title("Dialog Title")
dialog.transient(self.root)
dialog.grab_set()  # Optional: make modal

# Center the dialog
dialog.update_idletasks()
dialog_width = 400  # Set your desired width
dialog_height = 500  # Set your desired height
parent_x = self.root.winfo_rootx()
parent_y = self.root.winfo_rooty()
parent_width = self.root.winfo_width()
parent_height = self.root.winfo_height()
x = parent_x + (parent_width - dialog_width) // 2
y = parent_y + (parent_height - dialog_height) // 2
dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")

# Continue with dialog content...
```

**Why this matters:**
- Ensures consistent UX regardless of parent window position
- Prevents dialogs from appearing off-screen or in unexpected locations
- Makes the application feel more polished and professional

**Always include centering code when creating:**
- `tk.Toplevel()` windows
- Custom dialogs for filters, selections, or data entry
- Export/import dialogs
- Any popup that requires user interaction

### Time Format Normalization (CRITICAL)
**All timestamps MUST be normalized to H:MM:SS.MS format before database storage and display.**

```python
# ALWAYS normalize before saving to database
time_str = self._normalize_time_format("3:18.14")  # Returns "0:03:18.14"
db_helper.add_timestamp(movie_id, start_time, end_time)
db_helper.add_commercial_break(movie_id, break_time)

# ALWAYS normalize when displaying from database
timestamps = db_helper.get_timestamps(movie_id)
display_time = self._normalize_time_format(timestamps[0]['start_time'])
```

**Required format:** `H:MM:SS.MS` (e.g., `0:03:18.14`, `1:23:45.00`)
- Hour: Single digit or more (0, 1, 2...)
- Minute: Always 2 digits (00-59)
- Second: Always 2 digits (00-59)
- Millisecond: Always 2 digits (00-99)

**When to normalize:**
1. Before saving ANY time value to database (start_time, end_time, break_time)
2. When importing from text files (add missing fields like .00 for MS)
3. When displaying times in UI (ensures consistency)
4. After VLC auto-detection of movie duration

**Files implementing normalization:**
- `Manager.py` - `_normalize_time_format()` method (lines ~1760-1780)
- `FeaturePlayer.py` - `_parse_time_token()` handles parsing normalized times
- `setup_database.py` - Normalizes times during migration

### Development Workflow
**After EVERY code change:**
1. Check Pylance for errors/warnings (Problems panel in VS Code)
2. Fix any type errors, missing imports, or undefined variables
3. Test the change if possible (especially for database operations)
4. Verify normalized time format is maintained throughout the flow

### Error Handling
- Missing playlists: Fall back to "All Videos" playlist
- Deleted playlists: Validate playlist existence, fall back to "All Videos" if not found
- Missing videos in playlist: Warn but continue (some videos extracted to nested folders)
- VLC media state: Poll with retries, VLC state changes aren't instant
- Pylance type errors: Use `Optional[type]` for nullable parameters, `# type: ignore` for VLC methods

## Known Issues & Workarounds

1. **Manager needs display** - Cannot run in dev containers or headless environments
2. **VLC dependency** - Windows/Linux only, planned replacement with python-mpv or opencv-python
3. **Nested video folders** - Some zip extractions created subfolders, causing playlist warnings
4. **Text file exports** - Still generated for backward compatibility, database is authoritative

## Migration Script Maintenance

### `setup_database.py` - Database Setup & Migration
This script handles database initialization for new installations AND migration from old directory structures for upgrades. It enables users to migrate from OLD directory structure AND text-file storage to new Data/ structure AND database when upgrading RetroViewer versions. **Always maintain this script** even after migration is complete.

**Two-Phase Migration:**

**Phase 1: Directory Structure Migration (if old layout detected)**
- Detects old directory structure at root level (Playlist/, TimeStamps/, Settings/, VideoFiles/, MediaFiles/)
- Migrates to new Data/ structure:
  - `Playlist/` → `Data/Playlists/`
  - `TimeStamps/` → `Data/Timestamps/`
  - `Settings/` → `Data/Settings/`
  - `VideoFiles/` → `Data/VideoFiles/`
  - `MediaFiles/` → `Data/MediaFiles/`
- Handles merging if destination directories already exist
- Removes old directories after successful migration
- Prompts user for confirmation before proceeding

**Phase 2: Database Migration**
- Migrates videos from `Data/VideoFiles/` → `videos` table
- Migrates playlists from `Data/Playlists/*.txt` → `playlists` + `playlist_videos` tables
- Migrates settings from `Data/Settings/*.txt` → `settings` table (key-value pairs)
- Migrates feature movies from `Data/MediaFiles/` → `feature_movies` table
- Migrates timestamps from `Data/Timestamps/*.txt` → `timestamps` + `commercial_breaks` tables

**Critical implementation details:**
1. **Directory migration first** - Must run before database migration to ensure files are in correct locations

2. **Case-insensitive matching** for timestamp files:
   ```python
   # Handles "Frosty The snowman.txt" matching "Frosty The Snowman.mp4"
   SELECT id FROM feature_movies WHERE LOWER(title) = LOWER(?)
   ```

3. **Relative path storage** - Always store `Data/VideoFiles/file.mp4`, not absolute paths

4. **Timestamp parsing** - Handles both formats:
   - Simple: `03:18.14` (minutes:seconds.milliseconds)
   - Extended: `0:07:00` (hours:minutes:seconds)

5. **Safe file operations** - Uses shutil.move() for directory migration, handles merge conflicts

**When updating database schema:**
1. Update `database_schema.sql`
2. Update `setup_database.py` to handle new tables/columns
3. Update `db_helper.py` functions
4. Test migration on backup of production data
5. Document changes in `DATABASE_MIGRATION.md`

## Migration History
- **Dec 15, 2025** - Migrated from text files to SQLite database
- **Dec 15, 2025** - Fixed paths to be relative for portability
- **Dec 15, 2025** - Fixed case-insensitive timestamp file matching
- **Dec 15, 2025** - Added directory structure migration to handle old layout → Data/ layout
- **Dec 15, 2025** - Migration script now handles both directory AND database migration in two phases
- **Dec 16, 2025** - Separated shuffle settings: `media_player_shuffle` and `feature_player_shuffle`
- **Dec 16, 2025** - Changed default playlist from "file_list" to "All Videos" throughout codebase
- **Dec 16, 2025** - Removed legacy settings (shuffle, timed_play, now_playing) from database
- **Dec 16, 2025** - Added navigation controls: Left/Right for ads, Up/Down for movies in FeaturePlayer
- **Dec 16, 2025** - Removed all text file references from players (database-only operations)
- **Dec 16, 2025** - Fixed all Pylance type errors in db_helper.py and player scripts
- See `MIGRATION_COMPLETE.md`, `DATABASE_MIGRATION.md`, `MIGRATION_NOTES.md` for full details

## Future Plans
1. Replace VLC with cross-platform player (opencv-python or python-mpv)
2. Add web interface for remote control
3. Implement search/filter in players
4. Add scheduled playback (time-of-day playlists)
