#!/usr/bin/env python3
"""
RetroViewer Stream Server
M3U/XMLTV streaming server for RetroViewer content
Provides IPTV-compatible streaming of playlists and feature movies with EPG
"""

import os
import sys
import logging
import subprocess
from datetime import datetime, timedelta
from flask import Flask, Response, send_file, request
from urllib.parse import quote
import xml.etree.ElementTree as ET
from xml.dom import minidom
import db_helper

# Try to import production server (Waitress)
try:
    from waitress import serve
    PRODUCTION_SERVER = True
except ImportError:
    PRODUCTION_SERVER = False

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('waitress')

# ---------- Configuration ----------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
VIDEO_FOLDER = os.path.join(BASE_DIR, "Data", "VideoFiles")
MEDIA_FOLDER = os.path.join(BASE_DIR, "Data", "MediaFiles")

# Server settings
HOST = "0.0.0.0"  # Listen on all interfaces
PORT = 5000

app = Flask(__name__)

# Cache for XMLTV guide
from typing import Any
xmltv_cache: dict[str, Any] = {
    'content': None,
    'generated_at': None
}

# ---------- Helper Functions ----------

def get_base_url():
    """Get the base URL for the server (uses request context)."""
    return f"http://{request.host}"

def generate_m3u_playlist():
    """
    Generate M3U playlist with channels from database playlists.
    Creates channel list with playlist loops.
    """
    base_url = get_base_url()
    m3u_lines = ["#EXTM3U"]
    
    # Get all playlists from database
    playlists = db_helper.get_all_playlists()
    
    channel_number = 1
    for playlist in playlists:
        playlist_name = playlist['name']
        
        # Get video count for this playlist
        videos = db_helper.get_playlist_videos(playlist_name)
        if not videos:
            continue  # Skip empty playlists
        
        # Create channel entry
        # Format: #EXTINF:-1 tvg-id="channel_id" tvg-name="Channel Name" tvg-logo="" group-title="RetroViewer",Channel Name
        m3u_lines.append(f'#EXTINF:-1 tvg-id="{channel_number}" tvg-name="{playlist_name}" group-title="RetroViewer",{playlist_name}')
        m3u_lines.append(f"{base_url}/stream/{quote(playlist_name)}")
        
        channel_number += 1
    
    return "\n".join(m3u_lines)

def get_playlist_videos_paths(playlist_name):
    """Get absolute file paths for all videos in a playlist."""
    videos = db_helper.get_playlist_videos(playlist_name)
    paths = []
    for video in videos:
        filename = video['filename']
        path = os.path.join(VIDEO_FOLDER, filename)
        if os.path.exists(path):
            paths.append(path)
    return paths

def get_video_duration(video_path, filename=None):
    """
    Get video duration in seconds. Checks database cache first, then probes with ffprobe.
    Falls back to 30 seconds for commercials if unable to determine.
    """
    # Try database cache first
    if filename:
        cached_duration = db_helper.get_video_duration(filename)
        if cached_duration is not None:
            logger.debug(f"Using cached duration for {filename}: {cached_duration}s")
            return cached_duration
    
    duration = 30.0  # Default fallback
    
    try:
        # Use ffprobe (part of ffmpeg) - much faster and more reliable than VLC
        result = subprocess.run(
            [
                'ffprobe', 
                '-v', 'quiet',
                '-print_format', 'json',
                '-show_format',
                video_path
            ],
            capture_output=True,
            text=True,
            timeout=1.5,
            check=False
        )
        
        if result.returncode == 0 and result.stdout:
            import json
            data = json.loads(result.stdout)
            if 'format' in data and 'duration' in data['format']:
                duration = float(data['format']['duration'])
                if duration > 0:
                    # Save to database for future use
                    if filename:
                        db_helper.set_video_duration(filename, duration)
                        logger.debug(f"Cached duration for {filename}: {duration}s")
                    return duration
    except subprocess.TimeoutExpired:
        logger.warning(f"Timeout: {os.path.basename(video_path)}")
    except FileNotFoundError:
        pass  # ffprobe not installed
    except Exception as e:
        logger.debug(f"Error probing {os.path.basename(video_path)}: {e}")
    
    # Save fallback to database too (so we don't keep retrying)
    if filename:
        db_helper.set_video_duration(filename, duration)
    
    return duration

