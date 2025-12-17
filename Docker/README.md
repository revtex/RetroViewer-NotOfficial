# RetroViewer Docker Setup

## Quick Start

StreamServer is the only application designed to run in Docker - it's a headless IPTV/EPG web server that requires no display or GUI.

```bash
# Navigate to docker directory
cd docker

# Build and start StreamServer
docker-compose up -d

# Access the web interface
open http://localhost:5000
```

**Features:**
- 📺 IPTV M3U playlist at `http://localhost:5000/playlist.m3u`
- 📅 EPG guide at `http://localhost:5000/epg.xml`
- 🌐 Web interface for settings and control
- 🖥️ No display required (perfect for headless servers)
- 🔄 Auto-restart on failure
- ❤️ Health checks included

**Note:** GUI applications (Manager, Media Player, Feature Player) require VLC and display access, so they should be run directly on your host system using the launcher scripts.

## Directory Structure

```
RetroViewer/
├── Data/                    # Persistent data (mounted as volume)
│   ├── VideoFiles/         # Your commercial videos
│   ├── MediaFiles/         # Your feature movies
│   ├── Playlists/          # Playlist files
│   ├── Timestamps/         # Commercial break timestamps
│   └── Settings/           # Application settings
├── Database/               # SQLite database (mounted as volume)
│   └── retroviewer.db
├── docker/                 # Docker configuration
│   ├── Dockerfile         # Minimal StreamServer image
│   ├── docker-compose.yml # Service orchestration
│   ├── entrypoint.sh      # Container startup script
│   ├── requirements.txt   # Minimal Python dependencies
│   └── README.md          # This file
└── Scripts/
    ├── StreamServer.py    # IPTV/EPG server
    └── db_helper.py       # Database access
```

## Common Commands

### Build/Update
```bash
# Build the container
docker-compose build

# Pull latest changes and rebuild
git pull && docker-compose build
```

### Start/Stop
```bash
# Start StreamServer (background)
docker-compose up -d

# Start with logs visible
docker-compose up

# Stop StreamServer
docker-compose down

# Restart after changes
docker-compose restart
```

### View Logs
```bash
# Follow logs in real-time
docker-compose logs -f

# View last 100 lines
docker-compose logs --tail=100
```

### Database Operations
```bash
# Access database directly
docker-compose exec streamserver sqlite3 Database/retroviewer.db

# Run setup/migration script
docker-compose run --rm streamserver python3 Utilities/setup_database.py

# Cache video durations (recommended on first run)
docker-compose run --rm streamserver python3 Utilities/cache_durations.py
```

### Access Container Shell
```bash
# Open bash shell in running container
docker-compose exec streamserver bash

# Run one-off command
docker-compose run --rm streamserver ls -la Data/VideoFiles/
```

## Prerequisites

**Before running the container**, you need:

