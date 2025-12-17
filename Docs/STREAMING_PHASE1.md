# RetroViewer Streaming Server - Phase 1 Documentation

## Overview
Phase 1 implements basic M3U playlist generation and HTTP streaming infrastructure for RetroViewer. This allows users to stream their RetroViewer content to any IPTV-compatible player (VLC, Kodi, TiviMate, etc.) across their network.

**Status:** ✅ Complete  
**Date:** December 16, 2025

---

## What's New

### StreamServer.py
New Python script that provides HTTP-based streaming of RetroViewer content.

**Location:** `Scripts/StreamServer.py`

**Dependencies:**
- Flask (HTTP server framework)
- Existing RetroViewer database (`db_helper.py`)

### Key Features Implemented

#### 1. **M3U Playlist Generation**
- Automatically generates M3U playlist from database playlists
- Each playlist becomes a "channel" in the M3U
- Compatible with standard IPTV apps
- Dynamic generation (always reflects current database state)

#### 2. **Web Interface**
- Clean HTML interface at `http://localhost:8080/`
- Channel listing page showing all available streams
- Download links for M3U playlist
- Instructions for IPTV player setup

#### 3. **Video Streaming**
- HTTP-based video serving
- Direct file streaming (no transcoding in Phase 1)
- Serves from both `VideoFiles/` (commercials) and `MediaFiles/` (features)

#### 4. **Channel System**
- Maps database playlists to streaming channels
- Automatic channel numbering
- Filters empty playlists from channel list

---

## Usage

### Starting the Server

**Via Launcher (Recommended):**
```bash
# Windows
launch.bat
# Select option 4: Stream Server

# Linux/macOS
./launch.sh
# Select option 4: Stream Server
```

**Direct Execution:**
```bash
python3 Scripts/StreamServer.py
```

Server will start on `http://0.0.0.0:8080` (accessible from network)

### Accessing Content

#### Web Browser
1. Navigate to `http://localhost:8080/`
2. View channel list or download M3U file
3. Copy M3U URL for IPTV apps: `http://[YOUR_IP]:8080/playlist.m3u`

#### IPTV Player (VLC, Kodi, etc.)
1. Download M3U file from web interface
2. OR add M3U URL directly: `http://[YOUR_IP]:8080/playlist.m3u`
3. Open in your IPTV player
4. Select a channel to start streaming

---

## API Endpoints

### `GET /`
**Description:** Web interface home page  
**Returns:** HTML with navigation links

### `GET /playlist.m3u`
**Description:** M3U playlist file  
**Returns:** M3U format playlist (MIME: `application/x-mpegurl`)  
**Structure:**
```
#EXTM3U
#EXTINF:-1 tvg-id="1" tvg-name="1990's Christmas" group-title="RetroViewer",1990's Christmas
http://[HOST]/stream/1990's%20Christmas
#EXTINF:-1 tvg-id="2" tvg-name="Halloween" group-title="RetroViewer",Halloween
http://[HOST]/stream/Halloween
...
```

### `GET /channels`
**Description:** HTML channel listing  
**Returns:** HTML table with all channels, video counts, descriptions

### `GET /stream/<playlist_name>`
**Description:** Stream a playlist channel  
**Returns:** Video file (MP4)  
**Phase 1 Note:** Currently serves first video only (will loop entire playlist in Phase 2)

### `GET /video/<filename>`
**Description:** Serve individual video file  
**Returns:** Video file (MP4)  
**Searches:** Both `VideoFiles/` and `MediaFiles/` directories

---

## Architecture

### Component Integration
```
Database (retroviewer.db)
       ↓
   db_helper.py (data access layer)
       ↓
StreamServer.py (Flask HTTP server)
       ↓
   M3U/HTTP Endpoints
       ↓
  IPTV Players (network clients)
```

### Server Configuration
- **Host:** `0.0.0.0` (all network interfaces)
- **Port:** `8080`
- **Protocol:** HTTP (HTTPS planned for future phase)
- **Debug Mode:** Disabled (production mode)

---

## Limitations (Phase 1)

These are intentional limitations to be addressed in future phases:

1. **Single Video Per Channel**
   - Streams only the first video from each playlist
   - No automatic progression to next video
   - **Future:** Phase 3 will implement full playlist looping

2. **No Commercial Breaks**
   - Feature movies play without commercial insertion
   - Feature player logic not yet integrated
   - **Future:** Phase 4 will add timed commercial breaks

3. **No EPG (Electronic Program Guide)**
   - XMLTV not yet implemented
   - No program schedule information
   - **Future:** Phase 2 will add XMLTV guide

4. **No Transcoding**
   - Serves files as-is (MP4 format)
   - Client must support codec
   - **Future:** Optional ffmpeg transcoding in Phase 3+

5. **No Authentication**
   - Open access to anyone on network
   - No user accounts or passwords
   - **Future:** Optional authentication in Phase 5

6. **No Time-Based Programming**
   - Channels don't change content based on time of day
   - No scheduled playlists
   - **Future:** Phase 5 will add scheduling

---

## Network Access

### Local Network Access
Replace `localhost` with your server's IP address:
- Find IP: `ipconfig` (Windows) or `ifconfig` (Linux/macOS)
- Access from other devices: `http://[SERVER_IP]:8080/`
- Add to IPTV app: `http://[SERVER_IP]:8080/playlist.m3u`

