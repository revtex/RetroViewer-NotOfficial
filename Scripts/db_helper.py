"""
Database helper module for RetroViewer.
Provides common database operations for videos, playlists, settings, and timestamps.
"""

import os
import sqlite3
from typing import List, Tuple, Optional, Dict, Any
from contextlib import contextmanager


# Database path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)  # Parent of Scripts/
DB_PATH = os.path.join(BASE_DIR, "Database", "retroviewer.db")


def get_absolute_path(relative_path):
    """Convert relative path to absolute path from base directory."""
    if os.path.isabs(relative_path):
        return relative_path
    # Normalize path separators for cross-platform compatibility
    relative_path = relative_path.replace('\\', os.sep).replace('/', os.sep)
    return os.path.join(BASE_DIR, relative_path)


@contextmanager
def get_db_connection():
    """Context manager for database connections."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row  # Access columns by name
    try:
        yield conn
        conn.commit()  # Commit changes before closing
    except Exception:
        conn.rollback()  # Rollback on error
        raise
    finally:
        conn.close()


# ========== Video Operations ==========

def get_all_videos() -> List[Dict[str, Any]]:
    """Get all videos from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, filename, title, tags, year, genre, file_path, duration
            FROM videos
            ORDER BY filename
        """).fetchall()
        return [dict(row) for row in rows]


def get_video_by_filename(filename: str) -> Optional[Dict[str, Any]]:
    """Get a single video by filename."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("""
            SELECT id, filename, title, tags, year, genre, file_path
            FROM videos
            WHERE filename = ?
        """, (filename,)).fetchone()
        return dict(row) if row else None


def update_video_metadata(filename: str, title: Optional[str] = None, tags: Optional[str] = None, 
                         year: Optional[str] = None, genre: Optional[str] = None) -> bool:
    """Update video metadata in database."""
    fields = []
    values = []
    
    if title is not None:
        fields.append("title = ?")
        values.append(title)
    if tags is not None:
        fields.append("tags = ?")
        values.append(tags)
    if year is not None:
        fields.append("year = ?")
        values.append(year)
    if genre is not None:
        fields.append("genre = ?")
        values.append(genre)
    
    if not fields:
        return False
    
    fields.append("last_modified = CURRENT_TIMESTAMP")
    values.append(filename)
    
    query = f"UPDATE videos SET {', '.join(fields)} WHERE filename = ?"
    
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, values)
        conn.commit()
        return cursor.rowcount > 0


def add_video(filename: str, file_path: str, title: str = "Unknown", 
              tags: str = "Unknown", year: str = "Unknown", genre: str = "Unknown", duration: float = None) -> int:
    """Add a new video to the database. Returns the video ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO videos (filename, title, tags, year, genre, file_path, duration)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (filename, title, tags, year, genre, file_path, duration))
        conn.commit()
        return cursor.lastrowid or 0


def delete_video(filename: str) -> bool:
    """Delete a video from the database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM videos WHERE filename = ?", (filename,))
        conn.commit()
        return cursor.rowcount > 0


def get_video_duration(filename: str) -> float:
    """Get cached video duration from database. Returns None if not cached."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT duration FROM videos WHERE filename = ?", (filename,))
        row = cursor.fetchone()
        return row[0] if row and row[0] is not None else None


def set_video_duration(filename: str, duration: float) -> bool:
    """Cache video duration in database."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE videos SET duration = ?, last_modified = CURRENT_TIMESTAMP 
            WHERE filename = ?
        """, (duration, filename))
        return cursor.rowcount > 0


# ========== Playlist Operations ==========

def get_all_playlists() -> List[Dict[str, Any]]:
    """Get all playlists."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, name, description, created_date, last_modified
            FROM playlists
            ORDER BY name
        """).fetchall()
        return [dict(row) for row in rows]


def list_playlists() -> List[Dict[str, Any]]:
    """Alias for get_all_playlists()."""
    return get_all_playlists()