1. **Database initialized**: Run `python3 Utilities/setup_database.py` once
2. **Videos in Data/VideoFiles/**: Your commercial video files
3. **Optional**: Pre-cache durations with `python3 Utilities/cache_durations.py`

## What Gets Installed

The Docker image only includes what StreamServer needs:

**System Packages:**
- FFmpeg (for video duration detection)
- SQLite3 (for database operations)
- curl (for health checks)

**Python Packages:**
- flask (HTTP server)
- waitress (WSGI server)

**NOT Included:**
- VLC player (GUI apps only)
- Tkinter/ttkbootstrap (GUI apps only)
- python-vlc (GUI apps only)
- mutagen (Manager only)

This keeps the image small (~200MB) and focused.

## Volume Configuration

### Using Host Directories
The default setup mounts parent directories:

```yaml
volumes:
  - ../Data:/app/Data          # Your videos and playlists
  - ../Database:/app/Database  # SQLite database
```

### Mount External Video Collection
Edit `docker-compose.yml` to use videos from elsewhere:

```yaml
volumes:
  - ../Database:/app/Database
  - /media/videos:/app/Data/VideoFiles:ro      # Read-only
  - /media/movies:/app/Data/MediaFiles:ro
  - ../Data/Playlists:/app/Data/Playlists
  - ../Data/Timestamps:/app/Data/Timestamps
```

## Port Configuration

Default port is **5000** for StreamServer. To change:

```yaml
ports:
  - "8080:5000"  # Access on host port 8080
```

## Troubleshooting

### StreamServer Won't Start
```bash
# Check if container is running
docker-compose ps

# View logs for errors
docker-compose logs streamserver

# Check port availability
sudo lsof -i :5000
```

### No Videos Found
```bash
# Check if volumes are mounted correctly
docker-compose exec streamserver ls -la Data/VideoFiles/

# Check database
docker-compose exec streamserver sqlite3 Database/retroviewer.db "SELECT COUNT(*) FROM videos;"

# Re-import videos
docker-compose run --rm streamserver python3 Utilities/setup_database.py
```

### Port Already in Use
```bash
# Find what's using port 5000
sudo lsof -i :5000

# Use different port in docker-compose.yml
ports:
  - "8080:5000"  # Access on http://localhost:8080
```

### Container Keeps Restarting
```bash
# Check logs for errors
docker-compose logs --tail=50 streamserver

# Check health status
docker inspect retroviewer-stream | grep -A 10 Health
```

### Permission Errors
```bash
# Fix ownership of Data and Database directories
sudo chown -R $(id -u):$(id -g) Data/ Database/

# Or run container as your user
user: "${UID}:${GID}"
```

## Running GUI Applications

The GUI applications (Manager, Media Player, Feature Player) are **not designed for Docker** as they require:
- VLC video player with display output
- Direct X11/display access
- Audio output
- Keyboard/mouse input

**Instead, run GUI apps directly on your host:**

```bash
# On Linux/macOS
./launch.sh

# On Windows
launch.bat
# or
launch.ps1
```

**Manager** can still interact with the dockerized StreamServer's database:
- Edit `Data/` and `Database/` directories (shared with container via volumes)
- Changes are immediately visible to StreamServer
- No need to restart container

## Development Mode

For active development with live code changes:

```yaml
services:
  streamserver:
    build: .
    volumes:
      - ./Data:/app/Data
      - ./Database:/app/Database
      - ./Scripts:/app/Scripts  # Live code updates
      - ./Utilities:/app/Utilities
    environment:
      - FLASK_ENV=development
      - FLASK_DEBUG=1
```

Then:
```bash
docker-compose up
# Code changes in Scripts/ will be reflected immediately
# (may need to restart container for some changes)
```

## Database Setup

Before first run, initialize the database:

```bash
# From project root
python3 Utilities/setup_database.py

# Or from within container
docker-compose run --rm streamserver python3 Utilities/setup_database.py
```

StreamServer will:
- ✅ Use existing database if available
- ✅ Cache video durations on-demand during EPG generation
- ✅ Continue working even if some durations aren't cached

For faster startup, pre-cache all durations:
```bash
docker-compose run --rm streamserver python3 Utilities/cache_durations.py
```

## Production Deployment

### Using Docker Compose
```bash
cd docker

# Run in background
docker-compose up -d

# Auto-restart is already configured
# (restart: unless-stopped in docker-compose.yml)
```

### Using Docker Build/Run
```bash
cd docker

# Build image
docker build -t retroviewer:latest -f Dockerfile ..

# Run container
docker run -d \
  --name retroviewer \
  -p 5000:5000 \
  -v "$(pwd)/../Data:/app/Data" \
  -v "$(pwd)/../Database:/app/Database" \
  --restart unless-stopped \
  retroviewer:latest
```

### Behind Reverse Proxy (nginx)
```nginx
location / {
    proxy_pass http://localhost:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
}
```

## Environment Variables

Available environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DISPLAY` | `:0` | X11 display for GUI apps |
| `PYTHONUNBUFFERED` | `1` | Show Python output immediately |
| `FLASK_ENV` | `production` | Flask environment mode |
| `FLASK_DEBUG` | `0` | Enable Flask debug mode |

## Performance Tips

1. **Cache durations on first run:**
   ```bash
   docker-compose run --rm streamserver python3 Utilities/cache_durations.py
   ```

2. **Use SSD storage** for Data/Database volumes

3. **Increase shared memory** for VLC (if needed):
   ```yaml
   shm_size: '2gb'
   ```

4. **Resource limits** for production:
   ```yaml
   deploy:
     resources:
       limits:
         cpus: '2'
         memory: 2G
   ```

## Support

For issues, see:
- Main README.md
- Docs/DATABASE_MIGRATION.md
- Docs/DURATION_CACHE_FIX.md

## License

See main project LICENSE file.