def generate_xmltv_guide():
    """
    Generate XMLTV Electronic Program Guide (EPG).
    Creates 24-hour rolling schedule based on video durations.
    """
    logger.info("Starting XMLTV guide generation")
    
    # Pre-load all video durations from database for fast access
    all_videos = db_helper.get_all_videos()
    duration_cache = {v['filename']: v.get('duration') for v in all_videos if v.get('duration')}
    logger.info(f"Pre-loaded {len(duration_cache)} cached durations from database")
    
    # Create root element
    tv = ET.Element('tv', {
        'generator-info-name': 'RetroViewer',
        'generator-info-url': 'https://github.com/RetroViewer'
    })
    
    # Get all playlists
    playlists = db_helper.get_all_playlists()
    logger.info(f"Found {len(playlists)} playlists")
    
    # Current time as schedule start
    schedule_start = datetime.now()
    
    channel_number = 1
    
    # Track globally processed videos to avoid duplicates across playlists
    global_processed_videos = set()
    
    for playlist in playlists:
        playlist_name = playlist['name']
        videos = db_helper.get_playlist_videos(playlist_name)
        
        if not videos:
            continue  # Skip empty playlists
        
        logger.info(f"Processing playlist '{playlist_name}' with {len(videos)} videos")
        
        # Add channel definition
        channel_id = f"retroviewer.{channel_number}"
        channel = ET.SubElement(tv, 'channel', {'id': channel_id})
        
        display_name = ET.SubElement(channel, 'display-name')
        display_name.text = playlist_name
        
        # Add icon if available (future enhancement)
        # icon = ET.SubElement(channel, 'icon', {'src': f'/logos/{quote(playlist_name)}.png'})
        
        # Generate 24-hour program schedule
        current_time = schedule_start
        end_time = schedule_start + timedelta(hours=24)
        video_index = 0
        
        # Track unique videos processed in this playlist
        processed_in_playlist = set()
        
        while current_time < end_time:
            filename = "unknown"  # Initialize for error handling
            try:
                video = videos[video_index % len(videos)]
                filename = video['filename']
                title = video.get('title', filename)
                
                # Show progress for unique videos (only first time globally)
                if filename not in processed_in_playlist:
                    processed_in_playlist.add(filename)
                    if filename not in global_processed_videos:
                        global_processed_videos.add(filename)
                        logger.info(f"  [{len(global_processed_videos)}] Processing: {filename}")
                
                # Get video duration from pre-loaded cache
                duration_seconds: float
                if filename in duration_cache:
                    duration_seconds = duration_cache[filename] or 30.0
                else:
                    # Not cached - probe the file
                    video_path = os.path.join(VIDEO_FOLDER, filename)
                    if os.path.exists(video_path):
                        duration_seconds = get_video_duration(video_path, filename) or 30.0
                        duration_cache[filename] = duration_seconds  # Add to cache
                    else:
                        duration_seconds = 30.0  # Default 30 seconds for missing files
                        logger.warning(f"Video file not found: {filename}")
                
                program_end = current_time + timedelta(seconds=duration_seconds)
            except Exception as e:
                logger.error(f"Error processing video {filename}: {e}")
                # Use fallback values and continue
                duration_seconds = 180.0
                program_end = current_time + timedelta(seconds=duration_seconds)
                title = "Error loading video"
                video = {'filename': filename, 'title': title, 'tags': '', 'year': ''}  # Initialize for desc section
            
            # Add programme element
            programme = ET.SubElement(tv, 'programme', {
                'start': current_time.strftime('%Y%m%d%H%M%S %z'),
                'stop': program_end.strftime('%Y%m%d%H%M%S %z'),
                'channel': channel_id
            })
            
            # Programme title
            title_elem = ET.SubElement(programme, 'title', {'lang': 'en'})
            title_elem.text = title
            
            # Programme description (use tags if available)
            desc = ET.SubElement(programme, 'desc', {'lang': 'en'})
            tags = video.get('tags', '') if video else ''
            year = video.get('year', '') if video else ''
            desc_text = f"RetroViewer: {playlist_name}"
            if tags and tags != 'Unknown':
                desc_text += f" | Tags: {tags}"
            if year and year != 'Unknown':
                desc_text += f" | Year: {year}"
            desc.text = desc_text
            
            # Category
            category = ET.SubElement(programme, 'category', {'lang': 'en'})
            category.text = 'Commercial' if 'commercial' in playlist_name.lower() else 'Entertainment'
            
            # Move to next video
            current_time = program_end
            video_index += 1
        
        channel_number += 1
    
    # Convert to pretty XML string
    xml_str = ET.tostring(tv, encoding='utf-8', method='xml')
    dom = minidom.parseString(xml_str)
    pretty_xml = dom.toprettyxml(indent='  ', encoding='UTF-8')
    
    # Remove empty lines
    lines = [line for line in pretty_xml.decode('utf-8').split('\n') if line.strip()]
    logger.info("XMLTV guide generation complete")
    return '\n'.join(lines)