### Port Forwarding (Optional)
To access outside your local network:
1. Configure router port forwarding: External → `[SERVER_IP]:8080`
2. Use external IP or dynamic DNS service
3. **Security Warning:** Consider authentication before exposing to internet

---

## Testing

### Verify Server is Running
```bash
curl http://localhost:8080/
# Should return HTML welcome page

curl http://localhost:8080/playlist.m3u
# Should return M3U playlist
```

### Test in VLC
```bash
vlc http://localhost:8080/playlist.m3u
```

### Check Available Channels
Open browser: `http://localhost:8080/channels`

---

## Troubleshooting

### Port Already in Use
**Error:** `Address already in use`  
**Solution:** Change port in `StreamServer.py` line 17: `PORT = 8080` → `PORT = 8081`

### No Channels Showing
**Cause:** All playlists are empty  
**Solution:** Add videos to playlists using Manager.py

### Videos Not Playing
**Cause:** File path issues or missing videos  
**Check:** 
- Files exist in `Data/VideoFiles/` or `Data/MediaFiles/`
- Database paths are correct (use Manager.py to verify)

### Can't Access from Other Devices
**Causes:**
- Firewall blocking port 8080
- Server not listening on `0.0.0.0`
- Wrong IP address

**Solutions:**
- Add firewall exception for port 8080
- Verify `HOST = "0.0.0.0"` in `StreamServer.py`
- Use correct server IP (not `127.0.0.1`)

---

## File Changes

### New Files
- `Scripts/StreamServer.py` - Main streaming server implementation

### Modified Files
- `launch.bat` - Added Stream Server option (4)
- `launch.sh` - Added Stream Server option (4)
- `launch.ps1` - Added Stream Server option (4)

### Dependencies Added
Will be added to `requirements.txt` in future update:
- `flask` - HTTP server framework

---

## Next Steps: Phase 2

**Goal:** Add XMLTV Electronic Program Guide

**Features to Implement:**
- `/guide.xml` endpoint for EPG data
- Calculate program schedules from video durations
- 24-hour rolling program guide
- XMLTV-compliant format for IPTV apps
- Channel logos and metadata

**Benefits:**
- Clients show "what's on now" and "what's next"
- Better TV-like experience
- Program names and descriptions in guide

---

## Performance Notes

### Current Performance
- **Startup Time:** < 1 second
- **M3U Generation:** Instant (database query)
- **Video Serving:** Direct file serving (no CPU overhead)
- **Concurrent Clients:** Limited by network bandwidth

### Resource Usage
- **CPU:** Minimal (Flask + file serving only)
- **RAM:** ~50-100 MB
- **Network:** Depends on video bitrate × client count
- **Storage:** No additional storage (uses existing video files)

---

## Security Considerations

### Phase 1 Security Status
- ⚠️ No authentication
- ⚠️ No encryption (HTTP, not HTTPS)
- ✓ Read-only access (no file modification)
- ✓ Path validation (prevents directory traversal)

### Recommendations
- Use only on trusted local networks
- Do not expose to internet without authentication
- Consider VPN for remote access
- HTTPS implementation planned for future phase

---

## Development Notes

### Code Structure
```python
# Flask app initialization
app = Flask(__name__)

# Routes
/           → index()        # Web interface
/playlist.m3u → playlist()   # M3U generation
/channels   → channels()     # Channel list
/stream/<name> → stream()    # Video streaming
/video/<file> → serve_video() # Direct file serving
```

### Database Integration
Uses existing `db_helper.py` functions:
- `get_all_playlists()` - Get channel list
- `get_playlist_videos()` - Get videos for channel
- No database modifications (read-only)

### URL Encoding
Playlist names are URL-encoded in M3U for special characters:
- Spaces: `%20`
- Apostrophes: `%27`
- Example: `1990's Christmas` → `1990%27s%20Christmas`

---

## Support

### Compatible IPTV Players Tested
- ✅ VLC Media Player
- ✅ Kodi (with PVR IPTV Simple Client)
- ⏳ TiviMate (pending test)
- ⏳ Perfect Player (pending test)

### Known Working Clients
Any player that supports:
- M3U playlists
- HTTP streaming
- MP4/H.264 video codec

---

## Changelog

### Version 1.0 - Phase 1 (December 16, 2025)
- ✅ Initial release
- ✅ M3U playlist generation
- ✅ HTTP video streaming
- ✅ Web interface
- ✅ Channel listing
- ✅ Launcher integration

---

## Future Phases Overview

### Phase 2: XMLTV EPG (Next)
- Electronic program guide generation
- Schedule calculation from video durations
- XMLTV format output

### Phase 3: Continuous Streaming
- Full playlist looping (not just first video)
- HLS streaming implementation
- Playlist progression logic

### Phase 4: Commercial Breaks
- Integrate FeaturePlayer commercial insertion logic
- Timed ad breaks for feature movies
- Dynamic stream composition

### Phase 5: Advanced Features
- Time-based channel programming
- Multiple simultaneous channels
- Authentication and encryption
- Web UI for administration

---

## Conclusion

Phase 1 establishes the foundation for RetroViewer's streaming capabilities. While limited to basic functionality, it proves the concept and provides immediate value by making content accessible to IPTV players across the network.

The modular architecture allows incremental enhancement in future phases while maintaining compatibility with existing RetroViewer components (MediaPlayer, FeaturePlayer, Manager).

**Phase 1 Status:** ✅ Complete and Ready for Testing
