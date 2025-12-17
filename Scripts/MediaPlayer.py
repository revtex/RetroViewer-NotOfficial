import vlc  # type: ignore
import time
import os
import tkinter as tk
import threading
import sys
import queue
import random
import db_helper

# Hide the cursor on Windows
try:
    import ctypes
    ctypes.windll.user32.ShowCursor(False)  # type: ignore
except Exception:
    pass

# ---------- Paths ----------
script_dir = os.path.dirname(os.path.abspath(__file__))
base_dir = os.path.dirname(script_dir)  # Parent of Scripts/
video_folder = os.path.join(base_dir, "Data", "VideoFiles")  # Commercial videos on disk

# All playlists and settings managed via database (db_helper)

def get_active_playlist_name():
    """Get the active playlist name from database settings."""
    return db_helper.get_setting("active_playlist", "All Videos")

def list_playlists():
    """Get all playlist names from database that have at least one video."""
    playlists = db_helper.get_all_playlists()
    if playlists:
        # Filter out empty playlists - only include those with videos
        valid_playlists = []
        for p in playlists:
            videos = db_helper.get_playlist_videos(p['name'])
            if videos:  # Only include if it has videos
                valid_playlists.append(p['name'])
        
        if valid_playlists:
            return valid_playlists
    
    print("\n⚠️  WARNING: No playlists with videos found in database.")
    print("    Please use Manager.py to create playlists and add videos.\n")
    return []

def read_playlist(playlist_name):
    """Get list of video filenames from a playlist in the database."""
    videos = db_helper.get_playlist_videos(playlist_name)
    if videos:
        # Extract just the filenames from the video records
        return [v['filename'] for v in videos]
    
    # Defensive fallback (list_playlists already filters empty playlists)
    return []

