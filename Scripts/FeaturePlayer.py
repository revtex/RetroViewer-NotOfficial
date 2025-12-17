import vlc  # type: ignore
import time
import os
import tkinter as tk
import threading
import sys
import queue
import random  # shuffle
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

# Video file directories (actual video files on disk)
video_folder = os.path.join(base_dir, "Data", "VideoFiles")  # Commercial videos
media_folder = os.path.join(base_dir, "Data", "MediaFiles")   # Feature movies

# All settings, playlists, timestamps, and queue managed via database (db_helper)

# ---------- Config ----------
DEFAULT_COMMERCIALS_PER_BREAK = 3   # fallback if not in database settings
CHECK_INTERVAL = 0.2                # seconds; how often we check movie time
START_RETRY_MS = 2000               # wait up to this long for VLC to report Playing
ASPECT = "16:9"                     # force aspect ratio for both movie and ads

# ---------- Database Helpers ----------
def list_playlists():
    playlists = db_helper.get_all_playlists()
    return [p['name'] for p in playlists]

def read_playlist(playlist_name):
    """Get list of video filenames from a playlist in the database."""
    videos = db_helper.get_playlist_videos(playlist_name)
    # Extract just the filenames from the video records
    return [v['filename'] for v in videos] if videos else []

# ---------- Feature Player Settings ----------
def load_feature_settings():
    """
    Loads settings from database for:
      - ads_per_break
      - feature_playlist
      - shuffle

    Returns: (ads_per_break:int, playlist_name:str, shuffle_on:bool)
    """
    # Get settings from database
    ads_per_break_str = db_helper.get_setting("ads_per_break", str(DEFAULT_COMMERCIALS_PER_BREAK)) or str(DEFAULT_COMMERCIALS_PER_BREAK)
    ads_per_break = int(ads_per_break_str)
    playlist_name = db_helper.get_setting("feature_playlist", "All Videos")
    shuffle_setting = (db_helper.get_setting("feature_player_shuffle", "OFF") or "OFF").upper()
    shuffle_on = shuffle_setting in ("ON", "YES")
    
    # Validate playlist exists
    all_playlists = list_playlists()
    if playlist_name not in all_playlists:
        print(f"Playlist '{playlist_name}' not found in database. Falling back to 'All Videos'.")
        playlist_name = "All Videos"
    
    print(f"Feature settings: ads_per_break={ads_per_break}, playlist={playlist_name}, shuffle={shuffle_on}")
    return ads_per_break, playlist_name, shuffle_on

# ---------- Now Playing Queue from Database ----------
def load_now_playing_list():
    """
    Loads the Now Playing queue from database.
    Returns: list of absolute paths to video files on disk.
    """
    movies = []
    queue = db_helper.get_now_playing_queue()
    
    if not queue:
        print("Now Playing queue is empty. Please add movies in Manager.py.")
        return movies
    
    for item in queue:
        filename = item['filename']
        # Build absolute path
        path = os.path.join(media_folder, filename)
        if os.path.exists(path):
            movies.append(path)
        else:
            print(f"Now Playing movie not found on disk: {filename}")
    
    return movies

# ---------- Timestamp parsing helpers ----------
def _parse_time_token(tok):
    """Return milliseconds for a token 'HH:MM:SS', 'MM:SS', 'M:SS.xx', or 'SS'."""
    tok = tok.strip()
    if not tok:
        return None

    # Handle optional fractional seconds like 03:18.14 or 18.14
    if ":" in tok:
        parts = [p.strip() for p in tok.split(":")]
        try:
            if len(parts) == 3:
                h, m, s = parts
                seconds = float(s)
                return int((int(h) * 3600 + int(m) * 60 + seconds) * 1000)
            elif len(parts) == 2:
                m, s = parts
                seconds = float(s)
                return int((int(m) * 60 + seconds) * 1000)
            else:
                return None
        except ValueError:
            return None
    else:
        # plain seconds (can be float)
        try:
            return int(float(tok) * 1000)
        except ValueError:
            return None

