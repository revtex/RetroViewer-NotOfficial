# Docker Quick Reference

## Start StreamServer
```bash
cd docker
docker-compose up -d
```

## Access StreamServer
- **Web Interface:** http://localhost:5000
- **M3U Playlist:** http://localhost:5000/playlist.m3u
- **EPG Guide:** http://localhost:5000/epg.xml

## Common Commands
```bash
# View logs
docker-compose logs -f

# Stop
docker-compose down

# Restart
docker-compose restart

# Rebuild after changes
docker-compose build --no-cache

# Shell access
docker-compose exec streamserver bash

# Check database
docker-compose exec streamserver sqlite3 Database/retroviewer.db "SELECT COUNT(*) FROM videos;"

# Recache durations
docker-compose exec streamserver python3 Utilities/cache_durations.py
```

## What's Installed
- Python 3.11
- FFmpeg (duration detection)
- Flask + Waitress (HTTP server)
- SQLite3 (database)

## What's NOT Installed
- VLC (GUI apps only)
- Tkinter (GUI apps only)
- Mutagen (Manager only)

## Volumes
- `../Data` → `/app/Data` (videos, playlists, settings)
- `../Database` → `/app/Database` (SQLite database)

## Entrypoint
The `entrypoint.sh` script automatically:
1. Creates database if missing
2. Caches video durations
3. Validates setup
4. Starts StreamServer

## Troubleshooting
```bash
# Port already in use
# Edit docker-compose.yml: "8080:5000"

# Check container status
docker-compose ps

# View full logs
docker-compose logs --tail=100

# Fresh start
docker-compose down
docker-compose up -d --build
```

See [README.md](README.md) for full documentation.
