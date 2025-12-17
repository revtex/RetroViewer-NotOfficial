import os
import re
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import tkinter.font as tkfont
from typing import Optional
from mutagen.mp4 import MP4
import db_helper

# ----------------------------
# Metadata helpers
# ----------------------------
def _coerce_first(value, fallback="Unknown"):
    """Mutagen atoms return lists; coerce to clean string for display."""
    try:
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, bytes):
            value = value.decode(errors="replace")
        value = str(value).strip()
        return value if value else fallback
    except Exception:
        return fallback

def _year_display(s):
    """Normalize date-like strings to a displayable year."""
    s = str(s).strip()
    m = re.match(r"^(\d{4})", s)
    return m.group(1) if m else (s if s else "Unknown")

def get_metadata(file_path):
    try:
        mp4_file = MP4(file_path)
        title = _coerce_first(mp4_file.get("\xa9nam", ["Unknown"]))
        genre = _coerce_first(mp4_file.get("\xa9gen", ["Unknown"]))
        year_raw = _coerce_first(mp4_file.get("\xa9day", ["Unknown"]))
        year  = _year_display(year_raw)
        tags  = _coerce_first(mp4_file.get("\xa9too", ["Unknown"]))
        return title, tags, year, genre
    except Exception:
        return "Error", "Error", "Error", "Error"

def update_metadata(file_path, title=None, tags=None, year=None, genre=None):
    mp4_file = MP4(file_path)
    if title is not None:
        mp4_file["\xa9nam"] = title
    if tags is not None:
        mp4_file["\xa9too"] = tags
    if year is not None:
        mp4_file["\xa9day"] = year
    if genre is not None:
        mp4_file["\xa9gen"] = genre
    mp4_file.save()

