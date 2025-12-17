-- RetroViewer SQLite Database Schema
-- This schema replaces text files for playlists, settings, timestamps, and video metadata

-- Videos table: stores all video files and their metadata
CREATE TABLE IF NOT EXISTS videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,  -- e.g., "Big Lots - Halloween, 1997.mp4"
    title TEXT,                      -- From MP4 metadata ©nam
    tags TEXT,                       -- From MP4 metadata ©too (used for filtering)
    year TEXT,                       -- From MP4 metadata ©day
    genre TEXT,                      -- From MP4 metadata ©gen
    file_path TEXT,                  -- Full path to the file
    duration REAL,                   -- Video duration in seconds (cached from ffprobe)
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Playlists table: stores playlist definitions
CREATE TABLE IF NOT EXISTS playlists (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,       -- e.g., "1990's Christmas"
    description TEXT,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Playlist_videos junction table: many-to-many relationship
CREATE TABLE IF NOT EXISTS playlist_videos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    playlist_id INTEGER NOT NULL,
    video_id INTEGER NOT NULL,
    position INTEGER,                -- Order in playlist (for non-shuffled playback)
    FOREIGN KEY (playlist_id) REFERENCES playlists(id) ON DELETE CASCADE,
    FOREIGN KEY (video_id) REFERENCES videos(id) ON DELETE CASCADE,
    UNIQUE(playlist_id, video_id)
);

-- Settings table: key-value pairs for application settings
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT,
    description TEXT,
    last_modified TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Feature movies table: stores feature-length content (from MediaFiles)
CREATE TABLE IF NOT EXISTS feature_movies (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    filename TEXT NOT NULL UNIQUE,
    title TEXT,
    file_path TEXT,
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Timestamps table: stores commercial break timestamps for feature movies
CREATE TABLE IF NOT EXISTS timestamps (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER NOT NULL,
    start_time TEXT,                 -- e.g., "0:00.00"
    end_time TEXT,                   -- e.g., "23:31.00"
    FOREIGN KEY (movie_id) REFERENCES feature_movies(id) ON DELETE CASCADE
);

-- Commercial breaks table: individual break points within a movie
CREATE TABLE IF NOT EXISTS commercial_breaks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER NOT NULL,
    break_time TEXT NOT NULL,        -- e.g., "03:18.14"
    position INTEGER,                -- Order of break (1st, 2nd, 3rd, etc.)
    FOREIGN KEY (movie_id) REFERENCES feature_movies(id) ON DELETE CASCADE
);

-- Tags table: manages available tags for video categorization
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Genres table: manages available genres for video categorization
CREATE TABLE IF NOT EXISTS genres (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Now Playing queue: ordered list of feature movies to play
CREATE TABLE IF NOT EXISTS now_playing_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    movie_id INTEGER NOT NULL,
    position INTEGER NOT NULL,       -- Play order (1, 2, 3, etc.)
    added_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (movie_id) REFERENCES feature_movies(id) ON DELETE CASCADE,
    UNIQUE(position)
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_videos_filename ON videos(filename);
CREATE INDEX IF NOT EXISTS idx_videos_tags ON videos(tags);
CREATE INDEX IF NOT EXISTS idx_videos_year ON videos(year);
CREATE INDEX IF NOT EXISTS idx_videos_genre ON videos(genre);
CREATE INDEX IF NOT EXISTS idx_playlists_name ON playlists(name);
CREATE INDEX IF NOT EXISTS idx_playlist_videos_playlist ON playlist_videos(playlist_id);
CREATE INDEX IF NOT EXISTS idx_playlist_videos_video ON playlist_videos(video_id);
CREATE INDEX IF NOT EXISTS idx_feature_movies_filename ON feature_movies(filename);
CREATE INDEX IF NOT EXISTS idx_timestamps_movie ON timestamps(movie_id);
CREATE INDEX IF NOT EXISTS idx_commercial_breaks_movie ON commercial_breaks(movie_id);
CREATE INDEX IF NOT EXISTS idx_tags_name ON tags(name);
CREATE INDEX IF NOT EXISTS idx_genres_name ON genres(name);
CREATE INDEX IF NOT EXISTS idx_now_playing_queue_position ON now_playing_queue(position);

-- Insert default settings
INSERT OR IGNORE INTO settings (key, value, description) VALUES 
    ('active_playlist', 'All Videos', 'Currently selected playlist for Media Player'),
    ('ads_per_break', '3', 'Number of ads to play during commercial breaks'),
    ('feature_playlist', 'All Videos', 'Playlist for FeaturePlayer commercials'),
    ('media_player_shuffle', 'OFF', 'Enable or disable shuffle playback in Media Player'),
    ('feature_player_shuffle', 'OFF', 'Enable or disable shuffle playback in Feature Player');