def load_timestamps_for(movie_path):
    """
    Loads timestamps from database.

    Returns a dict:
        {
            "start_ms": <int or 0>,
            "end_ms": <int or None>,
            "breaks": [list of ms break points]
        }
    If movie not found in database, returns defaults with no breaks.
    """
    filename = os.path.basename(movie_path)
    
    result = {
        "start_ms": 0,
        "end_ms": None,
        "breaks": []
    }

    # Load from database
    movie = db_helper.get_feature_movie_by_filename(filename)
    if not movie:
        print(f"⚠️  Movie '{filename}' not found in database. Use Manager.py to add timestamps.")
        return result
    
    # Get timestamps (start/end)
    timestamps = db_helper.get_movie_timestamps(movie['id'])
    if timestamps:
        if timestamps['start_time']:
            ms = _parse_time_token(timestamps['start_time'])
            if ms is not None:
                result["start_ms"] = int(ms)
        
        if timestamps['end_time']:
            ms = _parse_time_token(timestamps['end_time'])
            if ms is not None:
                result["end_ms"] = int(ms)
    
    # Get commercial breaks
    break_times = db_helper.get_commercial_breaks(movie['id'])
    for break_data in break_times:
        ms = _parse_time_token(break_data['break_time'])
        if ms is not None:
            result["breaks"].append(int(ms))
    
    result["breaks"] = sorted(set(result["breaks"]))
    print(f"Loaded timestamps from database for {filename}: Start={result['start_ms']} ms, End={result['end_ms']} ms, Breaks={len(result['breaks'])}")
    
    return result