def get_playlist_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get a playlist by name."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("""
            SELECT id, name, description
            FROM playlists
            WHERE name = ?
        """, (name,)).fetchone()
        return dict(row) if row else None


def get_playlist_videos(playlist_name: str) -> List[Dict[str, Any]]:
    """Get all videos in a playlist with metadata, ordered by position."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT v.filename, v.title, v.tags, v.year, v.genre, pv.position
            FROM playlist_videos pv
            JOIN playlists p ON pv.playlist_id = p.id
            JOIN videos v ON pv.video_id = v.id
            WHERE p.name = ?
            ORDER BY pv.position
        """, (playlist_name,)).fetchall()
        return [dict(row) for row in rows]


def create_playlist(name: str, description: Optional[str] = None) -> int:
    """Create a new playlist. Returns the playlist ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO playlists (name, description)
            VALUES (?, ?)
        """, (name, description))
        conn.commit()
        return cursor.lastrowid or 0


def add_video_to_playlist(playlist_name: str, filename: str, position: Optional[int] = None):
    """Add a video to a playlist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        
        # Get playlist ID
        playlist = cursor.execute(
            "SELECT id FROM playlists WHERE name = ?", (playlist_name,)
        ).fetchone()
        if not playlist:
            return False
        
        # Get video ID
        video = cursor.execute(
            "SELECT id FROM videos WHERE filename = ?", (filename,)
        ).fetchone()
        if not video:
            return False
        
        # Determine position if not provided
        if position is None:
            max_pos = cursor.execute("""
                SELECT MAX(position) FROM playlist_videos WHERE playlist_id = ?
            """, (playlist['id'],)).fetchone()[0]
            position = (max_pos or 0) + 1
        
        # Insert
        cursor.execute("""
            INSERT OR IGNORE INTO playlist_videos (playlist_id, video_id, position)
            VALUES (?, ?, ?)
        """, (playlist['id'], video['id'], position))
        conn.commit()
        return True


def clear_playlist(playlist_name: str):
    """Remove all videos from a playlist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM playlist_videos
            WHERE playlist_id = (SELECT id FROM playlists WHERE name = ?)
        """, (playlist_name,))
        conn.commit()


def delete_playlist(playlist_name: str) -> bool:
    """Delete a playlist and all its video associations."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # First delete playlist_videos entries
        cursor.execute("""
            DELETE FROM playlist_videos
            WHERE playlist_id = (SELECT id FROM playlists WHERE name = ?)
        """, (playlist_name,))
        # Then delete the playlist
        cursor.execute("DELETE FROM playlists WHERE name = ?", (playlist_name,))
        conn.commit()
        return cursor.rowcount > 0


def remove_video_from_playlist(playlist_name: str, filename: str) -> bool:
    """Remove a video from a playlist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            DELETE FROM playlist_videos
            WHERE playlist_id = (SELECT id FROM playlists WHERE name = ?)
            AND video_id = (SELECT id FROM videos WHERE filename = ?)
        """, (playlist_name, filename))
        conn.commit()
        return cursor.rowcount > 0


def update_playlist_video_position(playlist_name: str, filename: str, new_position: int) -> bool:
    """Update the position of a video in a playlist."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE playlist_videos
            SET position = ?
            WHERE playlist_id = (SELECT id FROM playlists WHERE name = ?)
            AND video_id = (SELECT id FROM videos WHERE filename = ?)
        """, (new_position, playlist_name, filename))
        conn.commit()
        return cursor.rowcount > 0


# ========== Settings Operations ==========

def get_setting(key: str, default: Optional[str] = None) -> Optional[str]:
    """Get a setting value by key."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("""
            SELECT value FROM settings WHERE key = ?
        """, (key,)).fetchone()
        return row['value'] if row else default


def set_setting(key: str, value: str, description: Optional[str] = None):
    """Set a setting value."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        if description:
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, description, last_modified)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            """, (key, value, description))
        else:
            cursor.execute("""
                INSERT OR REPLACE INTO settings (key, value, last_modified)
                VALUES (?, ?, CURRENT_TIMESTAMP)
            """, (key, value))
        conn.commit()


def get_all_settings() -> Dict[str, str]:
    """Get all settings as a dictionary."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("SELECT key, value FROM settings").fetchall()
        return {row['key']: row['value'] for row in rows}


# ========== Feature Movie & Timestamp Operations ==========

