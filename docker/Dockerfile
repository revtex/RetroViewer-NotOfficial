# RetroViewer StreamServer Dockerfile
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install minimal system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    # FFmpeg for video duration detection
    ffmpeg \
    # SQLite CLI for database operations
    sqlite3 \
    # curl for health checks
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy minimal requirements and install Python dependencies
COPY docker/requirements.txt /app/docker/requirements.txt
RUN pip install --no-cache-dir -r docker/requirements.txt

# Copy only files needed for StreamServer
COPY Scripts/StreamServer.py ./Scripts/
COPY Scripts/db_helper.py ./Scripts/
COPY Utilities/cache_durations.py ./Utilities/
COPY Utilities/setup_database.py ./Utilities/
COPY Database/database_schema.sql ./Database/

# Create data directories
RUN mkdir -p Data/VideoFiles Data/MediaFiles Data/Playlists Data/Timestamps Data/Settings Database

# Expose StreamServer port
EXPOSE 5000

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/Scripts

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Default command
CMD ["python3", "Scripts/StreamServer.py"]