# ---------- App ----------
def play_movie_with_commercial_breaks(ad_playlist_name, movie_paths, ads_per_break, shuffle_default=False):
    try:
        if not movie_paths:
            print("Now Playing queue is empty or no valid movie files found.")
            return

        # --- Main Window / Canvas ---
        root = tk.Tk()
        root.configure(bg="black")
        root.attributes("-fullscreen", True)
        root.config(cursor="none")
        root.focus_force()

        video_canvas = tk.Canvas(root, bg="black", highlightthickness=0)
        video_canvas.pack(expand=True, fill="both")

        # ----- Toast overlay (top-right) -----
        toast_ids: dict[str, int | None] = {"text": None, "shadow": None, "bg": None}

        def show_toast(message, duration_ms=2000, pad=18):
            # clear any existing toast
            for k in ("bg", "shadow", "text"):
                if toast_ids[k] is not None:
                    try:
                        canvas_id = toast_ids[k]
                        if canvas_id is not None:  # Type narrowing
                            video_canvas.delete(canvas_id)
                    except Exception:
                        pass
                    toast_ids[k] = None

            video_canvas.update_idletasks()
            x = video_canvas.winfo_width() - pad
            y = pad

            toast_ids["shadow"] = video_canvas.create_text(
                x + 1, y + 1, text=message, fill="#000000",
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
                        except Exception:
                            pass
                        toast_ids[k] = None

            root.after(duration_ms, remove_toast)

        def on_resize(_event=None):
            if toast_ids["text"] is not None:
                msg = video_canvas.itemcget(toast_ids["text"], "text")
                show_toast(msg)
        root.bind("<Configure>", on_resize)

        # ----- Use only the playlist from settings -----
        # Playlist already validated in load_feature_settings()
        playlists = [ad_playlist_name]  # Single playlist from settings
        playlist_index = [0]  # Always use index 0 since we only have one playlist

        video_files = [[]]   # ad filenames for current playlist
        order = [[]]         # playback order (indices into video_files[0])
        video_pos = [0]      # position within 'order'
        shuffle_mode = [shuffle_default]  # start from FeaturePlayer setting

        def build_order():
            n = len(video_files[0])
            if n == 0:
                order[0] = []
                video_pos[0] = 0
                return
            order[0] = list(range(n))
            if shuffle_mode[0]:
                random.shuffle(order[0])
            video_pos[0] %= max(1, len(order[0]))

        def current_video_name():
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
            video_pos[0] = 0
            build_order()
            print(f"\n=== Now using ad playlist: {playlist_name} ({len(files)} items) ===")
            # No on-screen ad playlist display to keep TV illusion
            return True

        if not load_current_playlist():
            tried = 1
            while tried < len(playlists) and not video_files[0]:
                playlist_index[0] = (playlist_index[0] + 1) % len(playlists)
                if load_current_playlist():
                    break
                tried += 1
            if not video_files[0]:
                print("All ad playlists are empty or invalid.")
                return

        # ----- VLC setup: SINGLE player shared by movies + ads -----
        # Suppress VLC error messages and warnings
        instance = vlc.Instance('--quiet', '--no-video-title-show')
        player = instance.media_player_new()  # type: ignore

        root.update_idletasks()
        hwnd = video_canvas.winfo_id()
        player.set_hwnd(hwnd)  # Attach once like the original commercials-only script

        # Movie state
        movie_index = [0]           # index in movie_paths
        movie_media = [None]        # current movie's media
        breaks_ms = []              # breakpoints for current movie
        next_break_index = [0]      # index into breaks_ms

        movie_state = {
            "start_ms": 0,
            "end_ms": None
        }

        # Control queues / state
        command_queue = queue.Queue()
        last_press_time: list[float] = [0.0]
        press_cooldown = 0.4        # seconds
        state = {"mode": "MOVIE"}   # or "ADS"
        saved_pos_ms = [0]          # where to resume movie after ads
        ads_remaining = [0]

        # --- Helpers for VLC start/wait ---
        def _start_and_wait(player_obj, label=""):
            player_obj.play()
            waited = 0
            step = 0.1
            while waited < START_RETRY_MS / 1000.0:
                st = player_obj.get_state()
                if st == vlc.State.Playing:  # type: ignore
                    return True
                time.sleep(step)
                waited += step
            print(f"{label} failed to start (state={player_obj.get_state()}).")
            return False

        def load_movie(idx):
            """Load movie at movie_paths[idx] and its timestamps (start/end/breaks)."""
            path = movie_paths[idx]
            if not os.path.exists(path):
                print(f"Movie file not found: {path}")
                return False

            mm = instance.media_new(path)  # type: ignore
            movie_media[0] = mm
            player.stop()
            player.set_media(mm)
            player.video_set_aspect_ratio(ASPECT)
            player.video_set_scale(0)

            # Load timestamps for this movie
            ts = load_timestamps_for(path)
            start_ms = ts["start_ms"]
            end_ms = ts["end_ms"]
            all_breaks = ts["breaks"]

            # Filter breaks to be within [start_ms, end_ms] if end_ms is set
            filtered_breaks = []
            for b in all_breaks:
                if b < start_ms:
                    continue
                if end_ms is not None and b >= end_ms:
                    continue
                filtered_breaks.append(b)

            breaks_ms.clear()
            breaks_ms.extend(sorted(filtered_breaks))
            next_break_index[0] = 0

            movie_state["start_ms"] = start_ms
            movie_state["end_ms"] = end_ms

            print(f"\n=== Now playing feature: {os.path.basename(path)} ===")
            if start_ms > 0:
                print(f"  -> Will start at {start_ms} ms")
            if end_ms is not None:
                print(f"  -> Will end at {end_ms} ms")
            print(f"  -> {len(breaks_ms)} scheduled breaks in this range")

            return True

        def advance_to_next_movie():
            """Advance movie_index, loop through list, trying to find a playable movie."""
            if not movie_paths:
                return False

            tries = 0
            while tries < len(movie_paths):
                movie_index[0] = (movie_index[0] + 1) % len(movie_paths)
                if load_movie(movie_index[0]):
                    return True
                tries += 1
            return False

        def advance_to_prev_movie():
            """Go back to previous movie in the queue."""
            if not movie_paths:
                return False

            tries = 0
            while tries < len(movie_paths):
                movie_index[0] = (movie_index[0] - 1) % len(movie_paths)
                if load_movie(movie_index[0]):
                    return True
                tries += 1
            return False

        def _play_single_ad_by_name(name):
            """
            Play a single ad (blocking) using the same player.
            """
            if not name:
                return
            path = os.path.join(video_folder, name)
            if not os.path.exists(path):
                print(f"Ad file missing: {name} — skipping.")
                return

            # Swap the VLC media to this ad
            ad_media = instance.media_new(path)  # type: ignore
            player.stop()
            player.set_media(ad_media)
            player.video_set_aspect_ratio(ASPECT)
            player.video_set_scale(0)

            print(f"Playing Ad: {name}")
            if not _start_and_wait(player, "Ad"):
                return

            # Wait until ad finishes or we are told to skip
            while True:
                try:
                    cmd = command_queue.get(timeout=0.1)
                    if cmd == "next":  # skip ad
                        player.stop()
                        return
                    elif cmd == "exit":
                        player.stop()
                        root.destroy()
                        sys.exit(0)
                    elif cmd == "shuffle_toggle":
                        shuffle_mode[0] = not shuffle_mode[0]
                        mode = "ON" if shuffle_mode[0] else "OFF"
                        print(f"Shuffle: {mode}")
                        root.after(0, lambda: show_toast(f"Shuffle: {mode}"))
                        reshuffle_current()
                    elif cmd == "reshuffle":
                        reshuffle_current()
                        root.after(0, lambda: show_toast("Shuffle: Reshuffled"))
                    else:
                        # ignore other commands during ad
                        pass
                except queue.Empty:
                    if player.get_state() in [vlc.State.Ended, vlc.State.Stopped, vlc.State.Error]:  # type: ignore
                        return

        def step_next_ad():
            if not order[0]:
                return
            video_pos[0] = (video_pos[0] + 1) % len(order[0])

        def step_prev_ad():
            if not order[0]:
                return
            video_pos[0] = (video_pos[0] - 1) % len(order[0])

        def reshuffle_current():
            if not video_files[0]:
                return
            cur_name = current_video_name()
            build_order()
            if cur_name in video_files[0]:
                idx = video_files[0].index(cur_name)
                try:
                    video_pos[0] = order[0].index(idx)
                except ValueError:
                    video_pos[0] = 0

        # --- Main Controller Thread ---
        def controller():
            # Ensure we have at least one valid movie loaded
            tries = 0
            while tries < len(movie_paths):
                if load_movie(movie_index[0]):
                    break
                movie_index[0] = (movie_index[0] + 1) % len(movie_paths)
                tries += 1

            if movie_media[0] is None:
                print("No valid movie files found in Now Playing queue.")
                root.after(0, root.destroy)
                return

            # Start movie and seek to its configured start time
            if _start_and_wait(player, "Movie"):
                if movie_state["start_ms"] > 0:
                    player.set_time(movie_state["start_ms"])
                    player.set_pause(0)

            while True:
                # handle global commands that apply anytime
                try:
                    cmd = command_queue.get(timeout=CHECK_INTERVAL)
                    if cmd == "exit":
                        player.stop()
                        root.destroy()
                        sys.exit(0)
                    elif cmd == "shuffle_toggle":
                        shuffle_mode[0] = not shuffle_mode[0]
                        mode = "ON" if shuffle_mode[0] else "OFF"
                        print(f"Shuffle: {mode}")
                        root.after(0, lambda: show_toast(f"Shuffle: {mode}"))
                        reshuffle_current()
                    elif cmd == "reshuffle":
                        reshuffle_current()
                        root.after(0, lambda: show_toast("Shuffle: Reshuffled"))
                    elif cmd == "next":
                        # Skip to next ad during commercials
                        if state["mode"] == "ADS":
                            # Stop current ad and advance
                            player.stop()
                            step_next_ad()
                            print(f"Skipped to next ad ({video_pos[0] + 1}/{len(order[0])})")
                    elif cmd == "prev":
                        # Go back to previous ad during commercials
                        if state["mode"] == "ADS":
                            # Stop current ad and go back
                            player.stop()
                            step_prev_ad()
                            print(f"Back to previous ad ({video_pos[0] + 1}/{len(order[0])})")
                    elif cmd == "movie_next":
                        # Skip to next movie in queue
                        player.stop()
                        if advance_to_next_movie():
                            print(f"Skipping to next movie: {os.path.basename(movie_paths[movie_index[0]])}")
                            state["mode"] = "MOVIE"
                            if _start_and_wait(player, "Movie"):
                                if movie_state["start_ms"] > 0:
                                    player.set_time(movie_state["start_ms"])
                                    player.set_pause(0)
                        else:
                            print("No more playable movies in queue.")
                            player.stop()
                            root.after(0, root.destroy)
                    elif cmd == "movie_prev":
                        # Go back to previous movie in queue
                        player.stop()
                        if advance_to_prev_movie():
                            print(f"Going back to previous movie: {os.path.basename(movie_paths[movie_index[0]])}")
                            state["mode"] = "MOVIE"
                            if _start_and_wait(player, "Movie"):
                                if movie_state["start_ms"] > 0:
                                    player.set_time(movie_state["start_ms"])
                                    player.set_pause(0)
                        else:
                            print("No more playable movies in queue.")
                            player.stop()
                            root.after(0, root.destroy)
                except queue.Empty:
                    pass

                if state["mode"] == "MOVIE":
                    cur_ms = player.get_time()
                    end_ms = movie_state["end_ms"]

                    # Check for forced end time
                    if end_ms is not None and cur_ms >= end_ms:
                        print("Reached configured end-of-feature time. Advancing to next.")
                        if not advance_to_next_movie():
                            print("No playable movies remain. Stopping.")
                            player.stop()
                            root.after(0, root.destroy)
                            return
                        # Start new movie
                        if _start_and_wait(player, "Movie"):
                            if movie_state["start_ms"] > 0:
                                player.set_time(movie_state["start_ms"])
                                player.set_pause(0)
                        continue

                    # Check for next break
                    if next_break_index[0] < len(breaks_ms):
                        if cur_ms >= breaks_ms[next_break_index[0]]:
                            # Start ad break
                            saved_pos_ms[0] = cur_ms
                            next_break_index[0] += 1
                            state["mode"] = "ADS"
                            ads_remaining[0] = ads_per_break

                            player.pause()
                            # Optional on-screen text:
                            # root.after(0, lambda: show_toast("Commercial Break", 1800))
                            time.sleep(0.25)

                    # Detect natural end-of-file if no End: is set
                    st = player.get_state()
                    if end_ms is None and st in (vlc.State.Ended, vlc.State.Stopped, vlc.State.Error):  # type: ignore
                        print("Feature ended (natural). Advancing to next.")
                        if not advance_to_next_movie():
                            print("No playable movies remain. Stopping.")
                            player.stop()
                            root.after(0, root.destroy)
                            return
                        if _start_and_wait(player, "Movie"):
                            if movie_state["start_ms"] > 0:
                                player.set_time(movie_state["start_ms"])
                                player.set_pause(0)
                        continue

                if state["mode"] == "ADS":
                    # Play N ads in this break
                    while ads_remaining[0] > 0:
                        if not order[0] or not video_files[0]:
                            print("No ads available in current playlist; skipping break.")
                            break
                        name = current_video_name()
                        _play_single_ad_by_name(name)
                        step_next_ad()
                        ads_remaining[0] -= 1

                    # Finished ads (or none available) -> resume movie
                    state["mode"] = "MOVIE"

                    # Swap back to the current movie media
                    player.stop()
                    if movie_media[0] is not None:
                        player.set_media(movie_media[0])
                        player.video_set_aspect_ratio(ASPECT)
                        player.video_set_scale(0)

                        # Determine resume time; if it would be beyond End, just treat as ended
                        resume_ms = max(movie_state["start_ms"], saved_pos_ms[0] + 50)
                        end_ms = movie_state["end_ms"]
                        if end_ms is not None and resume_ms >= end_ms:
                            # Just advance to next feature instead of resuming
                            print("Ad break ended but we've passed feature's End time; advancing to next feature.")
                            if not advance_to_next_movie():
                                print("No playable movies remain. Stopping.")
                                player.stop()
                                root.after(0, root.destroy)
                                return
                            if _start_and_wait(player, "Movie"):
                                if movie_state["start_ms"] > 0:
                                    player.set_time(movie_state["start_ms"])
                                    player.set_pause(0)
                        else:
                            if _start_and_wait(player, "MovieResume"):
                                player.set_time(resume_ms)
                                player.set_pause(0)

        # --- Debounced command posting ---
        def debounce_and_put(cmd):
            now = time.time()
            if now - last_press_time[0] > press_cooldown:
                last_press_time[0] = now
                command_queue.put(cmd)

        # --- Key bindings ---
        def next_ad(event=None):         debounce_and_put("next")          # skip to next ad (during commercials)
        def previous_ad(event=None):     debounce_and_put("prev")          # go back to previous ad (during commercials)
        def next_movie(event=None):      debounce_and_put("movie_next")    # skip to next movie
        def previous_movie(event=None):  debounce_and_put("movie_prev")    # go back to previous movie
        def toggle_shuffle(event=None):  debounce_and_put("shuffle_toggle")
        def reshuffle(event=None):       debounce_and_put("reshuffle")

        def exit_app(event=None):
            print("Exiting...")
            debounce_and_put("exit")

        root.bind("<Right>", next_ad)        # skip to next commercial
        root.bind("<Left>", previous_ad)     # go back to previous commercial
        root.bind("<Up>", next_movie)        # skip to next movie
        root.bind("<Down>", previous_movie)  # go back to previous movie
        root.bind("<s>", toggle_shuffle)
        root.bind("<S>", toggle_shuffle)
        root.bind("<r>", reshuffle)
        root.bind("<R>", reshuffle)
        root.bind("<Escape>", exit_app)
        root.bind("<FocusIn>", lambda e: root.focus_force())

        # --- Start controller thread and Tk mainloop ---
        threading.Thread(target=controller, daemon=True).start()
        root.mainloop()

    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    ads_per_break, ad_playlist_name, shuffle_default = load_feature_settings()
    movie_paths = load_now_playing_list()
    if not movie_paths:
        print("No movies in Now Playing queue or files missing. Exiting.")
    else:
        play_movie_with_commercial_breaks(ad_playlist_name, movie_paths, ads_per_break, shuffle_default)