def get_all_feature_movies() -> List[Dict[str, Any]]:
    """Get all feature movies."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, filename, title, file_path
            FROM feature_movies
            ORDER BY title
        """).fetchall()
        return [dict(row) for row in rows]


def get_feature_movie_by_filename(filename: str) -> Optional[Dict[str, Any]]:
    """Get a feature movie by filename."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("""
            SELECT id, filename, title, file_path
            FROM feature_movies
            WHERE filename = ?
        """, (filename,)).fetchone()
        return dict(row) if row else None


def get_movie_timestamps(movie_id: int) -> Optional[Dict[str, Any]]:
    """Get start/end timestamps for a movie."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        row = cursor.execute("""
            SELECT start_time, end_time
            FROM timestamps
            WHERE movie_id = ?
        """, (movie_id,)).fetchone()
        return dict(row) if row else None


def get_commercial_breaks(movie_id: int) -> List[Dict[str, Any]]:
    """Get all commercial break times for a movie, ordered by break time."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, break_time, position
            FROM commercial_breaks
            WHERE movie_id = ?
            ORDER BY break_time
        """, (movie_id,)).fetchall()
        return [dict(row) for row in rows]


def get_timestamps(movie_id: int) -> List[Dict[str, Any]]:
    """Get timestamps for a movie."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        rows = cursor.execute("""
            SELECT id, start_time, end_time
            FROM timestamps
            WHERE movie_id = ?
        """, (movie_id,)).fetchall()
        return [dict(row) for row in rows]


def add_feature_movie(filename: str, title: str, file_path: str) -> int:
    """Add a feature movie and return its ID."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO feature_movies (filename, title, file_path)
            VALUES (?, ?, ?)
        """, (filename, title, file_path))
        conn.commit()
        return cursor.lastrowid or 0


def add_timestamp(movie_id: int, start_time: str, end_time: str) -> int:
    """Add timestamp record for a movie."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO timestamps (movie_id, start_time, end_time)
            VALUES (?, ?, ?)
        """, (movie_id, start_time, end_time))
        conn.commit()
        return cursor.lastrowid or 0


def add_commercial_break(movie_id: int, break_time: str) -> int:
    """Add a commercial break timestamp."""
    with get_db_connection() as conn:
        cursor = conn.cursor()
        # Get next position
        row = cursor.execute("""
            SELECT MAX(position) as max_pos
            FROM commercial_breaks
            WHERE movie_id = ?
        """, (movie_id,)).fetchone()
        next_pos = (row['max_pos'] or 0) + 1
        
        cursor.execute("""
            INSERT INTO commercial_breaks (movie_id, break_time, position)
            VALUES (?, ?, ?)
        """, (movie_id, break_time, next_pos))
        conn.commit()
        return cursor.lastrowid or 0


def delete_commercial_break(break_id: int) -> bool:
    """Delete a commercial break by ID."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM commercial_breaks WHERE id = ?", (break_id,))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting commercial break: {e}")
        return False


def clear_commercial_breaks(movie_id: int) -> bool:
    """Clear all commercial breaks for a movie."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM commercial_breaks WHERE movie_id = ?", (movie_id,))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error clearing commercial breaks: {e}")
        return False


def clear_timestamps(movie_id: int) -> bool:
    """Clear timestamps for a movie."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM timestamps WHERE movie_id = ?", (movie_id,))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error clearing timestamps: {e}")
        return False


# ========== Utility Functions ==========

