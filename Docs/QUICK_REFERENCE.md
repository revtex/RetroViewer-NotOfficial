# RetroViewer Database - Quick Reference

## 🗄️ Database Location
```
/workspaces/RetroViewer - .053/retroviewer.db
```

## 📦 Common Operations

### Import Module
```python
import db_helper
```

### Videos
```python
# Get all videos
videos = db_helper.get_all_videos()

# Get specific video
video = db_helper.get_video_by_filename("video.mp4")

# Update video metadata
db_helper.update_video_metadata("video.mp4", title="New Title", tags="Holiday")

# Add new video
db_helper.add_video("new.mp4", "/path/to/new.mp4", title="Title")

# Sync with filesystem
added, removed = db_helper.scan_and_sync_videos("/path/to/VideoFiles")
```

### Playlists
```python
# Get all playlists
playlists = db_helper.get_all_playlists()

# Get playlist videos
videos = db_helper.get_playlist_videos("1990's Christmas")

# Create playlist
playlist_id = db_helper.create_playlist("My Playlist", "Description")

# Add video to playlist
db_helper.add_video_to_playlist("My Playlist", "video.mp4", position=1)

# Clear playlist
db_helper.clear_playlist("My Playlist")

# Export playlist to text
db_helper.export_playlist_to_file("My Playlist", "output.txt")
```

### Settings
```python
# Get setting
value = db_helper.get_setting("ads_per_break", default="3")

# Set setting
db_helper.set_setting("ads_per_break", "5")

# Get all settings
settings = db_helper.get_all_settings()
```

### Feature Movies & Timestamps
```python
# Get all feature movies
movies = db_helper.get_all_feature_movies()

# Get movie by filename
movie = db_helper.get_feature_movie_by_filename("Garfield.mp4")

# Get timestamps
timestamps = db_helper.get_movie_timestamps(movie_id)

# Get commercial breaks
breaks = db_helper.get_commercial_breaks(movie_id)
```

## 🔧 Maintenance Commands

### Command Line
```bash
# Sync videos with database
python3 ReadFileName.py

# Test database connection
python3 db_helper.py

# View database
sqlite3 retroviewer.db

# Backup database
cp retroviewer.db retroviewer_backup.db
```

### SQL Queries
```sql
-- View all videos
SELECT filename, title, year FROM videos;

-- View all playlists
SELECT name FROM playlists;

-- View playlist contents
SELECT v.filename 
FROM playlist_videos pv 
JOIN videos v ON pv.video_id = v.id 
JOIN playlists p ON pv.playlist_id = p.id 
WHERE p.name = '1990''s Christmas' 
ORDER BY pv.position;

-- View settings
SELECT * FROM settings;

-- Count videos by year
SELECT year, COUNT(*) as count 
FROM videos 
GROUP BY year 
ORDER BY year;

-- Find videos by tag
SELECT filename, title 
FROM videos 
WHERE tags LIKE '%Christmas%';
```

## 📋 Database Tables

| Table | Purpose |
|-------|---------|
| `videos` | Video files and metadata |
| `playlists` | Playlist definitions |
| `playlist_videos` | Playlist membership |
| `settings` | Key-value settings |
| `feature_movies` | Feature-length movies |
| `timestamps` | Movie start/end times |
| `commercial_breaks` | Break timestamps |

## ⚙️ Current Settings

| Key | Default Value |
|-----|---------------|
| `active_playlist` | `file_list` |
| `ads_per_break` | `5` |
| `feature_playlist` | `1990's Christmas` |
| `shuffle` | `ON` |
| `timed_play` | `NO` |
| `now_playing` | `` |

## 🔄 Workflow

### Adding New Videos
1. Copy MP4 files to `VideoFiles/`
2. Run Manager.py and use Video Scanner tab to scan videos
3. Videos automatically added to database

### Creating Playlists
1. Open Meta Editor: `python3 "Meta Editor.v2.py"` (GUI required)
2. Filter videos (by tags, year, genre)
3. Click "Export Filtered List"
4. Playlist saved to database + text file

### Changing Settings
```python
import db_helper
db_helper.set_setting("ads_per_break", "3")
db_helper.set_setting("shuffle", "OFF")
```

## 🚨 Troubleshooting

| Issue | Solution |
|-------|----------|
| Videos missing | Use Manager.py Video Scanner tab to rescan |
| Old playlists | Text files still work, database preferred |
| Corrupted database | Restore from `Backups/` |
| Metadata out of sync | Meta Editor updates both MP4 + DB |

## 📚 Documentation Files

- **`DATABASE_MIGRATION.md`** - Complete documentation
- **`CONVERSION_SUMMARY.md`** - Migration summary
- **`database_schema.sql`** - Database schema
- **`db_helper.py`** - Helper functions (docstrings)

## 💾 Backup Locations

- **Current:** `retroviewer.db`
- **Original files:** `Backups/20251215_043357/`

---

**Quick Tip:** The database is just a single file. To backup, simply copy `retroviewer.db`!
