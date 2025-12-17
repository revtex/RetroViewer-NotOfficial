import os
import db_helper

# Get the directory where the script is running
script_dir = os.path.dirname(os.path.abspath(__file__))

# Set the folder path
folder_path = os.path.join(script_dir, "VideoFiles")

print("Scanning VideoFiles directory and syncing with database...")

try:
    # Try to sync with database
    added, removed = db_helper.scan_and_sync_videos(folder_path)

    print(f"✓ Scan complete:")
    print(f"  - Added: {added} new videos")
    print(f"  - Removed: {removed} deleted videos")

    # Get all videos from database
    all_videos = db_helper.get_all_videos()
    print(f"  - Total videos in database: {len(all_videos)}")

    # Update the file_list playlist
    print("\nUpdating 'file_list' playlist...")

    # Get or create file_list playlist
    playlist = db_helper.get_playlist_by_name("file_list")
    if not playlist:
        db_helper.create_playlist("file_list", "All videos in VideoFiles directory")

    # Clear and rebuild playlist
    db_helper.clear_playlist("file_list")
    for position, video in enumerate(all_videos, 1):
        db_helper.add_video_to_playlist("file_list", video['filename'], position)

    print(f"✓ Playlist 'file_list' updated with {len(all_videos)} videos")

    # Export to text file for backward compatibility
    output_file = os.path.join(script_dir, "Playlist", "file_list.txt")
    db_helper.export_playlist_to_file("file_list", output_file)
    print(f"✓ Exported to {output_file}")

except Exception as e:
    # Fallback to text file only (backward compatibility)
    print(f"\n⚠️  WARNING: Database not available ({e})")
    print("    Falling back to text-file only mode.")
    print("    Recommendation: Run 'python3 Utilities/setup_database.py' to set up database.\n")
    
    # Scan directory and create text file
    if not os.path.isdir(folder_path):
        print(f"Error: Directory '{folder_path}' not found")
        exit(1)
    
    video_files = []
    for filename in sorted(os.listdir(folder_path)):
        if filename.lower().endswith(".mp4"):
            video_files.append(filename)
    
    # Create Playlist directory if needed
    playlist_dir = os.path.join(script_dir, "Playlist")
    os.makedirs(playlist_dir, exist_ok=True)
    
    # Write to text file
    output_file = os.path.join(playlist_dir, "file_list.txt")
    with open(output_file, 'w', encoding='utf-8') as f:
        for filename in video_files:
            f.write(f"{filename}\n")
    
    print(f"✓ Scan complete: {len(video_files)} videos found")
    print(f"✓ Created text file: {output_file}")