def scan_and_sync_videos(video_folder: str) -> Tuple[int, int]:
    """
    Scan video folder and sync with database.
    Returns (added_count, removed_count).
    """
    import re
    from mutagen.mp4 import MP4
    
    def _coerce_first(value, fallback="Unknown"):
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
        s = str(s).strip()
        m = re.match(r"^(\d{4})", s)
        return m.group(1) if m else (s if s else "Unknown")
    
    def get_metadata(file_path):
        try:
            mp4_file = MP4(file_path)
            title = _coerce_first(mp4_file.get("\xa9nam", ["Unknown"]))
            genre = _coerce_first(mp4_file.get("\xa9gen", ["Unknown"]))
            year_raw = _coerce_first(mp4_file.get("\xa9day", ["Unknown"]))
            year = _year_display(year_raw)
            tags = _coerce_first(mp4_file.get("\xa9too", ["Unknown"]))
            return title, tags, year, genre
        except Exception:
            return "Unknown", "Unknown", "Unknown", "Unknown"
    
    if not os.path.isdir(video_folder):
        return 0, 0
    
    # Get existing videos from DB
    existing_videos = {v['filename']: v for v in get_all_videos()}
    
    # Scan folder
    found_files = set()
    added_count = 0
    
    for filename in os.listdir(video_folder):
        if filename.lower().endswith(".mp4"):
            found_files.add(filename)
            
            if filename not in existing_videos:
                # New file - add to database
                file_path = os.path.join(video_folder, filename)
                # Store relative path from base directory
                relative_path = os.path.join("Data", "VideoFiles", filename)
                title, tags, year, genre = get_metadata(file_path)
                add_video(filename, relative_path, title, tags, year, genre)
                added_count += 1
    
    # Remove videos from DB that no longer exist
    removed_count = 0
    for filename in existing_videos:
        if filename not in found_files:
            delete_video(filename)
            removed_count += 1
    
    return added_count, removed_count


def export_playlist_to_file(playlist_name: str, output_path: str) -> bool:
    """Export a playlist to a text file (for manual export/archival only - not used by system)."""
    try:
        videos = get_playlist_videos(playlist_name)
        with open(output_path, 'w', encoding='utf-8') as f:
            for video in videos:
                f.write(f"{video['filename']}\n")
        return True
    except Exception as e:
        print(f"Error exporting playlist: {e}")
        return False


# ========== Tag Management ==========

def get_all_tags() -> List[str]:
    """Get all available tags."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT name FROM tags ORDER BY name").fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        # Backward compatibility: if tags table doesn't exist, return empty list
        print(f"Warning: Could not fetch tags (table may not exist): {e}")
        return []


def add_tag(tag_name: str) -> bool:
    """Add a new tag to the available tags list."""
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (tag_name.strip(),))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error adding tag: {e}")
        return False


def delete_tag(tag_name: str) -> bool:
    """Delete a tag from the available tags list."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM tags WHERE name = ?", (tag_name,))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting tag: {e}")
        return False


def sync_tags_from_videos():
    """Extract all unique tags from videos and add them to the tags table."""
    all_videos = get_all_videos()
    tags_set = set()
    
    for video in all_videos:
        if video['tags'] and video['tags'] != "Unknown":
            # Split comma-separated tags
            video_tags = [t.strip() for t in video['tags'].split(',')]
            tags_set.update(video_tags)
    
    # Add all tags to the database
    for tag in tags_set:
        if tag:
            add_tag(tag)


# ========== Genre Management ==========

def get_all_genres() -> List[str]:
    """Get all available genres."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("SELECT name FROM genres ORDER BY name").fetchall()
            return [row[0] for row in rows]
    except Exception as e:
        # Backward compatibility: if genres table doesn't exist, return empty list
        print(f"Warning: Could not fetch genres (table may not exist): {e}")
        return []


def add_genre(genre_name: str) -> bool:
    """Add a new genre to the available genres list."""
    try:
        with get_db_connection() as conn:
            conn.execute("INSERT OR IGNORE INTO genres (name) VALUES (?)", (genre_name.strip(),))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error adding genre: {e}")
        return False


def delete_genre(genre_name: str) -> bool:
    """Delete a genre from the available genres list."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM genres WHERE name = ?", (genre_name,))
            conn.commit()
        return True
    except Exception as e:
        print(f"Error deleting genre: {e}")
        return False


def sync_genres_from_videos():
    """Extract all unique genres from videos and add them to the genres table."""
    all_videos = get_all_videos()
    genres_set = set()
    
    for video in all_videos:
        if video['genre'] and video['genre'] != "Unknown":
            genres_set.add(video['genre'].strip())
    
    # Add all genres to the database
    for genre in genres_set:
        if genre:
            add_genre(genre)


# ========== Now Playing Queue Management ==========