# ----------------------------
# GUI + filtering
# ----------------------------
class MetadataApp:
    COLUMNS = ("File Name", "Title", "Tags", "Year", "Genre")
    FILTERABLE = {"Tags", "Year", "Genre"}

    def __init__(self, directory):
        self.directory = directory
        self.base_dir  = os.path.dirname(self.directory)  # for default save location
        self.root = tk.Tk()
        self.root.title("MP4 Metadata Editor")
        self.root.geometry("1100x820")

        # Data store
        self.all_rows = self.scan_files(self.directory)
        self.active_filters: dict[str, set[str] | None] = {col: None for col in self.FILTERABLE}
        self.active_filters_norm: dict[str, set[str] | None] = {col: None for col in self.FILTERABLE}
        self.sort_state = {col: False for col in self.COLUMNS}
        self._last_filtered_rows = []  # updated every refresh

        # For distinguishing single vs double clicks
        self._single_click_job = None

        # Treeview
        self.tree = ttk.Treeview(self.root, columns=self.COLUMNS, show="headings")
        for col in self.COLUMNS:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=150, stretch=True)
        self.tree.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.root.grid_rowconfigure(0, weight=1)
        self.root.grid_columnconfigure(0, weight=1)

        # Scrollbars
        yscroll = ttk.Scrollbar(self.root, orient="vertical", command=self.tree.yview)
        yscroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=yscroll.set)
        xscroll = ttk.Scrollbar(self.root, orient="horizontal", command=self.tree.xview)
        xscroll.grid(row=1, column=0, sticky="ew")
        self.tree.configure(xscrollcommand=xscroll.set)

        # Status + buttons
        status_frame = ttk.Frame(self.root)
        status_frame.grid(row=2, column=0, sticky="we", padx=10, pady=(0, 10))
        self.status_var = tk.StringVar(value="No filters")
        ttk.Label(status_frame, textvariable=self.status_var).pack(side="left")

        btns_right = ttk.Frame(status_frame)
        btns_right.pack(side="right")
        ttk.Button(btns_right, text="Open Manager", command=self.open_manager).pack(side="right", padx=(6,0))
        ttk.Button(btns_right, text="Export Filtered List", command=self.export_filtered_list).pack(side="right", padx=(6,0))
        ttk.Button(btns_right, text="Reset Filters", command=self.reset_filters).pack(side="right", padx=(0,6))

        # Bindings
        self.tree.bind("<Button-1>", self.on_header_or_cell_click, add="+")  # header sorting/filter
        self.tree.bind("<ButtonRelease-1>", self.on_tree_button_release)     # single click (delayed)
        self.tree.bind("<Double-1>", self.on_tree_double_click)              # double click edit

        # Fill table
        self.refresh_tree()

    # ---------- Utilities ----------
    @staticmethod
    def _norm(v):
        return str(v).strip().lower()

    # ---------- Data ----------
    def scan_files(self, directory):
        """Load video metadata from database (with fallback to scanning MP4 files)."""
        rows = []
        
        # Try loading from database first
        all_videos = db_helper.get_all_videos()
        if all_videos:
            for video in all_videos:
                rows.append({
                    "File Name": video['filename'],
                    "Title": video['title'],
                    "Tags": video['tags'],
                    "Year": video['year'],
                    "Genre": video['genre']
                })
            return rows
        
        # Fallback to scanning MP4 files directly (backward compatibility)
        print("\n⚠️  WARNING: No videos in database, scanning MP4 files directly.")
        print("    Recommendation: Run 'python3 Utilities/setup_database.py' to set up database.")
        print("    This will improve performance and enable playlist management.\n")
        
        if not os.path.isdir(directory):
            return rows
        
        for filename in sorted(os.listdir(directory)):
            if filename.lower().endswith(".mp4"):
                file_path = os.path.join(directory, filename)
                title, tags, year, genre = get_metadata(file_path)
                rows.append({
                    "File Name": filename,
                    "Title": title,
                    "Tags": tags,
                    "Year": year,
                    "Genre": genre
                })
        
        return rows

    # ---------- Display ----------
    def refresh_tree(self):
        for item in self.tree.get_children(""):
            self.tree.delete(item)

        def passes_filters(row):
            for col, allowed_norm in self.active_filters_norm.items():
                if allowed_norm is None:
                    continue
                value = row.get(col, "")
                if col == "Year":
                    value = _year_display(value)
                if self._norm(value) not in allowed_norm:
                    return False
            return True

        filtered = [r for r in self.all_rows if passes_filters(r)]
        self._last_filtered_rows = filtered  # store for export

        for r in filtered:
            self.tree.insert("", "end", values=tuple(r[c] for c in self.COLUMNS))

        active_bits = []
        for col in self.FILTERABLE:
            sel = self.active_filters.get(col)
            if sel is not None:
                active_bits.append(f"{col}: {len(sel)}")
        summary = "No filters" if not active_bits else "Filters → " + " | ".join(active_bits)
        self.status_var.set(f"{summary}    •   Showing {len(filtered)} of {len(self.all_rows)}")

        self._autosize_columns()

    def _autosize_columns(self):
        font = tkfont.Font()
        for col in self.COLUMNS:
            header_w = font.measure(col) + 30
            max_w = header_w
            for item in self.tree.get_children("")[:200]:
                text = str(self.tree.set(item, col))
                w = font.measure(text) + 30
                if w > max_w:
                    max_w = w
            self.tree.column(col, width=max_w, stretch=True)

    def reset_filters(self):
        self.active_filters = {col: None for col in self.FILTERABLE}
        self.active_filters_norm = {col: None for col in self.FILTERABLE}
        self.refresh_tree()

    # ---------- Export ----------
    def export_filtered_list(self):
        """Prompt for a filename and export current filtered File Names to a .txt."""
        if not self._last_filtered_rows:
            messagebox.showinfo("Export Filtered List", "There are no visible rows to export.")
            return

        # Ask for a simple name, then save into 'Playlist' beside VideoFiles by default
        default_name = "file_list.txt"
        name = simpledialog.askstring("Export Filtered List",
                                      "Enter a name for the text file (e.g., file_list):",
                                      parent=self.root,
                                      initialvalue=os.path.splitext(default_name)[0])
        if not name:
            return

        # Ensure .txt extension
        filename = f"{name}.txt" if not name.lower().endswith(".txt") else name

        # Save as playlist in database
        try:
            # Get or create playlist
            playlist = db_helper.get_playlist_by_name(name)
            if not playlist:
                db_helper.create_playlist(name, f"Filtered playlist with {len(self._last_filtered_rows)} videos")
            
            # Clear and rebuild
            db_helper.clear_playlist(name)
            for position, row in enumerate(self._last_filtered_rows, 1):
                db_helper.add_video_to_playlist(name, row['File Name'], position)
            
            # Also export to text file for backward compatibility
            playlist_dir = os.path.join(self.base_dir, "Playlist")
            os.makedirs(playlist_dir, exist_ok=True)
            save_path = os.path.join(playlist_dir, filename)
            db_helper.export_playlist_to_file(name, save_path)
            
            messagebox.showinfo("Export Complete", 
                f"Saved {len(self._last_filtered_rows)} entries to:\n" +
                f"Database playlist: {name}\n" +
                f"Text file: {save_path}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not save playlist:\n{e}")
            return

    # ---------- Single vs Double click wiring ----------
    def on_tree_button_release(self, event):
        """Handle (potential) single-click: schedule it slightly later so a double-click can cancel it."""
        if self.tree.identify_region(event.x, event.y) != "cell":
            return

        # cancel pending single-click if any
        if self._single_click_job is not None:
            self.root.after_cancel(self._single_click_job)
            self._single_click_job = None

        x, y = event.x, event.y
        # run after small delay so double-click has chance to cancel
        self._single_click_job = self.root.after(
            200, lambda: self.handle_single_click(x, y)
        )

    def on_tree_double_click(self, event):
        """Double-click: cancel single-click job and open editor dialog."""
        if self._single_click_job is not None:
            self.root.after_cancel(self._single_click_job)
            self._single_click_job = None

        if self.tree.identify_region(event.x, event.y) != "cell":
            return

        self.handle_double_click(event.x, event.y)

    # ---------- Single-click behavior ----------
    def handle_single_click(self, x, y):
        self._single_click_job = None  # this job is running now

        item_id = self.tree.identify_row(y)
        col_id  = self.tree.identify_column(x)
        if not item_id or not col_id:
            return

        col_index = int(col_id[1:]) - 1
        if col_index < 0 or col_index >= len(self.COLUMNS):
            return

        region = self.tree.identify_region(x, y)
        if region != "cell":
            return

        self.tree.selection_set(item_id)
        values = self.tree.item(item_id, "values")
        if not values:
            return

        column_name = self.COLUMNS[col_index]
        file_name   = values[0]

        # Single-click on File Name: copy base name to clipboard
        if column_name == "File Name":
            base_name, _ = os.path.splitext(file_name)
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(base_name)
                self.status_var.set(f"Copied file name to clipboard: {base_name}")
            except Exception as e:
                print(f"Failed to copy to clipboard: {e}")
            return

        # Single-click on Title: auto-paste clipboard as new title
        if column_name == "Title":
            try:
                new_value = self.root.clipboard_get().strip()
            except Exception:
                new_value = ""

            if not new_value:
                return  # nothing useful on clipboard

            file_path = os.path.join(self.directory, file_name)

            try:
                # Update MP4 file
                update_metadata(file_path, title=new_value)
                # Update database
                db_helper.update_video_metadata(file_name, title=new_value)
            except Exception as e:
                print(f"Failed to update Title for {file_name}: {e}")
                return

            # Update in-memory row
            for r in self.all_rows:
                if r["File Name"] == file_name:
                    r["Title"] = new_value
                    break

            self.status_var.set(f"Set Title from clipboard for: {file_name}")
            self.refresh_tree()
            return

        # Single-click on other columns: no special behavior

    # ---------- Double-click behavior (open editor) ----------
    def handle_double_click(self, x, y):
        item_id = self.tree.identify_row(y)
        col_id  = self.tree.identify_column(x)
        if not item_id or not col_id:
            return

        col_index = int(col_id[1:]) - 1
        if col_index < 0 or col_index >= len(self.COLUMNS):
            return

        region = self.tree.identify_region(x, y)
        if region != "cell":
            return

        values = self.tree.item(item_id, "values")
        if not values:
            return

        column_name = self.COLUMNS[col_index]
        file_name   = values[0]

        # Do NOT edit File Name column
        if column_name == "File Name":
            return

        old_value = values[col_index]
        file_path = os.path.join(self.directory, file_name)

        # Use selection dialogs for Tags and Genre
        if column_name == "Tags":
            new_value = self.show_tags_selection_dialog(old_value)
        elif column_name == "Genre":
            new_value = self.show_genre_selection_dialog(old_value)
        else:
            new_value = simpledialog.askstring(
                "Edit Metadata",
                f"Edit {column_name}:",
                initialvalue=old_value,
                parent=self.root
            )
        
        if new_value is None:
            return

        try:
            # Update MP4 file metadata
            if column_name == "Title":
                update_metadata(file_path, title=new_value)
            elif column_name == "Tags":
                update_metadata(file_path, tags=new_value)
            elif column_name == "Year":
                update_metadata(file_path, year=new_value)
            elif column_name == "Genre":
                update_metadata(file_path, genre=new_value)
            
            # Update database
            if column_name == "Title":
                db_helper.update_video_metadata(file_name, title=new_value)
            elif column_name == "Tags":
                db_helper.update_video_metadata(file_name, tags=new_value)
            elif column_name == "Year":
                db_helper.update_video_metadata(file_name, year=new_value)
            elif column_name == "Genre":
                db_helper.update_video_metadata(file_name, genre=new_value)
        except Exception as e:
            print(f"Failed to update {column_name} for {file_name}: {e}")

        for r in self.all_rows:
            if r["File Name"] == file_name:
                r[column_name] = _year_display(new_value) if column_name == "Year" else new_value
                break

        self.refresh_tree()

    # ---------- Sorting / Header clicks ----------
    def on_header_or_cell_click(self, event):
        if self.tree.identify_region(event.x, event.y) != "heading":
            return
        col_id = self.tree.identify_column(event.x)
        col_index = int(col_id[1:]) - 1
        if col_index < 0 or col_index >= len(self.COLUMNS):
            return
        column_name = self.COLUMNS[col_index]
        if column_name in self.FILTERABLE:
            self.show_checkbox_filter_popup(column_name, event)
        else:
            self.toggle_sort(column_name)

    def toggle_sort(self, column_name):
        reverse = self.sort_state[column_name]

        def try_int(val):
            try:
                return int(str(val).strip())
            except Exception:
                s = "" if val is None else str(val).lower()
                return s

        # Choose key function explicitly (no lambda-in-lambda bug)
        if column_name == "Year":
            key_fn = lambda r: try_int(_year_display(r.get(column_name, "")))
        else:
            key_fn = lambda r: try_int(r.get(column_name, ""))

        self.all_rows.sort(key=key_fn, reverse=reverse)
        self.sort_state[column_name] = not reverse
        self.refresh_tree()

    # ---------- Checkbox Filter UI ----------
    def show_checkbox_filter_popup(self, column_name, event):
        def display_value_for_col(v):
            return _year_display(v) if column_name == "Year" else str(v)

        all_vals = [display_value_for_col(r.get(column_name, "")) for r in self.all_rows]
        unique_vals = sorted({v for v in all_vals}, key=lambda s: s.lower())

        popup = tk.Toplevel(self.root)
        popup.transient(self.root)
        popup.title(f"Filter: {column_name}")
        popup.attributes("-topmost", True)
        
        # Center the popup on the parent window
        popup.update_idletasks()  # Ensure geometry is calculated
        popup_width = 300  # Default width for filter window
        popup_height = 400  # Default height for filter window
        
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        
        x = parent_x + (parent_width - popup_width) // 2
        y = parent_y + (parent_height - popup_height) // 2
        
        popup.geometry(f"{popup_width}x{popup_height}+{x}+{y}")

        ttk.Label(popup, text=f"Show {column_name} values:").pack(anchor="w", padx=10, pady=(10, 5))

        container = ttk.Frame(popup)
        container.pack(fill="both", expand=True, padx=10, pady=5)
        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")

        # Track if scrolling is needed
        scroll_bindings_active = [False]  # Use list to allow modification in nested function
        
        def _on_mousewheel(event):
            # Only scroll if content actually needs scrolling
            bbox = canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = canvas.winfo_height()
                if content_height > canvas_height:
                    # Windows and MacOS
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _on_mousewheel_linux(event):
            # Only scroll if content actually needs scrolling
            bbox = canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = canvas.winfo_height()
                if content_height > canvas_height:
                    # Linux uses Button-4 (scroll up) and Button-5 (scroll down)
                    if event.num == 4:
                        canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        canvas.yview_scroll(1, "units")
        
        def _on_configure(_=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(inner_id, width=canvas.winfo_width())
            
            # Check if content needs scrolling
            bbox = canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = canvas.winfo_height()
                needs_scroll = content_height > canvas_height
                
                # Show/hide scrollbar and enable/disable scroll bindings
                if needs_scroll:
                    if not scroll_bindings_active[0]:
                        # Bind to popup window instead of bind_all
                        popup.bind("<MouseWheel>", _on_mousewheel)
                        popup.bind("<Button-4>", _on_mousewheel_linux)
                        popup.bind("<Button-5>", _on_mousewheel_linux)
                        scroll_bindings_active[0] = True
                    vsb.pack(side="right", fill="y")
                else:
                    if scroll_bindings_active[0]:
                        # Unbind from popup
                        popup.unbind("<MouseWheel>")
                        popup.unbind("<Button-4>")
                        popup.unbind("<Button-5>")
                        scroll_bindings_active[0] = False
                    vsb.pack_forget()
        
        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_configure)
        
        # Cleanup bindings when popup closes
        def _on_destroy():
            if scroll_bindings_active[0]:
                popup.unbind("<MouseWheel>")
                popup.unbind("<Button-4>")
                popup.unbind("<Button-5>")
        
        popup.bind("<Destroy>", lambda e: _on_destroy() if e.widget == popup else None)

        active_display = self.active_filters.get(column_name)
        check_vars = {}
        for v in unique_vals:
            initial = True if active_display is None else (v in active_display)
            var = tk.BooleanVar(value=initial)
            cb = ttk.Checkbutton(inner, text=v, variable=var)
            cb.pack(anchor="w", pady=2)
            check_vars[v] = var

        btns = ttk.Frame(popup)
        btns.pack(fill="x", padx=10, pady=(5, 10))
        ttk.Button(btns, text="Select All", command=lambda: [var.set(True) for var in check_vars.values()]).pack(side="left")
        ttk.Button(btns, text="Clear All", command=lambda: [var.set(False) for var in check_vars.values()]).pack(side="left", padx=5)

        def apply_filter():
            chosen_display = [v for v, var in check_vars.items() if var.get()]
            if len(chosen_display) == 0 or len(chosen_display) == len(unique_vals):
                self.active_filters[column_name] = None
                self.active_filters_norm[column_name] = None
            else:
                self.active_filters[column_name] = set(chosen_display)
                self.active_filters_norm[column_name] = {self._norm(v) for v in chosen_display}
            popup.destroy()
            self.refresh_tree()

        ttk.Button(btns, text="Apply", command=apply_filter).pack(side="right")

    # ---------- Manager Launcher ----------
    def open_manager(self):
        """Launch the RetroViewer Manager for tags/genres/timestamps."""
        import subprocess
        import sys
        
        manager_script = os.path.join(self.base_dir, "Manager.py")
        if os.path.exists(manager_script):
            # Launch in separate process
            try:
                subprocess.Popen([sys.executable, manager_script])
                self.status_var.set("Launched RetroViewer Manager")
            except Exception as e:
                messagebox.showerror("Launch Failed", f"Could not launch Manager: {e}")
        else:
            messagebox.showerror("Manager Not Found", 
                f"Manager.py not found at:\n{manager_script}\n\n"
                "Please ensure Manager.py is in the same directory as Meta Editor.")

    # ---------- Tags Selection Dialog ----------
    def show_tags_selection_dialog(self, current_tags: str) -> Optional[str]:
        """Show multi-select dialog for tags."""
        available_tags = db_helper.get_all_tags()
        
        if not available_tags:
            messagebox.showinfo("No Tags", "No tags available. Please add tags in 'Manage Tags/Genres' first.")
            return None
        
        # Parse current tags
        current_tag_list = [t.strip() for t in current_tags.split(',')] if current_tags and current_tags != "Unknown" else []
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.title("Select Tags")
        dialog.attributes("-topmost", True)
        
        # Center the dialog
        dialog.update_idletasks()
        dialog_width = 400
        dialog_height = 500
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        ttk.Label(dialog, text="Select tags (multiple allowed):").pack(anchor="w", padx=10, pady=(10, 5))
        
        # Scrollable frame for checkboxes
        container = ttk.Frame(dialog)
        container.pack(fill="both", expand=True, padx=10, pady=5)
        canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
        vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas)
        inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        
        def _on_configure(_=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(inner_id, width=canvas.winfo_width())
        
        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_configure)
        
        # Create checkboxes
        check_vars = {}
        for tag in sorted(available_tags):
            var = tk.BooleanVar(value=(tag in current_tag_list))
            cb = ttk.Checkbutton(inner, text=tag, variable=var)
            cb.pack(anchor="w", pady=2)
            check_vars[tag] = var
        
        # Result storage
        result: list[Optional[str]] = [None]
        
        def on_apply():
            selected = [tag for tag, var in check_vars.items() if var.get()]
            result[0] = ", ".join(selected) if selected else "Unknown"
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Buttons
        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=10, pady=(5, 10))
        ttk.Button(btns, text="Select All", command=lambda: [var.set(True) for var in check_vars.values()]).pack(side="left")
        ttk.Button(btns, text="Clear All", command=lambda: [var.set(False) for var in check_vars.values()]).pack(side="left", padx=5)
        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(btns, text="Apply", command=on_apply).pack(side="right")
        
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result[0]

    # ---------- Genre Selection Dialog ----------
    def show_genre_selection_dialog(self, current_genre: str) -> Optional[str]:
        """Show single-select dialog for genre."""
        available_genres = db_helper.get_all_genres()
        
        if not available_genres:
            messagebox.showinfo("No Genres", "No genres available. Please add genres in 'Manage Tags/Genres' first.")
            return None
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.title("Select Genre")
        dialog.attributes("-topmost", True)
        
        # Center the dialog
        dialog.update_idletasks()
        dialog_width = 350
        dialog_height = 400
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        ttk.Label(dialog, text="Select genre:").pack(anchor="w", padx=10, pady=(10, 5))
        
        # Listbox with scrollbar
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, selectmode="single")
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)
        
        # Populate listbox
        for genre in sorted(available_genres):
            listbox.insert(tk.END, genre)
            if genre == current_genre:
                listbox.selection_set(listbox.size() - 1)
        
        # Result storage
        result: list[Optional[str]] = [None]
        
        def on_apply():
            selection = listbox.curselection()
            if selection:
                result[0] = listbox.get(selection[0])
            else:
                result[0] = "Unknown"
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Buttons
        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=10, pady=(5, 10))
        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(btns, text="Apply", command=on_apply).pack(side="right")
        
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result[0]

    # ---------- Main ----------
    def run(self):
        """Start the metadata editor application."""
        self.root.mainloop()


# ----------------------------
# Entrypoint
# ----------------------------
if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.abspath(__file__))
    directory = os.path.join(base_dir, "VideoFiles")
    print("Looking in:", directory)
    
    # Show welcome message about Manager.py
    print("\n" + "="*60)
    print("Meta Editor - Video Metadata Editor")
    print("="*60)
    print("For managing tags, genres, and commercial breaks,")
    print("use Manager.py or click 'Open Manager' button")
    print("="*60 + "\n")

    app = MetadataApp(directory)
    app.run()

# Dummy manager variable to prevent errors (rest will be deleted)