def play_videos_with_black_background(video_folder, initial_playlist_name):
    try:
        root = tk.Tk()
        root.configure(bg="black")
        
        # Fullscreen setup - maximize window first, then fullscreen
        root.state('zoomed')  # Maximize window
        root.update_idletasks()  # Process window events
        root.attributes("-fullscreen", True)  # Then go fullscreen
        root.attributes("-topmost", True)  # Keep on top
        root.config(cursor="none")
        
        # Load shuffle setting from database
        shuffle_setting = (db_helper.get_setting("media_player_shuffle", "OFF") or "OFF").upper()
        initial_shuffle_mode = shuffle_setting in ("ON", "YES")
        root.focus_force()

        video_canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        video_canvas.pack(expand=True, fill="both")

        # ----- Toast overlay (top-right) -----
        toast_ids: dict[str, int | None] = {"text": None, "shadow": None, "bg": None}
        def show_toast(message, duration_ms=2000, pad=18):
            for k in ("bg", "shadow", "text"):
                if toast_ids[k] is not None:
                    try:
                        canvas_id = toast_ids[k]
                        if canvas_id is not None:  # Type narrowing
                            video_canvas.delete(canvas_id)
                    except Exception: pass
                    toast_ids[k] = None

            video_canvas.update_idletasks()
            x = video_canvas.winfo_width() - pad
            y = pad

            toast_ids["shadow"] = video_canvas.create_text(
                x+1, y+1, text=message, fill="#000000",
                anchor="ne", font=("Segoe UI", 20, "bold")
            )
            toast_ids["text"] = video_canvas.create_text(
                x, y, text=message, fill="#FFFFFF",
                anchor="ne", font=("Segoe UI", 20, "bold")
            )
            bbox = video_canvas.bbox(toast_ids["text"])
            if bbox:
                bx0, by0, bx1, by1 = bbox
                pad_rect = 8
                toast_ids["bg"] = video_canvas.create_rectangle(
                    bx0 - pad_rect, by0 - pad_rect, bx1 + pad_rect, by1 + pad_rect,
                    fill="#202020", outline=""
                )
                video_canvas.tag_lower(toast_ids["bg"], toast_ids["shadow"])

            def remove_toast():
                for k in ("bg", "shadow", "text"):
                    if toast_ids[k] is not None:
                        try:
                            canvas_id = toast_ids[k]
                            if canvas_id is not None:  # Type narrowing
                                video_canvas.delete(canvas_id)
                        except Exception: pass
                        toast_ids[k] = None
            root.after(duration_ms, remove_toast)

        def on_resize(_event=None):
            if toast_ids["text"] is not None:
                msg = video_canvas.itemcget(toast_ids["text"], "text")
                show_toast(msg)
        root.bind("<Configure>", on_resize)

        # ----- Build playlist list from database -----
        playlists = list_playlists()
        if not playlists:
            print("No playlists found in database.")
            return

        playlist_index = [0]
        try:
            playlist_index[0] = playlists.index(initial_playlist_name)
        except ValueError:
            playlist_index[0] = 0

        # Active list of video filenames for the current playlist
        video_files = [[]]

        # ORDER controls playback sequence; holds indices into video_files[0]
        order = [[]]              # current play order (sequential or shuffled)
        video_pos = [0]           # position within 'order'

        shuffle_mode = [initial_shuffle_mode]    # Initialize from database

        def build_order():
            """(Re)build the order array based on shuffle_mode and current video_files."""
            n = len(video_files[0])
            if n == 0:
                order[0] = []
                video_pos[0] = 0
                return
            if shuffle_mode[0]:
                order[0] = list(range(n))
                random.shuffle(order[0])
            else:
                order[0] = list(range(n))
            # Clamp/reset position within range
            video_pos[0] %= max(1, len(order[0]))

        def current_video_name():
            """Return the filename at the current position."""
            if not order[0] or not video_files[0]:
                return None
            idx = order[0][video_pos[0]]
            return video_files[0][idx]

        def load_current_playlist():
            playlist_name = playlists[playlist_index[0]]
            files = read_playlist(playlist_name)
            if not files:
                print(f"Playlist '{playlist_name}' is empty or invalid. Skipping.")
                return False
            video_files[0] = files
            # Reset position and build order according to shuffle
            video_pos[0] = 0
            build_order()
            # Save active playlist to database
            db_helper.set_setting("active_playlist", playlist_name)
            print(f"\n=== Now using playlist: {playlist_name} ({len(files)} items) ===")
            root.after(0, lambda: show_toast(f"Playlist: {playlist_name}"))
            return True

        if not load_current_playlist():
            tried = 1
            while tried < len(playlists) and not video_files[0]:
                playlist_index[0] = (playlist_index[0] + 1) % len(playlists)
                if load_current_playlist():
                    break
                tried += 1
            if not video_files[0]:
                print("All playlists are empty or invalid.")
                return

        # ----- VLC setup -----
        # Suppress VLC error messages and warnings
        instance = vlc.Instance('--quiet', '--no-video-title-show')
        player = instance.media_player_new()  # type: ignore

        root.update_idletasks()
        player.set_hwnd(video_canvas.winfo_id())

        command_queue = queue.Queue()
        last_press_time: list[float] = [0.0]
        press_cooldown = 0.4  # seconds

        def load_and_play_by_pos():
            """Load and play the video pointed to by video_pos/order."""
            if not order[0] or not video_files[0]:
                return
            player.stop()
            time.sleep(0.2)

            video_name = current_video_name()
            if video_name is None:
                return
            video_path = os.path.join(video_folder, video_name)

            if not os.path.exists(video_path):
                print(f"Video file '{video_name}' not found. Skipping.")
                return

            print(f"Playing: {video_name}")
            media = instance.media_new(video_path)  # type: ignore
            player.set_media(media)
            player.set_hwnd(video_canvas.winfo_id())
            player.video_set_aspect_ratio("16:9")
            player.video_set_scale(0)
            # Don't use VLC's fullscreen - rely on Tkinter's fullscreen window instead
            # This prevents the "Failed to set fullscreen" error
            player.play()

            for _ in range(20):
                if player.get_state() == vlc.State.Playing:  # type: ignore
                    print("Playback started.")
                    return
                time.sleep(0.1)
            print("Playback failed to start.")

        def step_next():
            if not order[0]:
                return
            video_pos[0] = (video_pos[0] + 1) % len(order[0])

        def step_prev():
            if not order[0]:
                return
            video_pos[0] = (video_pos[0] - 1) % len(order[0])

        def reshuffle_current():
            """Reshuffle while trying to keep the current video playing next."""
            if not video_files[0]:
                return
            cur_name = current_video_name()
            build_order()
            # set position to the same video after reshuffle
            if cur_name in video_files[0]:
                idx = video_files[0].index(cur_name)
                try:
                    video_pos[0] = order[0].index(idx)
                except ValueError:
                    video_pos[0] = 0

        def switch_playlist(direction):
            if not playlists:
                return
            player.stop()
            count = len(playlists)
            playlist_index[0] = (playlist_index[0] + direction) % count
            start_idx = playlist_index[0]
            while True:
                if load_current_playlist():
                    break
                playlist_index[0] = (playlist_index[0] + direction) % count
                if playlist_index[0] == start_idx:
                    print("No usable playlists found (all empty/invalid).")
                    break

        def video_loop():
            while True:
                if not order[0] or not video_files[0]:
                    time.sleep(0.2)
                    continue

                load_and_play_by_pos()

                while True:
                    try:
                        command = command_queue.get(timeout=0.2)

                        if command == "next":
                            step_next()
                            break

                        elif command == "prev":
                            step_prev()
                            break

                        elif command == "plist_next":
                            switch_playlist(+1)
                            break

                        elif command == "plist_prev":
                            switch_playlist(-1)
                            break

                        elif command == "shuffle_toggle":
                            shuffle_mode[0] = not shuffle_mode[0]
                            mode = "ON" if shuffle_mode[0] else "OFF"
                            print(f"Shuffle: {mode}")
                            root.after(0, lambda: show_toast(f"Shuffle: {mode}"))
                            # rebuild order but keep current video if possible
                            reshuffle_current()
                            # do not break; keep playing current, next change applies on step
                            continue

                        elif command == "reshuffle":
                            reshuffle_current()
                            root.after(0, lambda: show_toast("Shuffle: Reshuffled"))
                            continue

                        elif command == "exit":
                            player.stop()
                            root.destroy()
                            sys.exit(0)

                    except queue.Empty:
                        if player.get_state() in [vlc.State.Ended, vlc.State.Stopped, vlc.State.Error]:  # type: ignore
                            # On wrap-around in shuffle, you can reshuffle again if desired:
                            before = video_pos[0]
                            step_next()
                            if shuffle_mode[0] and video_pos[0] == 0:
                                # Optional: auto-reshuffle after a full cycle
                                random.shuffle(order[0])
                            break

        def debounce_and_put(cmd):
            now = time.time()
            if now - last_press_time[0] > press_cooldown:
                last_press_time[0] = now
                command_queue.put(cmd)

        # --- Key bindings ---
        def next_video(event=None):      debounce_and_put("next")
        def previous_video(event=None):  debounce_and_put("prev")
        def next_playlist(event=None):   debounce_and_put("plist_next")
        def prev_playlist(event=None):   debounce_and_put("plist_prev")
        def toggle_shuffle(event=None):  debounce_and_put("shuffle_toggle")  # S key
        def reshuffle(event=None):       debounce_and_put("reshuffle")        # R key

        def exit_app(event=None):
            print("Exiting...")
            command_queue.put("exit")

        root.bind("<Right>", next_video)
        root.bind("<Left>", previous_video)
        root.bind("<Up>", next_playlist)
        root.bind("<Down>", prev_playlist)
        root.bind("<s>", toggle_shuffle)     # toggle shuffle
        root.bind("<S>", toggle_shuffle)
        root.bind("<r>", reshuffle)          # reshuffle order
        root.bind("<R>", reshuffle)
        root.bind("<Escape>", exit_app)
        root.bind("<FocusIn>", lambda e: root.focus_force())

        threading.Thread(target=video_loop, daemon=True).start()
        root.mainloop()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    playlist_name = get_active_playlist_name()
    play_videos_with_black_background(video_folder, playlist_name)