def refresh_xmltv_cache():
    """Regenerate and cache the XMLTV guide."""
    logger.info("Refreshing XMLTV cache...")
    try:
        xmltv_cache['content'] = generate_xmltv_guide()
        xmltv_cache['generated_at'] = datetime.now()
        logger.info(f"XMLTV cache refreshed at {xmltv_cache['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
        return True
    except Exception as e:
        logger.error(f"Failed to refresh XMLTV cache: {e}", exc_info=True)
        # Don't raise - let server continue without EPG
        return False

# ---------- Routes ----------

@app.route('/')
def index():
    """Welcome page with links to M3U and guide."""
    base_url = get_base_url()
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>RetroViewer Stream Server</title>
        <style>
            body {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 800px;
                margin: 50px auto;
                padding: 20px;
                background-color: #1a1a1a;
                color: #ffffff;
            }}
            h1 {{
                color: #00ff00;
                text-align: center;
            }}
            .info {{
                background-color: #2a2a2a;
                padding: 20px;
                border-radius: 8px;
                margin: 20px 0;
            }}
            .link {{
                display: block;
                padding: 15px;
                margin: 10px 0;
                background-color: #0066cc;
                color: white;
                text-decoration: none;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }}
            .link:hover {{
                background-color: #0052a3;
            }}
            .note {{
                color: #ffaa00;
                margin-top: 30px;
                padding: 15px;
                background-color: #332200;
                border-radius: 5px;
            }}
            .refresh-btn {{
                display: block;
                padding: 15px;
                margin: 10px 0;
                background-color: #cc6600;
                color: white;
                border: none;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
                font-size: 16px;
                cursor: pointer;
                text-decoration: none;
            }}
            .refresh-btn:hover {{
                background-color: #aa5500;
            }}
            .refresh-btn:disabled {{
                background-color: #666666;
                cursor: not-allowed;
            }}
            #status {{
                margin-top: 10px;
                padding: 10px;
                border-radius: 5px;
                text-align: center;
                display: none;
            }}
            .status-loading {{
                background-color: #334455;
                color: #88aaff;
            }}
            .status-success {{
                background-color: #224422;
                color: #88ff88;
            }}
            .status-error {{
                background-color: #442222;
                color: #ff8888;
            }}
        </style>
        <script>
            async function refreshEPG() {{
                const btn = document.getElementById('refreshBtn');
                const status = document.getElementById('status');
                
                // Disable button and show loading
                btn.disabled = true;
                btn.textContent = '⏳ Refreshing EPG...';
                status.className = 'status-loading';
                status.textContent = 'Generating XMLTV guide (this may take a few minutes)...';
                status.style.display = 'block';
                
                try {{
                    const response = await fetch('/refresh-guide');
                    const text = await response.text();
                    
                    if (response.ok) {{
                        status.className = 'status-success';
                        status.textContent = '✓ ' + text;
                        setTimeout(() => {{
                            status.style.display = 'none';
                        }}, 5000);
                    }} else {{
                        status.className = 'status-error';
                        status.textContent = '✗ Failed: ' + text;
                    }}
                }} catch (error) {{
                    status.className = 'status-error';
                    status.textContent = '✗ Error: ' + error.message;
                }} finally {{
                    btn.disabled = false;
                    btn.textContent = '🔄 Refresh EPG';
                }}
            }}
        </script>
    </head>
    <body>
        <h1>🎬 RetroViewer Stream Server</h1>
        
        <div class="info">
            <h2>IPTV Streaming with EPG Support</h2>
            <p>Streaming server is running with Electronic Program Guide! Use the links below to access your content:</p>
        </div>
        
        <a href="/playlist.m3u" class="link">📺 Download M3U Playlist</a>
        <a href="/guide.xml" class="link">📅 Download XMLTV Guide (EPG)</a>
        <a href="/channels" class="link">📋 View Channel List</a>
        
        <button id="refreshBtn" class="refresh-btn" onclick="refreshEPG()">🔄 Refresh EPG</button>
        <div id="status"></div>
        
        <div class="note">
            <strong>How to use:</strong>
            <ol>
                <li>Download the M3U playlist file</li>
                <li>Download the XMLTV guide (optional but recommended)</li>
                <li>Add both to your IPTV player (VLC, Kodi, TiviMate, etc.)</li>
                <li>Enjoy program guide with schedule information!</li>
            </ol>
            <p><strong>M3U URL:</strong> <code>{base_url}/playlist.m3u</code></p>
            <p><strong>EPG URL:</strong> <code>{base_url}/guide.xml</code></p>
            <p><strong>Note:</strong> EPG is generated at server startup. Click the "Refresh EPG" button above after adding/modifying videos or playlists.</p>
        </div>
    </body>
    </html>
    """
    return html

@app.route('/playlist.m3u')
def playlist():
    """Serve M3U playlist file."""
    m3u_content = generate_m3u_playlist()
    return Response(m3u_content, mimetype='application/x-mpegurl')

@app.route('/guide.xml')
def guide():
    """Serve cached XMLTV Electronic Program Guide."""
    if xmltv_cache['content'] is None:
        return Response("EPG not yet generated. Please wait and refresh.", status=503)
    
    return Response(xmltv_cache['content'], mimetype='application/xml')

@app.route('/refresh-guide')
def refresh_guide():
    """Manually trigger EPG regeneration."""
    try:
        logger.info("Manual EPG refresh triggered")
        refresh_xmltv_cache()
        return Response("EPG refreshed successfully", mimetype='text/plain')
    except Exception as e:
        logger.error(f"Error refreshing EPG: {e}", exc_info=True)
        return Response(f"Error: {e}", status=500)

@app.route('/channels')
def channels():
    """Display available channels in HTML format."""
    playlists = db_helper.get_all_playlists()
    
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>RetroViewer Channels</title>
        <style>
            body {
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 1000px;
                margin: 50px auto;
                padding: 20px;
                background-color: #1a1a1a;
                color: #ffffff;
            }
            h1 {
                color: #00ff00;
                text-align: center;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 20px;
            }
            th, td {
                padding: 12px;
                text-align: left;
                border-bottom: 1px solid #444;
            }
            th {
                background-color: #0066cc;
                color: white;
            }
            tr:hover {
                background-color: #2a2a2a;
            }
            .back-link {
                display: inline-block;
                margin-bottom: 20px;
                color: #00ff00;
                text-decoration: none;
            }
        </style>
    </head>
    <body>
        <a href="/" class="back-link">← Back to Home</a>
        <h1>Available Channels</h1>
        <table>
            <tr>
                <th>Channel #</th>
                <th>Name</th>
                <th>Videos</th>
                <th>Description</th>
            </tr>
    """
    
    channel_number = 1
    for playlist in playlists:
        playlist_name = playlist['name']
        description = playlist.get('description', 'No description')
        videos = db_helper.get_playlist_videos(playlist_name)
        video_count = len(videos) if videos else 0
        
        if video_count > 0:
            html += f"""
            <tr>
                <td>{channel_number}</td>
                <td><strong>{playlist_name}</strong></td>
                <td>{video_count} videos</td>
                <td>{description or '-'}</td>
            </tr>
            """
            channel_number += 1
    
    html += """
        </table>
    </body>
    </html>
    """
    return html