def get_now_playing_queue() -> List[Dict[str, Any]]:
    """Get the ordered list of movies in the now playing queue."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            rows = cursor.execute("""
                SELECT q.id, q.movie_id, q.position, m.filename, m.title, m.file_path
                FROM now_playing_queue q
                JOIN feature_movies m ON q.movie_id = m.id
                ORDER BY q.position
            """).fetchall()
            return [
                {
                    "id": row[0],
                    "movie_id": row[1],
                    "position": row[2],
                    "filename": row[3],
                    "title": row[4],
                    "file_path": row[5]
                }
                for row in rows
            ]
    except Exception as e:
        print(f"Error getting now playing queue: {e}")
        return []


def add_to_now_playing_queue(movie_id: int) -> bool:
    """Add a movie to the end of the now playing queue."""
    try:
        with get_db_connection() as conn:
            # Get max position
            cursor = conn.cursor()
            max_pos = cursor.execute("SELECT MAX(position) FROM now_playing_queue").fetchone()[0]
            next_pos = (max_pos or 0) + 1
            
            conn.execute(
                "INSERT INTO now_playing_queue (movie_id, position) VALUES (?, ?)",
                (movie_id, next_pos)
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"Error adding to now playing queue: {e}")
        return False


def remove_from_now_playing_queue(queue_id: int) -> bool:
    """Remove a movie from the now playing queue and reorder remaining."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get position of item to remove
            pos = cursor.execute(
                "SELECT position FROM now_playing_queue WHERE id = ?",
                (queue_id,)
            ).fetchone()
            
            if not pos:
                return False
            
            removed_pos = pos[0]
            
            # Delete the item
            cursor.execute("DELETE FROM now_playing_queue WHERE id = ?", (queue_id,))
            
            # Reorder: Set all positions to negative temporarily to avoid UNIQUE constraint
            cursor.execute(
                "UPDATE now_playing_queue SET position = -position WHERE position > ?",
                (removed_pos,)
            )
            
            # Then shift down by setting to positive values minus 1
            cursor.execute(
                "UPDATE now_playing_queue SET position = -position - 1 WHERE position < 0"
            )
            
        return True
    except Exception as e:
        print(f"Error removing from now playing queue: {e}")
        return False


def clear_now_playing_queue() -> bool:
    """Clear all movies from the now playing queue."""
    try:
        with get_db_connection() as conn:
            conn.execute("DELETE FROM now_playing_queue")
            conn.commit()
        return True
    except Exception as e:
        print(f"Error clearing now playing queue: {e}")
        return False


def move_in_now_playing_queue(queue_id: int, new_position: int) -> bool:
    """Move a movie to a new position in the queue."""
    try:
        with get_db_connection() as conn:
            cursor = conn.cursor()
            
            # Get current position
            current = cursor.execute(
                "SELECT position FROM now_playing_queue WHERE id = ?",
                (queue_id,)
            ).fetchone()
            
            if not current:
                return False
            
            old_pos = current[0]
            
            if old_pos == new_position:
                return True
            
            # Step 1: Move the item to a temporary position to avoid constraint violation
            temp_pos = -1
            conn.execute(
                "UPDATE now_playing_queue SET position = ? WHERE id = ?",
                (temp_pos, queue_id)
            )
            
            # Step 2: Shift items between old and new positions
            if new_position < old_pos:
                # Moving up: shift items down
                conn.execute(
                    "UPDATE now_playing_queue SET position = position + 1 WHERE position >= ? AND position < ?",
                    (new_position, old_pos)
                )
            else:
                # Moving down: shift items up
                conn.execute(
                    "UPDATE now_playing_queue SET position = position - 1 WHERE position > ? AND position <= ?",
                    (old_pos, new_position)
                )
            
            # Step 3: Move item from temporary position to final position
            conn.execute(
                "UPDATE now_playing_queue SET position = ? WHERE id = ?",
                (new_position, queue_id)
            )
            conn.commit()
        return True
    except Exception as e:
        print(f"Error moving in now playing queue: {e}")
        return False


if __name__ == "__main__":
    # Test database connection
    print("Testing database connection...")
    print(f"Database: {DB_PATH}")
    print(f"Exists: {os.path.exists(DB_PATH)}")
    
    print("\nVideo count:", len(get_all_videos()))
    print("Playlist count:", len(get_all_playlists()))
    print("\nSettings:")
    for key, value in get_all_settings().items():
        print(f"  {key}: {value}")
