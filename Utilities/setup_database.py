"""
Migration script to convert text-based data to SQLite database.

⚠️  IMPORTANT: This is a ONE-TIME migration tool for existing installations.
    After running this script, RetroViewer will ONLY use the database.
    Text files in Data/Playlists and Data/Timestamps are now RETIRED.
    
    This script now handles BOTH:
    1. Directory structure migration (old layout → new Data/ layout)
    2. Database migration (text files → SQLite database)
    
    The system no longer reads from or writes to .txt files automatically.
    Only the database is used for all operations.
    
    Text files can still be imported manually via Manager.py if needed,
    but the application will not generate or update them.
    
    Usage:
        python3 setup_database.py           # Interactive mode
        python3 setup_database.py --auto    # Silent mode for new installs
"""

import os
import sys
import sqlite3
import re
import shutil
from datetime import datetime
from mutagen.mp4 import MP4


# Paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # Parent of Utilities/
DB_PATH = os.path.join(BASE_DIR, "Database", "retroviewer.db")

# Log file path
LOG_DIR = os.path.join(BASE_DIR, "Database")
LOG_FILE = os.path.join(LOG_DIR, f"setup_database_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

# Global log file handle
_log_file = None

# New directory structure (Data/)
DATA_DIR = os.path.join(BASE_DIR, "Data")
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


def log_print(message="", to_console=True):
    """Print to both console and log file."""
    global _log_file
    
    if to_console:
        print(message)
    
    if _log_file:
        _log_file.write(message + "\n")
        _log_file.flush()


def init_log():
    """Initialize log file."""
    global _log_file
    
    # Ensure log directory exists
    os.makedirs(LOG_DIR, exist_ok=True)
    
    try:
        _log_file = open(LOG_FILE, 'w', encoding='utf-8')
        log_print(f"RetroViewer Database Setup Log", to_console=False)
        log_print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", to_console=False)
        log_print(f"Log file: {LOG_FILE}", to_console=False)
        log_print("=" * 60, to_console=False)
        log_print("", to_console=False)
        return True
    except Exception as e:
        print(f"Warning: Could not create log file: {e}")
        return False


def close_log():
    """Close log file."""
    global _log_file
    
    if _log_file:
        log_print("", to_console=False)
        log_print("=" * 60, to_console=False)
        log_print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", to_console=False)
        _log_file.close()


def create_data_directory_structure():
    """Create complete Data/ directory structure for new installations."""
    log_print("\nCreating Data/ directory structure...")
    
    directories = [
        (DATA_DIR, "Data/"),
        (VIDEO_FOLDER, "Data/VideoFiles/"),
        (MEDIA_FOLDER, "Data/MediaFiles/"),
        (PLAYLIST_DIR, "Data/Playlists/"),
        (TIMESTAMPS_DIR, "Data/Timestamps/"),
        (SETTINGS_DIR, "Data/Settings/"),
    ]
    
    for dir_path, display_name in directories:
        os.makedirs(dir_path, exist_ok=True)
        log_print(f"  ✓ Created {display_name}")
    
    log_print("✓ Data directory structure ready")
        _log_file = None


def is_new_installation():
    """Detect if this is a new installation vs an upgrade.
    
    New installation = no old directory structure at root level.
    If old directories exist, it's an upgrade that needs migration.
    """
    has_old_structure = any([
        os.path.isdir(OLD_PLAYLIST_DIR),
        os.path.isdir(OLD_TIMESTAMPS_DIR),
        os.path.isdir(OLD_SETTINGS_DIR),
        os.path.isdir(OLD_VIDEO_FOLDER),
        os.path.isdir(OLD_MEDIA_FOLDER)
    ])
    
    # New install: no old structure at root level
    return not has_old_structure


def check_old_directory_structure():
    """Check if old directory structure exists that needs migration."""
    old_dirs_exist = []
    
    if os.path.isdir(OLD_PLAYLIST_DIR):
        old_dirs_exist.append("Playlist/")
    if os.path.isdir(OLD_TIMESTAMPS_DIR):
        old_dirs_exist.append("TimeStamps/")
    if os.path.isdir(OLD_SETTINGS_DIR):
        old_dirs_exist.append("Settings/")
    if os.path.isdir(OLD_VIDEO_FOLDER):
        old_dirs_exist.append("VideoFiles/")
    if os.path.isdir(OLD_MEDIA_FOLDER):
        old_dirs_exist.append("MediaFiles/")
    
    return old_dirs_exist


def migrate_directory_structure():
    """Migrate old directory structure to new Data/ structure."""
    log_print("\n" + "=" * 60)
    log_print("STEP 1: Directory Structure Migration")
    log_print("=" * 60)
    
    old_dirs = check_old_directory_structure()
    
    if not old_dirs:
        log_print("✓ No old directory structure found - already using new Data/ layout")
        return True
    
    log_print(f"Found old directory structure: {', '.join(old_dirs)}")
    log_print("\nThis will migrate your files to the new Data/ structure:")
    log_print("  Playlist/     → Data/Playlists/")
    log_print("  TimeStamps/   → Data/Timestamps/")
    log_print("  Settings/     → Data/Settings/")
    log_print("  VideoFiles/   → Data/VideoFiles/")
    log_print("  MediaFiles/   → Data/MediaFiles/")
    log_print("\nOld directories and scripts will be ARCHIVED for safe keeping.")
    
    response = input("\nProceed with directory migration? (yes/no): ").strip().lower()
    if response not in ['yes', 'y']:
        log_print("✗ Directory migration cancelled by user")
        return False
    
    # Create Data/ directory structure if it doesn't exist
    create_data_directory_structure()
    
    # Create timestamped archive directory first
    archive_dir = os.path.join(BASE_DIR, "Archive")
    os.makedirs(archive_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_subdir = os.path.join(archive_dir, f"migration_{timestamp}")
    os.makedirs(archive_subdir, exist_ok=True)
    
    log_print(f"\n✓ Created archive directory: {archive_subdir}")
    
    migration_success = True
    dirs_to_remove = []
    
    # Migrate each directory
    migrations = [
        (OLD_PLAYLIST_DIR, PLAYLIST_DIR, "Playlists"),
        (OLD_TIMESTAMPS_DIR, TIMESTAMPS_DIR, "Timestamps"),
        (OLD_SETTINGS_DIR, SETTINGS_DIR, "Settings"),
        (OLD_VIDEO_FOLDER, VIDEO_FOLDER, "VideoFiles"),
        (OLD_MEDIA_FOLDER, MEDIA_FOLDER, "MediaFiles"),
    ]
    
    for old_path, new_path, name in migrations:
        if os.path.isdir(old_path):
            try:
                log_print(f"\nMigrating {name}...")
                
                # Step 1: Copy to archive
                archive_path = os.path.join(archive_subdir, os.path.basename(old_path))
                shutil.copytree(old_path, archive_path)
                log_print(f"  ✓ Archived to: Archive/migration_{timestamp}/{os.path.basename(old_path)}/")
                
                # Step 2: Copy/merge to new Data/ location
                if os.path.exists(new_path):
                    log_print(f"  Warning: {new_path} already exists - merging contents")
                    
                    # Merge files
                    for item in os.listdir(old_path):
                        old_item_path = os.path.join(old_path, item)
                        new_item_path = os.path.join(new_path, item)
                        
                        if os.path.isfile(old_item_path):
                            if not os.path.exists(new_item_path):
                                shutil.copy2(old_item_path, new_item_path)
                                log_print(f"  ✓ Copied: {item}")
                            else:
                                log_print(f"  - Skipped (exists): {item}")
                        elif os.path.isdir(old_item_path):
                            if not os.path.exists(new_item_path):
                                shutil.copytree(old_item_path, new_item_path)
                                log_print(f"  ✓ Copied directory: {item}")
                            else:
                                log_print(f"  - Skipped directory (exists): {item}")
                else:
                    # Move to new location
                    shutil.move(old_path, new_path)
                    log_print(f"  ✓ Moved to: {new_path}")
                    continue  # Skip adding to removal list since already moved
                
                # Step 3: Mark for deletion (only if we copied, not moved)
                dirs_to_remove.append(old_path)
                
            except Exception as e:
                log_print(f"  ✗ Error migrating {name}: {e}")
                migration_success = False
    
    if not migration_success:
        log_print("\n✗ Directory migration completed with errors")
        log_print("Please review errors above before proceeding.")
        return False
    
    # Remove old directories after successful archive and migration
    log_print("\n" + "=" * 60)
    log_print("Removing old directories...")
    log_print("=" * 60)
    
    for old_path in dirs_to_remove:
        if os.path.isdir(old_path):
            try:
                shutil.rmtree(old_path)
                log_print(f"✓ Removed: {old_path}")
            except Exception as e:
                log_print(f"  Warning: Could not remove {old_path}: {e}")
    
    # Archive and remove old Python scripts from root directory
    log_print("\n" + "=" * 60)
    log_print("Archiving old Python scripts...")
    log_print("=" * 60)
    
    old_scripts = [
        "FeaturePlayer.v2.py",
        "Media Player.py",
        "Meta Editor.v2.py",
        "ReadFileName.py"
    ]
    
    for script_name in old_scripts:
        script_path = os.path.join(BASE_DIR, script_name)
        if os.path.isfile(script_path):
            try:
                # Copy to archive
                archive_path = os.path.join(archive_subdir, script_name)
                shutil.copy2(script_path, archive_path)
                log_print(f"✓ Archived: {script_name}")
                
                # Remove original
                os.remove(script_path)
                log_print(f"✓ Removed: {script_name}")
            except Exception as e:
                log_print(f"  Warning: Could not archive/remove {script_name}: {e}")
    
    log_print("\n" + "=" * 60)
    log_print("✓ Directory structure migration completed successfully!")
    log_print("=" * 60)
    log_print("\nNew directory structure:")
    for _, new_path, name in migrations:
        if os.path.isdir(new_path):
            file_count = len([f for f in os.listdir(new_path) if os.path.isfile(os.path.join(new_path, f))])
            log_print(f"  {name}: {file_count} files")
    
    return True


def _coerce_first(value, fallback="Unknown"):
    """Mutagen atoms return lists; coerce to clean string."""
    try:
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, bytes):
            value = value.decode(errors="replace")
        value = str(value).strip()
        return value if value else fallback
    except Exception:
        return fallback


def _year_display(s):
    """Normalize date-like strings to a displayable year."""
    s = str(s).strip()
    m = re.match(r"^(\d{4})", s)
    return m.group(1) if m else (s if s else "Unknown")


def get_metadata(file_path):
    """Extract metadata from MP4 file."""
    try:
        mp4_file = MP4(file_path)
        title = _coerce_first(mp4_file.get("\xa9nam", ["Unknown"]))
        genre = _coerce_first(mp4_file.get("\xa9gen", ["Unknown"]))
        year_raw = _coerce_first(mp4_file.get("\xa9day", ["Unknown"]))
        year = _year_display(year_raw)
        tags = _coerce_first(mp4_file.get("\xa9too", ["Unknown"]))
        return title, tags, year, genre
    except Exception as e:
        log_print(f"  Warning: Could not read metadata from {os.path.basename(file_path)}: {e}")
        return "Unknown", "Unknown", "Unknown", "Unknown"


def init_database():
    """Create database and tables from schema."""
    log_print("Initializing database...")
    
    # Read schema file
    schema_path = os.path.join(BASE_DIR, "Database", "database_schema.sql")
    with open(schema_path, 'r') as f:
        schema_sql = f.read()
    
    # Create database
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(schema_sql)
    conn.commit()
    log_print(f"✓ Database created at: {DB_PATH}")
    return conn


def get_video_duration_ffprobe(file_path):
    """Get video duration using ffprobe. Returns None if unable to determine."""
    try:
        import subprocess
        import json
        
        result = subprocess.run(
            [
                'ffprobe', 
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                file_path
            ],
            capture_output=True,
            text=True,
            timeout=2.0,
            check=False
        )
        
        if result.returncode == 0 and result.stdout:
            data = json.loads(result.stdout)
            if 'format' in data and 'duration' in data['format']:
                return float(data['format']['duration'])
    except Exception:
        pass  # ffprobe not available or failed
    
    return None


def migrate_videos(conn, incremental=False):
    """Scan VideoFiles recursively and populate videos table with duration caching."""
    log_print("\nMigrating videos from VideoFiles...")
    log_print("  (Scanning recursively for videos in subdirectories)")
    log_print("  (Detecting video durations with ffprobe for EPG caching)")
    
    if not os.path.isdir(VIDEO_FOLDER):
        log_print(f"  Warning: VideoFiles folder not found at {VIDEO_FOLDER}")
        return
    
    cursor = conn.cursor()
    video_count = 0
    added_count = 0
    skipped_count = 0
    duration_count = 0
    
    # Get existing filenames if incremental
    existing_filenames = set()
    if incremental:
        existing_filenames = set(row[0] for row in cursor.execute("SELECT filename FROM videos").fetchall())
        log_print(f"  (Incremental mode: {len(existing_filenames)} videos already in database)")
    
    # Recursively scan for MP4 files
    for root, dirs, files in os.walk(VIDEO_FOLDER):
        for filename in sorted(files):
            if filename.lower().endswith(".mp4"):
                video_count += 1
                
                # Skip if already exists in incremental mode
                if incremental and filename in existing_filenames:
                    skipped_count += 1
                    continue
                
                file_path = os.path.join(root, filename)
                # Store relative path from base directory
                rel_from_base = os.path.relpath(file_path, BASE_DIR)
                
                title, tags, year, genre = get_metadata(file_path)
                
                # Get duration with ffprobe
                duration = get_video_duration_ffprobe(file_path)
                if duration is not None:
                    duration_count += 1
                
                cursor.execute("""
                    INSERT OR IGNORE INTO videos (filename, title, tags, year, genre, file_path, duration)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (filename, title, tags, year, genre, rel_from_base, duration))
                
                added_count += 1
                if added_count % 50 == 0:
                    log_print(f"  Added {added_count} new videos ({duration_count} with cached durations)...")
    
    conn.commit()
    if incremental:
        log_print(f"✓ Scanned {video_count} videos: {added_count} new, {skipped_count} already in database")
        log_print(f"  ({duration_count}/{added_count} new videos have cached durations)")
    else:
        log_print(f"✓ Migrated {video_count} videos ({duration_count} with cached durations)")


def migrate_playlists(conn, incremental=False):
    """Read playlist text files and populate playlists and playlist_videos tables."""
    log_print("\nMigrating playlists from Playlist/*.txt...")
    
    if not os.path.isdir(PLAYLIST_DIR):
        log_print(f"  Warning: Playlist folder not found at {PLAYLIST_DIR}")
        return
    
    cursor = conn.cursor()
    playlist_count = 0
    skipped_count = 0
    
    # Track all missing videos per playlist for separate log file
    all_missing_videos = {}
    
    # Get existing playlists if incremental
    existing_playlists = set()
    if incremental:
        existing_playlists = set(row[0] for row in cursor.execute("SELECT name FROM playlists").fetchall())
        log_print(f"  (Incremental mode: {len(existing_playlists)} playlists already in database)")
    
    for filename in sorted(os.listdir(PLAYLIST_DIR)):
        if filename.lower().endswith(".txt"):
            playlist_name = os.path.splitext(filename)[0]
            
            # Skip retired file_list playlist (replaced by All Videos)
            if playlist_name == "file_list":
                log_print(f"  Skipping retired playlist: {playlist_name}")
                continue
            
            # Skip if already exists in incremental mode
            if incremental and playlist_name in existing_playlists:
                skipped_count += 1
                continue
            
            playlist_path = os.path.join(PLAYLIST_DIR, filename)
            
            # Create playlist
            cursor.execute("""
                INSERT OR IGNORE INTO playlists (name)
                VALUES (?)
            """, (playlist_name,))
            
            playlist_id = cursor.execute(
                "SELECT id FROM playlists WHERE name = ?", (playlist_name,)
            ).fetchone()[0]
            
            # Read video filenames from playlist
            try:
                missing_videos = []
                with open(playlist_path, 'r', encoding='utf-8', errors='ignore') as f:
                    position = 1
                    for line in f:
                        video_filename = line.strip()
                        if not video_filename:
                            continue
                        
                        # Get video_id
                        video_row = cursor.execute(
                            "SELECT id FROM videos WHERE filename = ?", (video_filename,)
                        ).fetchone()
                        
                        if video_row:
                            video_id = video_row[0]
                            cursor.execute("""
                                INSERT OR IGNORE INTO playlist_videos (playlist_id, video_id, position)
                                VALUES (?, ?, ?)
                            """, (playlist_id, video_id, position))
                            position += 1
                        else:
                            missing_videos.append(video_filename)
                
                if missing_videos:
                    all_missing_videos[playlist_name] = missing_videos
                    log_print(f"  Info: {len(missing_videos)} videos in '{playlist_name}' not found (files not in VideoFiles/)")
                    if len(missing_videos) <= 3:
                        for vid in missing_videos:
                            log_print(f"    - {vid}")
                    else:
                        log_print(f"    First 3: {', '.join(missing_videos[:3])}")
                        log_print(f"    (This is normal if videos were removed or ZIPs not extracted yet)")
                
                playlist_count += 1
            except Exception as e:
                log_print(f"  Error reading playlist {filename}: {e}")
    
    conn.commit()
    
    # Write detailed missing videos report to separate file
    if all_missing_videos:
        missing_log_path = os.path.join(LOG_DIR, f"missing_videos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt")
        try:
            with open(missing_log_path, 'w', encoding='utf-8') as f:
                f.write("=" * 80 + "\n")
                f.write("RetroViewer Migration - Missing Videos Report\n")
                f.write("=" * 80 + "\n\n")
                f.write("⚠️  IMPORTANT NOTES:\n")
                f.write("• These videos were NOT added to the database during migration\n")
                f.write("• Videos listed below were referenced in playlists but not found in VideoFiles/\n")
                f.write("• To add these videos:\n")
                f.write("  1. Place video files in Data/VideoFiles/ directory\n")
                f.write("  2. Run Manager.py and use the Video Scanner tab to scan for new videos\n")
                f.write("  3. Add scanned videos to playlists manually via Manager.py\n")
                f.write("\n")
                f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("=" * 80 + "\n\n")
                
                total_missing = sum(len(videos) for videos in all_missing_videos.values())
                f.write(f"Total Missing Videos: {total_missing}\n")
                f.write(f"Playlists Affected: {len(all_missing_videos)}\n\n")
                f.write("=" * 80 + "\n\n")
                
                for playlist_name, missing_videos in sorted(all_missing_videos.items()):
                    f.write(f"Playlist: {playlist_name}\n")
                    f.write(f"Missing: {len(missing_videos)} videos\n")
                    f.write("-" * 80 + "\n")
                    for video in missing_videos:
                        f.write(f"  • {video}\n")
                    f.write("\n")
            
            log_print(f"  📝 Detailed missing videos report: {missing_log_path}")
        except Exception as e:
            log_print(f"  Warning: Could not create missing videos report: {e}")
    
    if incremental:
        log_print(f"✓ Processed {playlist_count + skipped_count} playlists: {playlist_count} new, {skipped_count} skipped")
    else:
        log_print(f"✓ Migrated {playlist_count} playlists")


def create_all_videos_playlist(conn):
    """Create/update the 'All Videos' playlist with all videos in the database."""
    log_print("\nCreating 'All Videos' playlist...")
    
    cursor = conn.cursor()
    
    # Create or get the All Videos playlist
    cursor.execute("""
        INSERT OR IGNORE INTO playlists (name, description)
        VALUES ('All Videos', 'Master playlist containing all videos in the library')
    """)
    
    playlist_id = cursor.execute(
        "SELECT id FROM playlists WHERE name = 'All Videos'"
    ).fetchone()[0]
    
    # Clear existing entries (in case we're re-creating it)
    cursor.execute("DELETE FROM playlist_videos WHERE playlist_id = ?", (playlist_id,))
    
    # Add all videos to the playlist
    videos = cursor.execute("SELECT id FROM videos ORDER BY filename").fetchall()
    
    for position, (video_id,) in enumerate(videos, start=1):
        cursor.execute("""
            INSERT INTO playlist_videos (playlist_id, video_id, position)
            VALUES (?, ?, ?)
        """, (playlist_id, video_id, position))
    
    conn.commit()
    log_print(f"✓ Created 'All Videos' playlist with {len(videos)} videos")


def migrate_settings(conn, incremental=False):
    """Read settings files and populate settings table."""
    log_print("\nMigrating settings...")
    
    cursor = conn.cursor()
    
    if incremental:
        log_print("  (Incremental mode: will only update if settings files are present)")
    
    # Read settings.txt
    settings_file = os.path.join(SETTINGS_DIR, "settings.txt")
    if os.path.exists(settings_file):
        try:
            with open(settings_file, 'r') as f:
                lines = [line.strip().upper() for line in f if line.strip()]
                if lines:
                    first_line = lines[0]
                    if first_line == "YES":
                        playlist_name = "All Videos"  # Use master playlist as default
                    else:
                        playlist_name = first_line
                    
                    cursor.execute("""
                        UPDATE settings SET value = ?, last_modified = CURRENT_TIMESTAMP
                        WHERE key = 'active_playlist'
                    """, (playlist_name,))
        except Exception as e:
            log_print(f"  Warning: Could not read settings.txt: {e}")
    
    # Read FeaturePlayer.txt
    feature_settings_file = os.path.join(SETTINGS_DIR, "FeaturePlayer.txt")
    if os.path.exists(feature_settings_file):
        try:
            with open(feature_settings_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("Ads Played During Break:"):
                        ads_count = line.split(":")[-1].strip()
                        cursor.execute("""
                            UPDATE settings SET value = ?, last_modified = CURRENT_TIMESTAMP
                            WHERE key = 'ads_per_break'
                        """, (ads_count,))
                    elif line.startswith("Playlist:"):
                        playlist_name = line.split(":", 1)[-1].strip()
                        cursor.execute("""
                            UPDATE settings SET value = ?, last_modified = CURRENT_TIMESTAMP
                            WHERE key = 'feature_playlist'
                        """, (playlist_name,))
                    elif line.startswith("Shuffle:"):
                        # Migrate old shuffle setting to both new settings
                        shuffle_value = line.split(":")[-1].strip().upper()
                        cursor.execute("""
                            UPDATE settings SET value = ?, last_modified = CURRENT_TIMESTAMP
                            WHERE key = 'media_player_shuffle'
                        """, (shuffle_value,))
                        cursor.execute("""
                            UPDATE settings SET value = ?, last_modified = CURRENT_TIMESTAMP
                            WHERE key = 'feature_player_shuffle'
                        """, (shuffle_value,))
        except Exception as e:
            log_print(f"  Warning: Could not read FeaturePlayer.txt: {e}")
    
    conn.commit()
    log_print("✓ Settings migrated from text files")


def migrate_feature_movies_and_timestamps(conn, incremental=False):
    """Scan MediaFiles and migrate timestamps."""
    log_print("\nMigrating feature movies and timestamps...")
    
    cursor = conn.cursor()
    movie_count = 0
    timestamp_count = 0
    skipped_movies = 0
    skipped_timestamps = 0
    
    # Get existing movies and timestamps if incremental
    existing_movies = set()
    movies_with_timestamps = set()
    if incremental:
        existing_movies = set(row[0] for row in cursor.execute("SELECT filename FROM feature_movies").fetchall())
        movies_with_timestamps = set(row[0] for row in cursor.execute("""
            SELECT fm.filename FROM feature_movies fm 
            JOIN timestamps t ON fm.id = t.movie_id
        """).fetchall())
        log_print(f"  (Incremental mode: {len(existing_movies)} movies, {len(movies_with_timestamps)} with timestamps)")
    
    # Migrate feature movies
    if os.path.isdir(MEDIA_FOLDER):
        for filename in sorted(os.listdir(MEDIA_FOLDER)):
            if filename.lower().endswith((".mp4", ".mkv", ".avi")):
                # Skip if already exists in incremental mode
                if incremental and filename in existing_movies:
                    skipped_movies += 1
                    continue
                
                # Store relative path from base directory
                relative_path = os.path.join("Data", "MediaFiles", filename)
                title = os.path.splitext(filename)[0]
                
                cursor.execute("""
                    INSERT OR IGNORE INTO feature_movies (filename, title, file_path)
                    VALUES (?, ?, ?)
                """, (filename, title, relative_path))
                movie_count += 1
    
    # Migrate timestamps
    if os.path.isdir(TIMESTAMPS_DIR):
        for filename in os.listdir(TIMESTAMPS_DIR):
            if filename.lower().endswith(".txt"):
                timestamp_file = os.path.join(TIMESTAMPS_DIR, filename)
                movie_title = os.path.splitext(filename)[0]
                
                # Find corresponding movie (case-insensitive match)
                movie_row = cursor.execute("""
                    SELECT id, filename FROM feature_movies WHERE LOWER(title) = LOWER(?)
                """, (movie_title,)).fetchone()
                
                if not movie_row:
                    log_print(f"  Info: No feature movie found for timestamp file '{filename}'")
                    continue
                
                movie_id, movie_filename = movie_row[0], movie_row[1]
                
                # Skip if timestamps already exist for this movie in incremental mode
                if incremental and movie_filename in movies_with_timestamps:
                    skipped_timestamps += 1
                    continue
                
                try:
                    with open(timestamp_file, 'r') as f:
                        lines = [line.strip() for line in f if line.strip()]
                        
                        start_time = None
                        end_time = None
                        break_times = []
                        
                        for line in lines:
                            if line.startswith("Start:"):
                                start_time = line.split(":", 1)[1].strip()
                            elif line.startswith("End:"):
                                end_time = line.split(":", 1)[1].strip()
                            elif line.startswith("Timestamps:"):
                                continue
                            elif re.match(r"^\d+:\d+", line):
                                break_times.append(line)
                        
                        # Insert timestamp record
                        cursor.execute("""
                            INSERT OR IGNORE INTO timestamps (movie_id, start_time, end_time)
                            VALUES (?, ?, ?)
                        """, (movie_id, start_time, end_time))
                        
                        # Get timestamp_id
                        timestamp_id = cursor.execute(
                            "SELECT id FROM timestamps WHERE movie_id = ?", (movie_id,)
                        ).fetchone()[0]
                        
                        # Insert commercial breaks
                        for position, break_time in enumerate(break_times, 1):
                            cursor.execute("""
                                INSERT OR IGNORE INTO commercial_breaks (movie_id, break_time, position)
                                VALUES (?, ?, ?)
                            """, (movie_id, break_time, position))
                        
                        timestamp_count += 1
                except Exception as e:
                    log_print(f"  Error reading timestamp file {filename}: {e}")
    
    conn.commit()
    if incremental:
        log_print(f"✓ Movies: {movie_count} new, {skipped_movies} skipped | Timestamps: {timestamp_count} new, {skipped_timestamps} skipped")
    else:
        log_print(f"✓ Migrated {movie_count} feature movies and {timestamp_count} timestamp files")


def migrate_tags_and_genres(conn):
    """Extract unique tags and genres from videos and populate management tables."""
    log_print("\nExtracting tags and genres from videos...")
    
    cursor = conn.cursor()
    
    # Create tables if they don't exist (for backward compatibility)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create indexes
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_genres_name ON genres(name)")
    
    # Extract all tags from videos
    tags_set = set()
    genres_set = set()
    
    for row in cursor.execute("SELECT tags, genre FROM videos"):
        tags_value = row[0]
        genre_value = row[1]
        
        # Process tags (comma-separated)
        if tags_value and tags_value != "Unknown":
            tag_list = [t.strip() for t in tags_value.split(',')]
            tags_set.update([t for t in tag_list if t])
        
        # Process genre (single value)
        if genre_value and genre_value != "Unknown":
            genres_set.add(genre_value.strip())
    
    # Insert tags
    tag_count = 0
    for tag in tags_set:
        cursor.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag,))
        if cursor.rowcount > 0:
            tag_count += 1
    
    # Insert genres
    genre_count = 0
    for genre in genres_set:
        cursor.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (genre,))
        if cursor.rowcount > 0:
            genre_count += 1
    
    conn.commit()
    log_print(f"✓ Extracted {tag_count} unique tags and {genre_count} unique genres")


def main():
    """Run the complete migration."""
    # Initialize logging
    init_log()
    
    # Check for --auto flag for silent installation
    auto_mode = "--auto" in sys.argv
    
    # Detect installation type
    new_install = is_new_installation()
    
    if new_install:
        if auto_mode:
            # Silent mode - minimal output
            pass  # No banner needed for silent mode
        else:
            # New installation - simple, welcoming message
            log_print("=" * 60)
            log_print("RetroViewer Database Setup")
            log_print("=" * 60)
            log_print("\nWelcome to RetroViewer!")
            log_print("This will initialize your database and import any existing data.")
            log_print("\nThe database will be created at:")
            log_print(f"  {DB_PATH}")
            log_print("\nReady to set up your RetroViewer database.")
    else:
        # Upgrade - detailed migration information
        log_print("=" * 60)
        log_print("RetroViewer Migration Tool")
        log_print("=" * 60)
        log_print("\n⚠️  IMPORTANT MIGRATION NOTICE:")
        log_print("=" * 60)
        log_print("• This script handles BOTH directory AND database migration")
        log_print("• Old directory structure will be migrated to new Data/ layout")
        log_print("• Text files will be migrated to SQLite database")
        log_print("• Text files will remain as REFERENCE ONLY after migration")
        log_print("• DO NOT create new text files - use the database and GUI tools")
        log_print("=" * 60)
        
        log_print("\nThis script will:")
        log_print("  PHASE 1: Directory Structure Migration (if needed)")
        log_print("    - Migrate old directory structure to new Data/ layout")
        log_print("    - Archive old directories for safe keeping")
        log_print("")
        log_print("  PHASE 2: Database Migration")
        log_print("    - Create/update SQLite database from schema")
        log_print("    - Import videos, playlists, settings, and timestamps")
        log_print("    - Extract tags and genres from videos for management")
    
    # Check for --auto mode - skip all prompts for new installations
    if auto_mode and new_install:
        # Create directory structure for new installation
        create_data_directory_structure()
        
        # Silent auto-create for new installations
        conn = init_database()
        
        # Import any existing data silently (shouldn't be any, but check anyway)
        migrate_videos(conn, incremental=False)
        migrate_playlists(conn, incremental=False)
        create_all_videos_playlist(conn)  # Always create All Videos playlist
        migrate_settings(conn, incremental=False)
        migrate_feature_movies_and_timestamps(conn, incremental=False)
        migrate_tags_and_genres(conn)
        
        conn.close()
        close_log()
        
        # Show log file location
        if os.path.exists(LOG_FILE):
            print(f"📝 Full log saved to: {LOG_FILE}")
        
        return  # Exit silently
    
    # Check if directory migration is needed
    old_dirs = check_old_directory_structure()
    
    if old_dirs:
        if not migrate_directory_structure():
            log_print("\n✗ Migration cancelled - directory structure not migrated")
            close_log()
            sys.exit(1)  # Exit with error code to stop launcher
    
    log_print("\n" + "=" * 60)
    log_print("STEP 2: Database Migration")
    log_print("=" * 60)
    
    # Determine migration mode
    migration_mode = "full"  # full or incremental
    
    if os.path.exists(DB_PATH):
        log_print(f"\n⚠️  Database already exists at {DB_PATH}")
        log_print("\nChoose migration mode:")
        log_print("  1. FULL - Wipe database and re-import everything from text files")
        log_print("  2. INCREMENTAL - Import only new items from text files (keeps existing data)")
        log_print("\nRecommendation: Use INCREMENTAL unless you have issues with the database.")
        
        while True:
            choice = input("\nEnter your choice (1 or 2): ").strip()
            if choice == "1":
                migration_mode = "full"
                os.remove(DB_PATH)
                log_print("✓ Existing database removed - will perform full migration")
                break
            elif choice == "2":
                migration_mode = "incremental"
                log_print("✓ Will perform incremental migration (add new items only)")
                break
            else:
                log_print("Invalid choice. Please enter 1 or 2.")
    else:
        if new_install:
            log_print("\nInitializing database...")
        else:
            log_print("\nNo existing database found - will perform full migration.")
        migration_mode = "full"
    
    # Verify schema file exists
    schema_path = os.path.join(BASE_DIR, "Database", "database_schema.sql")
    if not os.path.exists(schema_path):
        log_print(f"\n✗ Error: Schema file not found at {schema_path}")
      Ensure Data/ directory structure exists (for new installs or upgrades)
    if new_install or not os.path.exists(DATA_DIR):
        create_data_directory_structure()
    
    #   log_print("Cannot proceed without database schema.")
        return
    
    # Initialize database (creates new or opens existing)
    if migration_mode == "full":
        conn = init_database()
    else:
        # Open existing database
        log_print("\nOpening existing database...")
        conn = sqlite3.connect(DB_PATH)
        log_print(f"✓ Connected to existing database")
    
    try:
        # Run migrations based on mode
        log_print(f"\n{'='*60}")
        log_print(f"Starting {'FULL' if migration_mode == 'full' else 'INCREMENTAL'} migration...")
        if migration_mode == "incremental":
            log_print("  (Only NEW items from text files will be imported)")
        log_print(f"{'='*60}")
        
        migrate_videos(conn, incremental=(migration_mode == "incremental"))
        migrate_playlists(conn, incremental=(migration_mode == "incremental"))
        create_all_videos_playlist(conn)  # Always create/update All Videos playlist
        migrate_settings(conn, incremental=(migration_mode == "incremental"))
        migrate_feature_movies_and_timestamps(conn, incremental=(migration_mode == "incremental"))
        
        # Migrate tags and genres
        log_print("\n" + "=" * 60)
        log_print("Syncing Tags and Genres...")
        log_print("=" * 60)
        migrate_tags_and_genres(conn)
        
        # Summary
        log_print("\n" + "=" * 60)
        log_print(f"Migration Summary ({'FULL' if migration_mode == 'full' else 'INCREMENTAL'} mode):")
        log_print("=" * 60)
        
        cursor = conn.cursor()
        
        video_count = cursor.execute("SELECT COUNT(*) FROM videos").fetchone()[0]
        playlist_count = cursor.execute("SELECT COUNT(*) FROM playlists").fetchone()[0]
        movie_count = cursor.execute("SELECT COUNT(*) FROM feature_movies").fetchone()[0]
        timestamp_count = cursor.execute("SELECT COUNT(*) FROM timestamps").fetchone()[0]
        break_count = cursor.execute("SELECT COUNT(*) FROM commercial_breaks").fetchone()[0]
        setting_count = cursor.execute("SELECT COUNT(*) FROM settings").fetchone()[0]
        
        # Get tags and genres count
        try:
            tag_count = cursor.execute("SELECT COUNT(*) FROM tags").fetchone()[0]
            genre_count = cursor.execute("SELECT COUNT(*) FROM genres").fetchone()[0]
        except sqlite3.OperationalError:
            tag_count = 0
            genre_count = 0
        
        log_print(f"Videos:              {video_count}")
        log_print(f"Playlists:           {playlist_count}")
        log_print(f"Feature Movies:      {movie_count}")
        log_print(f"Timestamps:          {timestamp_count}")
        log_print(f"Commercial Breaks:   {break_count}")
        log_print(f"Settings:            {setting_count}")
        log_print(f"Tags:                {tag_count}")
        log_print(f"Genres:              {genre_count}")
        log_print("=" * 60)
        log_print(f"\n✓ {'FULL' if migration_mode == 'full' else 'INCREMENTAL'} migration completed successfully!")
        log_print(f"\nDatabase location: {DB_PATH}")
        
        if migration_mode == "incremental":
            log_print("\nNote: Incremental mode used - existing database entries were preserved.")
            log_print("      Only new items from text files were added.")
        
        log_print("\n" + "=" * 60)
        log_print("NEXT STEPS:")
        log_print("=" * 60)
        
        if new_install:
            # Simplified next steps for new installations
            log_print("1. Add your video files:")
            log_print("   - Place commercial videos in: Data/VideoFiles/")
            log_print("   - Place feature movies in: Data/MediaFiles/")
            log_print("")
            log_print("2. Scan your videos:")
            log_print("   - Run Manager.py and use the Video Scanner tab to add videos to database")
            log_print("")
            log_print("3. Start using RetroViewer:")
            log_print("   - Manager: Organize playlists and add timestamps")
            log_print("   - Media Player: Watch commercials")
            log_print("   - Feature Player: Watch movies with commercial breaks")
            log_print("")
            log_print("Tip: Run the launcher (launch.sh/launch.bat/launch.ps1) for easy access!")
        else:
            # Detailed next steps for upgrades
            log_print("1. Test the application with the new structure and database:")
            log_print("   - Use Manager.py Video Scanner tab to scan for new videos")
            log_print("   - Run 'python3 Scripts/MediaPlayer.py' to test playback")
            log_print("   - Run 'python3 Scripts/Manager.py' to manage playlists/timestamps")
            log_print("\n2. ⚠️  DIRECTORY STRUCTURE CHANGES:")
            log_print("   - All data files are now under Data/ directory")
            log_print("   - Videos: Data/VideoFiles/")
            log_print("   - Feature movies: Data/MediaFiles/")
            log_print("   - Playlists: Data/Playlists/")
            log_print("   - Timestamps: Data/Timestamps/")
            log_print("   - Settings: Data/Settings/")
            log_print("\n3. ⚠️  TEXT FILES ARE NOW RETIRED:")
            log_print("   - Text files in Data/Playlists/ and Data/Timestamps/ are NO LONGER USED")
            log_print("   - The database is the ONLY data source")
            log_print("   - Players will ONLY read from database (no fallback)")
            log_print("   - You can safely ARCHIVE or DELETE old .txt files")
            log_print("   - Manager.py can still IMPORT from .txt files if needed")
            log_print("\n4. Managing your library going forward:")
            log_print("   - Add new videos: Place in Data/VideoFiles/ and scan via Manager.py Video Scanner tab")
            log_print("   - Create playlists: Use Scripts/Manager.py to create and manage")
            log_print("   - Add timestamps: Use Scripts/Manager.py Commercial Breaks tab")
            log_print("   - Update metadata: Use Scripts/Manager.py (updates both MP4 and database)")
            log_print("\n⚠️  CRITICAL: Database is now REQUIRED for all operations.")
            log_print("   Without the database, players will not work.")
        
        log_print("=" * 60)
        
    except Exception as e:
        log_print(f"\n✗ Migration failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        conn.close()
        close_log()
        
        # Move log files to Migration Logs folder
        migration_logs_dir = os.path.join(BASE_DIR, "Migration Logs")
        os.makedirs(migration_logs_dir, exist_ok=True)
        
        log_files_moved = []
        
        # Move main setup log
        if os.path.exists(LOG_FILE):
            new_log_path = os.path.join(migration_logs_dir, os.path.basename(LOG_FILE))
            try:
                shutil.move(LOG_FILE, new_log_path)
                log_files_moved.append(new_log_path)
            except Exception:
                log_files_moved.append(LOG_FILE)  # Keep original path if move failed
        
        # Move missing videos log if it exists
        for file in os.listdir(LOG_DIR):
            if file.startswith("missing_videos_") and file.endswith(".txt"):
                old_path = os.path.join(LOG_DIR, file)
                new_path = os.path.join(migration_logs_dir, file)
                try:
                    shutil.move(old_path, new_path)
                    log_files_moved.append(new_path)
                except Exception:
                    pass
        
        # Show log file locations
        if log_files_moved:
            print(f"\n📝 Migration logs saved to: {migration_logs_dir}")
            for log_path in log_files_moved:
                print(f"   • {os.path.basename(log_path)}")


if __name__ == "__main__":
    main()