@app.route('/stream/<playlist_name>')
def stream(playlist_name):
    """
    Stream a playlist channel.
    Phase 1: Simple implementation - serves first video, will enhance later.
    """
    videos = get_playlist_videos_paths(playlist_name)
    
    if not videos:
        return Response(f"Playlist '{playlist_name}' is empty or not found", status=404)
    
    # Serve the video file for streaming
    first_video = videos[0]
    
    return send_file(
        first_video,
        mimetype='video/mp4',
        as_attachment=False,
        download_name=os.path.basename(first_video)
    )

@app.route('/video/<path:filename>')
def serve_video(filename):
    """Serve individual video files."""
    # Check in both VideoFiles and MediaFiles
    video_path = os.path.join(VIDEO_FOLDER, filename)
    if not os.path.exists(video_path):
        video_path = os.path.join(MEDIA_FOLDER, filename)
    
    if not os.path.exists(video_path):
        return Response(f"Video not found: {filename}", status=404)
    
    return send_file(
        video_path,
        mimetype='video/mp4',
        as_attachment=False,
        download_name=os.path.basename(video_path)
    )

# ---------- Main ----------

def main():
    """Start the streaming server."""
    print("=" * 60)
    print("RetroViewer StreamServer")
    print("=" * 60)
    
    # Database stats
    try:
        videos = db_helper.get_all_videos()
        video_count = len(videos)
        cached_count = sum(1 for v in videos if v.get('duration') is not None)
        print(f"📊 Videos in database: {video_count}")
        if video_count > 0:
            if cached_count == video_count:
                print("✅ All video durations cached")
            elif cached_count > 0:
                print(f"⏱️  Durations cached: {cached_count}/{video_count} (will cache remaining on-demand)")
            else:
                print("⚠️  No durations cached (will cache on-demand during EPG generation)")
    except Exception as e:
        print(f"⚠️  Could not read database: {e}")
    
    # Check for ffprobe
    print("")
    try:
        result = subprocess.run(['ffprobe', '-version'], capture_output=True, timeout=2)
        if result.returncode == 0:
            print("✅ ffprobe available for duration detection")
        else:
            print("⚠️  ffprobe not working properly - will use 30-second estimates")
    except FileNotFoundError:
        print("⚠️  ffprobe not found - will use 30-second duration estimates")
    except Exception as e:
        print(f"⚠️  Could not verify ffprobe: {e}")
    
    print("=" * 60)
    print("🚀 Starting StreamServer on port", PORT)
    print("=" * 60)
    
    # Generate XMLTV guide at startup
    print("\n⏳ Generating XMLTV EPG (this may take a moment)...")
    success = refresh_xmltv_cache()
    if success and xmltv_cache['generated_at']:
        print(f"✓ EPG generated successfully at {xmltv_cache['generated_at'].strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        print(f"⚠️  Warning: EPG generation incomplete or failed")
        print("   EPG may be partial or unavailable. Check logs above for details.")
        print("   Use /refresh-guide endpoint to retry after server starts.")
    
    print(f"\nAccess points:")
    print(f"  • Web Interface:  http://localhost:{PORT}/")
    print(f"  • M3U Playlist:   http://localhost:{PORT}/playlist.m3u")
    print(f"  • XMLTV Guide:    http://localhost:{PORT}/guide.xml")
    print(f"  • Refresh EPG:    http://localhost:{PORT}/refresh-guide")
    print(f"  • Channel List:   http://localhost:{PORT}/channels")
    print(f"\nFeatures:")
    print("  ✓ M3U playlist generation from database")
    print("  ✓ XMLTV Electronic Program Guide (EPG) - Cached at startup")
    print("  ✓ 24-hour rolling schedule")
    print("  ✓ Program duration calculation")
    print("  ✓ Video streaming")
    print("  ✓ Channel listing")
    
    if PRODUCTION_SERVER:
        print(f"\nUsing: Waitress (production server)")
    else:
        print(f"\nUsing: Flask development server (install waitress for production)")
    
    print(f"\nPress Ctrl+C to stop the server")
    print("=" * 60)
    
    try:
        if PRODUCTION_SERVER:
            # Use Waitress production server (no warning, better performance)
            # _quiet=False enables request logging to console
            serve(app, host=HOST, port=PORT, threads=4, _quiet=False)  # type: ignore
        else:
            # Fallback to Flask development server
            app.run(host=HOST, port=PORT, debug=False)
    except KeyboardInterrupt:
        print("\n\nServer stopped by user")
    except Exception as e:
        print(f"\nError starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
