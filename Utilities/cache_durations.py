#!/usr/bin/env python3
"""
Cache video durations for all videos in the database.
Run this once to populate duration cache for faster EPG generation.
"""

import os
import sys
import subprocess
import json

# Add Scripts directory to path for db_helper
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.dirname(SCRIPT_DIR)
sys.path.insert(0, os.path.join(BASE_DIR, 'Scripts'))

import db_helper

def get_video_duration_ffprobe(file_path):
    """Get video duration using ffprobe. Returns None if unable to determine."""
    try:
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
    except FileNotFoundError:
        print("\n❌ Error: ffprobe not found!")
        print("Please install FFmpeg:")
        print("  • Linux: sudo apt-get install ffmpeg")
        print("  • macOS: brew install ffmpeg")
        print("  • Windows: Download from https://ffmpeg.org/download.html")
        sys.exit(1)
    except Exception as e:
        print(f"Error probing video: {e}")
    
    return None


def main():
    print("=" * 60)
    print("RetroViewer Duration Cache Builder")
    print("=" * 60)
    
    # Get all videos
    videos = db_helper.get_all_videos()
    
    if not videos:
        print("\n❌ No videos found in database")
        print("Run setup_database.py first to import videos")
        return
    
    # Count videos without durations
    needs_caching = sum(1 for v in videos if v.get('duration') is None)
    
    print(f"\nFound {len(videos)} videos in database")
    print(f"  • {len(videos) - needs_caching} already have cached durations")
    print(f"  • {needs_caching} need duration caching")
    
    if needs_caching == 0:
        print("\n✓ All videos already have cached durations!")
        return
    
    print(f"\nCaching durations for {needs_caching} videos...")
    print("(This may take a few minutes)")
    
    cached = 0
    failed = 0
    
    for i, video in enumerate(videos, 1):
        if video.get('duration') is not None:
            continue  # Skip already cached
        
        filename = video['filename']
        file_path = db_helper.get_absolute_path(video['file_path'])
        
        if not os.path.exists(file_path):
            print(f"  [{i}/{len(videos)}] ⚠️  File not found: {filename}")
            failed += 1
            continue
        
        duration = get_video_duration_ffprobe(file_path)
        
        if duration is not None:
            db_helper.set_video_duration(filename, duration)
            cached += 1
            if cached % 25 == 0:
                print(f"  Cached {cached}/{needs_caching} durations...")
        else:
            failed += 1
    
    print(f"\n✓ Duration caching complete!")
    print(f"  • Cached: {cached}")
    print(f"  • Failed/Missing: {failed}")
    print(f"\nEPG generation will now use cached durations for instant startup!")


if __name__ == "__main__":
    main()
