"""
RetroViewer Manager - Unified GUI tool for metadata editing, tag/genre management, 
and commercial break timestamps.
"""

import os
import re
import time
import json
import tkinter as tk
from tkinter import ttk, simpledialog, messagebox, filedialog
import tkinter.font as tkfont
from typing import Optional
from mutagen.mp4 import MP4
import db_helper
import traceback

try:
    import ttkbootstrap as ttkb
except ImportError:
    ttkb = None  # Fall back to regular tk.Tk if not installed

try:
    import vlc  # type: ignore
except ImportError:
    vlc = None  # type: ignore


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


class RetroViewerManager:
    def __init__(self):
        # Base directory is parent of Scripts/
        script_dir = os.path.dirname(os.path.abspath(__file__))
        self.base_dir = os.path.dirname(script_dir)
        self.video_directory = os.path.join(self.base_dir, "Data", "VideoFiles")
        
        # Use ttkbootstrap with 'darkly' theme if available, otherwise regular Tk
        if ttkb:
            try:
                self.root = ttkb.Window(themename="darkly")
                # Try to set title bar to dark (platform-specific)
                try:
                    # Windows 11
                    self.root.tk.call('tk', 'windowingsystem')
                    self.root.update()
                    import ctypes
                    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
                    hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())  # type: ignore
                    ctypes.windll.dwmapi.DwmSetWindowAttribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(ctypes.c_int(2)), ctypes.sizeof(ctypes.c_int))  # type: ignore
                except:
                    pass  # Silently fail if not on Windows or if it doesn't work
            except Exception as e:
                print(f"Failed to load 'darkly' theme, falling back to default: {e}")
                self.root = tk.Tk()
        else:
            self.root = tk.Tk()
        
        self.root.title("RetroViewer Manager")
        
        # Maximize window
        self.root.state('zoomed')  # Windows
        try:
            self.root.attributes('-zoomed', True)  # Linux
        except:
            pass
        
        # Create notebook (tabbed interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Style customizations for darker appearance
        style = ttk.Style()
        
        # Darken backgrounds and borders, lighten text
        darker_bg = '#1a1a1a'  # Very dark background
        darker_border = '#0d0d0d'  # Almost black border
        light_text = '#e0e0e0'  # Light gray text for readability
        listbox_bg = '#2d2d2d'  # Slightly lighter for listboxes
        select_bg = '#404040'  # Selection background
        tab_bg = '#2d2d2d'  # Tab background
        
        # Configure all ttk widgets with light text
        style.configure('TNotebook.Tab', padding=[10, 5], foreground=light_text, background=tab_bg)
        style.map('TNotebook.Tab', foreground=[('selected', light_text), ('active', light_text)])
        
        style.configure('TFrame', background=darker_bg, bordercolor=darker_border)
        style.configure('TLabelframe', background=darker_bg, bordercolor=darker_border, darkcolor=darker_border, lightcolor=darker_border, foreground=light_text)
        style.configure('TLabelframe.Label', background=darker_bg, foreground=light_text)
        style.configure('TLabel', background=darker_bg, foreground=light_text)
        style.configure('TButton', foreground=light_text, background='#3d3d3d', bordercolor='#555555', relief='raised')
        style.map('TButton', background=[('active', '#4d4d4d'), ('!active', '#3d3d3d')], foreground=[('active', light_text)])
        style.configure('TCheckbutton', background=darker_bg, foreground=light_text)
        style.configure('TRadiobutton', background=darker_bg, foreground=light_text)
        
        # Configure root and dialog backgrounds
        self.root.configure(bg=darker_bg)
        self.root.option_add('*Dialog.msg.background', darker_bg)
        self.root.option_add('*Background', darker_bg)
        self.root.option_add('*Foreground', light_text)
        self.root.option_add('*Toplevel*Background', darker_bg)
        self.root.option_add('*Toplevel*Foreground', light_text)
        
        # Configure Listbox colors (tk widgets, not ttk)
        self.root.option_add('*Listbox.background', listbox_bg)
        self.root.option_add('*Listbox.foreground', light_text)
        self.root.option_add('*Listbox.selectBackground', select_bg)
        self.root.option_add('*Listbox.selectForeground', light_text)
        self.root.option_add('*Listbox.activestyle', 'none')  # Remove underline on selection
        
        # Configure Text widget colors
        self.root.option_add('*Text.background', listbox_bg)
        self.root.option_add('*Text.foreground', light_text)
        self.root.option_add('*Text.selectBackground', select_bg)
        self.root.option_add('*Text.selectForeground', light_text)
        
        # Configure Entry widget colors
        self.root.option_add('*Entry.background', listbox_bg)
        self.root.option_add('*Entry.foreground', light_text)
        self.root.option_add('*Entry.selectBackground', select_bg)
        self.root.option_add('*Entry.selectForeground', light_text)
        
        # Remove focus indicators (dotted rectangles) from ttk widgets
        style.layout('TButton', [('Button.border', {'children': [('Button.padding', {'children': [('Button.label', {'sticky': 'nswe'})], 'sticky': 'nswe'})], 'sticky': 'nswe', 'border': '1'})])  # type: ignore
        
        # PanedWindow styling - fix the light grey divider/background
        style.configure('TPanedwindow', background=darker_bg)
        style.configure('Sash', sashthickness=3, sashrelief='flat', background=darker_border)
        
        # Treeview styling
        style.configure('Treeview', 
            background=listbox_bg,
            foreground=light_text,
            fieldbackground=listbox_bg,
            borderwidth=0,
            relief='flat')
        style.configure('Treeview.Heading',
            background='#3d3d3d',
            foreground=light_text,
            borderwidth=1,
            relief='flat')
        style.map('Treeview.Heading',
            background=[('active', '#4d4d4d')],
            foreground=[('active', light_text)])
        style.map('Treeview',
            background=[('selected', select_bg)],
            foreground=[('selected', light_text)])
        
        # Create tabs (Meta Editor first)
        self.create_metadata_editor_tab()
        self.create_playlist_editor_tab()
        self.create_video_scanner_tab()
        self.create_tags_genres_tab()
        self.create_timestamp_tab()
        self.create_now_playing_tab()
        self.create_settings_tab()
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(self.root, textvariable=self.status_var, relief="sunken", anchor="w")
        status_bar.pack(side="bottom", fill="x")
    
    # ========== Metadata Editor Tab ==========
    def create_metadata_editor_tab(self):
        """Create the video metadata editor tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Video Metadata")
        
        # Data store for metadata editor
        self.COLUMNS = ("File Name", "Title", "Tags", "Year", "Genre", "Duration")
        self.FILTERABLE = {"Tags", "Year", "Genre"}
        self.all_rows = self.scan_video_files()
        self.active_filters: dict[str, set[str] | None] = {col: None for col in self.FILTERABLE}
        self.active_filters_norm: dict[str, set[str] | None] = {col: None for col in self.FILTERABLE}
        self.sort_state = {col: False for col in self.COLUMNS}
        self._last_filtered_rows = []
        self._single_click_job = None
        
        # Treeview
        self.tree = ttk.Treeview(tab, columns=self.COLUMNS, show="headings")
        for col in self.COLUMNS:
            self.tree.heading(col, text=col, command=lambda c=col: self.toggle_sort(c))
            self.tree.column(col, width=150, stretch=True)
        self.tree.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        tab.grid_rowconfigure(0, weight=1)
        tab.grid_columnconfigure(0, weight=1)
        
        # Status + buttons
        status_frame = ttk.Frame(tab)
        status_frame.grid(row=1, column=0, sticky="we", padx=10, pady=(0, 10))
        self.tree_status_var = tk.StringVar(value="No filters")
        ttk.Label(status_frame, textvariable=self.tree_status_var).pack(side="left")
        
        ttk.Button(status_frame, text="Reset Filters", command=self.reset_filters).pack(side="right")
        ttk.Button(status_frame, text="Filter", command=self.show_filter_dialog).pack(side="right", padx=(0, 5))
        
        # Bindings
        self.tree.bind("<ButtonRelease-1>", self.on_tree_button_release)
        self.tree.bind("<Double-1>", self.on_tree_double_click)
        
        # Fill table
        self.refresh_tree()
    
    def scan_video_files(self):
        """Load video metadata from database."""
        rows = []
        all_videos = db_helper.get_all_videos()
        if all_videos:
            for video in all_videos:
                # Format duration for display (e.g., "0:30" for 30 seconds)
                duration_str = ""
                if video.get('duration'):
                    duration = video['duration']
                    minutes = int(duration // 60)
                    seconds = int(duration % 60)
                    duration_str = f"{minutes}:{seconds:02d}"
                
                rows.append({
                    "File Name": video['filename'],
                    "Title": video['title'],
                    "Tags": video['tags'],
                    "Year": video['year'],
                    "Genre": video['genre'],
                    "Duration": duration_str
                })
        return rows
    
    def refresh_tree(self):
        """Refresh the metadata tree view."""
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
        self._last_filtered_rows = filtered
        
        for r in filtered:
            self.tree.insert("", "end", values=tuple(r[c] for c in self.COLUMNS))
        
        active_bits = []
        for col in self.FILTERABLE:
            sel = self.active_filters.get(col)
            if sel is not None:
                active_bits.append(f"{col}: {len(sel)}")
        summary = "No filters" if not active_bits else "Filters → " + " | ".join(active_bits)
        self.tree_status_var.set(f"{summary}    •   Showing {len(filtered)} of {len(self.all_rows)}")
        
        self._autosize_columns()
    
    @staticmethod
    def _norm(v):
        return str(v).strip().lower()
    
    def _autosize_columns(self):
        font = tkfont.Font()
        col_widths = {}
        
        for col in self.COLUMNS:
            header_w = font.measure(col) + 40
            max_w = header_w
            # Check all visible rows for accurate sizing
            for item in self.tree.get_children(""):
                text = str(self.tree.set(item, col))
                w = font.measure(text) + 40
                if w > max_w:
                    max_w = w
            
            # Set minimum and maximum widths based on column type
            if col == "File Name":
                max_w = max(min(max_w, 400), 250)  # Min 250px, Max 400px
            elif col == "Title":
                max_w = max(min(max_w, 300), 200)  # Min 200px, Max 300px
            elif col == "Tags":
                max_w = max(min(max_w, 250), 150)  # Min 150px, Max 250px
            elif col == "Year":
                max_w = max(min(max_w, 100), 80)   # Min 80px, Max 100px
            elif col == "Genre":
                max_w = max(min(max_w, 150), 100)  # Min 100px, Max 150px
            
            col_widths[col] = max_w
        
        # Get available width (account for scrollbar)
        self.tree.update_idletasks()
        available_width = self.tree.winfo_width() - 20  # 20px for scrollbar margin
        total_width = sum(col_widths.values())
        
        # Scale down proportionally if columns exceed available width
        if total_width > available_width and available_width > 100:
            scale = available_width / total_width
            for col in self.COLUMNS:
                col_widths[col] = int(col_widths[col] * scale)
        
        # Apply widths
        for col in self.COLUMNS:
            self.tree.column(col, width=col_widths[col], stretch=True)
    
    def reset_filters(self):
        self.active_filters = {col: None for col in self.FILTERABLE}
        self.active_filters_norm = {col: None for col in self.FILTERABLE}
        self.refresh_tree()
    
    def on_tree_button_release(self, event):
        """Handle potential single-click."""
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        
        if self._single_click_job is not None:
            self.root.after_cancel(self._single_click_job)
            self._single_click_job = None
        
        x, y = event.x, event.y
        self._single_click_job = self.root.after(200, lambda: self.handle_single_click(x, y))
    
    def on_tree_double_click(self, event):
        """Handle double-click to edit metadata."""
        if self._single_click_job is not None:
            self.root.after_cancel(self._single_click_job)
            self._single_click_job = None
        
        if self.tree.identify_region(event.x, event.y) != "cell":
            return
        
        self.handle_double_click(event.x, event.y)
    
    def handle_single_click(self, x, y):
        """Handle single-click on tree."""
        self._single_click_job = None
        
        item_id = self.tree.identify_row(y)
        col_id = self.tree.identify_column(x)
        if not item_id or not col_id:
            return
        
        col_index = int(col_id[1:]) - 1
        if col_index < 0 or col_index >= len(self.COLUMNS):
            return
        
        if self.tree.identify_region(x, y) != "cell":
            return
        
        self.tree.selection_set(item_id)
        values = self.tree.item(item_id, "values")
        if not values:
            return
        
        column_name = self.COLUMNS[col_index]
        file_name = values[0]
        
        # Single-click on File Name: copy to clipboard
        if column_name == "File Name":
            base_name, _ = os.path.splitext(file_name)
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(base_name)
                self.tree_status_var.set(f"Copied file name to clipboard: {base_name}")
            except Exception as e:
                print(f"Failed to copy to clipboard: {e}")
            return
    
    def handle_double_click(self, x, y):
        """Handle double-click to edit metadata."""
        item_id = self.tree.identify_row(y)
        col_id = self.tree.identify_column(x)
        if not item_id or not col_id:
            return
        
        col_index = int(col_id[1:]) - 1
        if col_index < 0 or col_index >= len(self.COLUMNS):
            return
        
        if self.tree.identify_region(x, y) != "cell":
            return
        
        values = self.tree.item(item_id, "values")
        if not values:
            return
        
        column_name = self.COLUMNS[col_index]
        file_name = values[0]
        
        # Do NOT edit File Name column
        if column_name == "File Name":
            return
        
        old_value = values[col_index]
        file_path = os.path.join(self.video_directory, file_name)
        
        # Use selection dialogs for Tags and Genre
        if column_name == "Tags":
            new_value = self.show_tags_selection_dialog(old_value)
        elif column_name == "Genre":
            new_value = self.show_genre_selection_dialog(old_value)
        elif column_name == "Title":
            new_value = self.show_title_edit_dialog(old_value, file_name)
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
    
    def show_filter_dialog(self):
        """Show filter dialog with options for all filterable columns."""
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.title("Filter Videos")
        dialog.geometry("500x600")
        
        # Center the dialog
        dialog.update_idletasks()
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        dialog_width = 500
        dialog_height = 600
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}") 
        
        ttk.Label(dialog, text="Select filters to apply:", font=('TkDefaultFont', 10, 'bold')).pack(pady=10)
        
        # Create notebook for each filter category
        filter_notebook = ttk.Notebook(dialog)
        filter_notebook.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        # Store check vars for each column
        all_check_vars = {}
        
        for column_name in self.FILTERABLE:
            # Create tab for this filter
            tab = ttk.Frame(filter_notebook)
            filter_notebook.add(tab, text=column_name)
            
            # Get unique values for this column
            def display_value_for_col(v):
                return _year_display(v) if column_name == "Year" else str(v)
            
            all_vals = [display_value_for_col(r.get(column_name, "")) for r in self.all_rows]
            unique_vals = sorted({v for v in all_vals if v}, key=lambda s: str(s).lower())
            
            # Create scrollable frame
            container = ttk.Frame(tab)
            container.pack(fill="both", expand=True, padx=5, pady=5)
            
            canvas = tk.Canvas(container, borderwidth=0, highlightthickness=0)
            vsb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
            canvas.configure(yscrollcommand=vsb.set)
            vsb.pack(side="right", fill="y")
            canvas.pack(side="left", fill="both", expand=True)
            
            inner = ttk.Frame(canvas)
            inner_id = canvas.create_window((0, 0), window=inner, anchor="nw")
            
            def _on_configure(canvas=canvas, inner_id=inner_id):
                canvas.configure(scrollregion=canvas.bbox("all"))
                canvas.itemconfig(inner_id, width=canvas.winfo_width())
            
            inner.bind("<Configure>", lambda e, c=canvas, iid=inner_id: _on_configure(c, iid))
            
            # Get currently active filters
            active_display = self.active_filters.get(column_name)
            check_vars = {}
            
            for v in unique_vals:
                initial = True if active_display is None else (v in active_display)
                var = tk.BooleanVar(value=initial)
                cb = ttk.Checkbutton(inner, text=v, variable=var)
                cb.pack(anchor="w", pady=2)
                check_vars[v] = var
            
            all_check_vars[column_name] = (check_vars, unique_vals)
            
            # Select/Clear All buttons for this tab
            btn_frame = ttk.Frame(tab)
            btn_frame.pack(fill="x", padx=5, pady=5)
            ttk.Button(btn_frame, text="Select All", 
                      command=lambda cvs=check_vars: [var.set(True) for var in cvs.values()]).pack(side="left", padx=(0, 5))
            ttk.Button(btn_frame, text="Clear All", 
                      command=lambda cvs=check_vars: [var.set(False) for var in cvs.values()]).pack(side="left")
        
        # Apply and Cancel buttons at bottom
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        def apply_filters():
            for column_name, (check_vars, unique_vals) in all_check_vars.items():
                chosen_display = [v for v, var in check_vars.items() if var.get()]
                if len(chosen_display) == 0 or len(chosen_display) == len(unique_vals):
                    self.active_filters[column_name] = None
                    self.active_filters_norm[column_name] = None
                else:
                    self.active_filters[column_name] = set(chosen_display)
                    self.active_filters_norm[column_name] = {self._norm(v) for v in chosen_display}
            
            self.refresh_tree()
            dialog.destroy()
        
        ttk.Button(button_frame, text="Apply Filters", command=apply_filters).pack(side="left", padx=(0, 5))
        ttk.Button(button_frame, text="Cancel", command=dialog.destroy).pack(side="left")
    
    def toggle_sort(self, column_name):
        """Sort by column."""
        reverse = self.sort_state[column_name]
        
        def try_int(val):
            try:
                return int(str(val).strip())
            except Exception:
                s = "" if val is None else str(val).lower()
                return s
        
        if column_name == "Year":
            key_fn = lambda r: try_int(_year_display(r.get(column_name, "")))
        else:
            key_fn = lambda r: try_int(r.get(column_name, ""))
        
        self.all_rows.sort(key=key_fn, reverse=reverse)
        self.sort_state[column_name] = not reverse
        self.refresh_tree()
    
    def show_checkbox_filter_popup(self, column_name, event):
        """Show filter popup for column."""
        def display_value_for_col(v):
            return _year_display(v) if column_name == "Year" else str(v)
        
        all_vals = [display_value_for_col(r.get(column_name, "")) for r in self.all_rows]
        unique_vals = sorted({v for v in all_vals}, key=lambda s: s.lower())
        
        popup = tk.Toplevel(self.root)
        popup.transient(self.root)
        popup.title(f"Filter: {column_name}")
        popup.attributes("-topmost", True)
        
        # Center the popup
        popup.update_idletasks()
        popup_width = 300
        popup_height = 400
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
        
        scroll_bindings_active = [False]
        
        def _on_mousewheel(event):
            bbox = canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = canvas.winfo_height()
                if content_height > canvas_height:
                    canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        
        def _on_mousewheel_linux(event):
            bbox = canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = canvas.winfo_height()
                if content_height > canvas_height:
                    if event.num == 4:
                        canvas.yview_scroll(-1, "units")
                    elif event.num == 5:
                        canvas.yview_scroll(1, "units")
        
        def _on_configure(_=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(inner_id, width=canvas.winfo_width())
            
            bbox = canvas.bbox("all")
            if bbox:
                content_height = bbox[3] - bbox[1]
                canvas_height = canvas.winfo_height()
                needs_scroll = content_height > canvas_height
                
                if needs_scroll:
                    if not scroll_bindings_active[0]:
                        popup.bind("<MouseWheel>", _on_mousewheel)
                        popup.bind("<Button-4>", _on_mousewheel_linux)
                        popup.bind("<Button-5>", _on_mousewheel_linux)
                        scroll_bindings_active[0] = True
                    vsb.pack(side="right", fill="y")
                else:
                    if scroll_bindings_active[0]:
                        popup.unbind("<MouseWheel>")
                        popup.unbind("<Button-4>")
                        popup.unbind("<Button-5>")
                        scroll_bindings_active[0] = False
                    vsb.pack_forget()
        
        inner.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", _on_configure)
        
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
    
    def show_tags_selection_dialog(self, current_tags: str) -> Optional[str]:
        """Show multi-select dialog for tags."""
        available_tags = db_helper.get_all_tags()
        
        if not available_tags:
            messagebox.showinfo("No Tags", "No tags available. Please add tags in 'Tags & Genres' tab first.")
            return None
        
        current_tag_list = [t.strip() for t in current_tags.split(',')] if current_tags and current_tags != "Unknown" else []
        
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.title("Select Tags")
        dialog.attributes("-topmost", True)
        
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
        
        check_vars = {}
        for tag in sorted(available_tags):
            var = tk.BooleanVar(value=(tag in current_tag_list))
            cb = ttk.Checkbutton(inner, text=tag, variable=var)
            cb.pack(anchor="w", pady=2)
            check_vars[tag] = var
        
        result: list[Optional[str]] = [None]
        
        def on_apply():
            selected = [tag for tag, var in check_vars.items() if var.get()]
            result[0] = ", ".join(selected) if selected else "Unknown"
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=10, pady=(5, 10))
        ttk.Button(btns, text="Select All", command=lambda: [var.set(True) for var in check_vars.values()]).pack(side="left")
        ttk.Button(btns, text="Clear All", command=lambda: [var.set(False) for var in check_vars.values()]).pack(side="left", padx=5)
        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(btns, text="Apply", command=on_apply).pack(side="right")
        
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result[0]
    
    def show_genre_selection_dialog(self, current_genre: str) -> Optional[str]:
        """Show single-select dialog for genre."""
        available_genres = db_helper.get_all_genres()
        
        if not available_genres:
            messagebox.showinfo("No Genres", "No genres available. Please add genres in 'Tags & Genres' tab first.")
            return None
        
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.title("Select Genre")
        dialog.attributes("-topmost", True)
        
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
        
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set, selectmode="single",
                            bg='#2d2d2d', fg='#e0e0e0',
                            selectbackground='#404040', selectforeground='#e0e0e0',
                            activestyle='none')
        scrollbar.config(command=listbox.yview)
        scrollbar.pack(side="right", fill="y")
        listbox.pack(side="left", fill="both", expand=True)
        
        for genre in sorted(available_genres):
            listbox.insert(tk.END, genre)
            if genre == current_genre:
                listbox.selection_set(listbox.size() - 1)
        
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
        
        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=10, pady=(5, 10))
        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(btns, text="Apply", command=on_apply).pack(side="right")
        
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result[0]
    
    def show_title_edit_dialog(self, current_title: str, file_name: str) -> Optional[str]:
        """Show larger edit dialog for title editing."""
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.title("Edit Title")
        dialog.attributes("-topmost", True)
        
        dialog.update_idletasks()
        dialog_width = 600
        dialog_height = 200
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        # File name label (clickable to copy)
        file_frame = ttk.Frame(dialog)
        file_frame.pack(anchor="w", padx=10, pady=(10, 5))
        
        ttk.Label(file_frame, text="File: ", font=("TkDefaultFont", 9)).pack(side="left")
        
        file_label = ttk.Label(file_frame, text=file_name, font=("TkDefaultFont", 9), 
                              foreground="blue", cursor="hand2")
        file_label.pack(side="left")
        
        def copy_filename(event=None):
            base_name, _ = os.path.splitext(file_name)
            try:
                dialog.clipboard_clear()
                dialog.clipboard_append(base_name)
                file_label.config(foreground="green")
                dialog.after(500, lambda: file_label.config(foreground="blue"))
            except Exception as e:
                print(f"Failed to copy to clipboard: {e}")
        
        file_label.bind("<Button-1>", copy_filename)
        
        ttk.Label(dialog, text="Edit Title:", font=("TkDefaultFont", 10, "bold")).pack(anchor="w", padx=10, pady=(5, 5))
        
        # Text entry with larger width
        entry_frame = ttk.Frame(dialog)
        entry_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        entry = ttk.Entry(entry_frame, font=("TkDefaultFont", 10))
        entry.pack(fill="x")
        entry.insert(0, current_title)
        entry.select_range(0, tk.END)
        entry.focus()
        
        result: list[Optional[str]] = [None]
        
        def on_apply():
            result[0] = entry.get().strip()
            dialog.destroy()
        
        def on_cancel():
            dialog.destroy()
        
        # Allow Enter key to apply
        entry.bind("<Return>", lambda e: on_apply())
        entry.bind("<Escape>", lambda e: on_cancel())
        
        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=10, pady=(5, 10))
        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(btns, text="Apply", command=on_apply).pack(side="right")
        
        dialog.grab_set()
        self.root.wait_window(dialog)
        return result[0]
    
    # ========== Video Scanner Tab ==========
    def create_video_scanner_tab(self):
        """Create the video file scanner tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Video Scanner")
        
        # Main container
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Video File Scanner", font=("TkDefaultFont", 14, "bold"))
        title_label.pack(pady=(0, 10))
        
        # Description
        desc_text = (
            "Scan the VideoFiles directory to find new videos and sync with the database.\n\n"
            "This will:\n"
            "  • Add newly detected .mp4 files to the database\n"
            "  • Remove database entries for deleted files\n"
            "  • Extract metadata from MP4 files"
        )
        desc_label = ttk.Label(main_frame, text=desc_text, font=("TkDefaultFont", 9), background='#222222', justify="left")
        desc_label.pack(anchor="w", pady=(0, 20))
        
        # Folder path display
        folder_frame = ttk.LabelFrame(main_frame, text="Scan Directory", padding=10)
        folder_frame.pack(fill="x", pady=(0, 20))
        
        folder_path = os.path.join(self.base_dir, "Data", "VideoFiles")
        folder_label = ttk.Label(folder_frame, text=folder_path, font=("TkDefaultFont", 9, "bold"), background='#222222')
        folder_label.pack(anchor="w")
        
        # Results display
        results_frame = ttk.LabelFrame(main_frame, text="Scan Results", padding=10)
        results_frame.pack(fill="both", expand=True, pady=(0, 20))
        
        self.scanner_text = tk.Text(results_frame, height=15, wrap="word", state="disabled")
        self.scanner_text.pack(side="left", fill="both", expand=True)
        
        # Button frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        
        self.scan_btn = ttk.Button(btn_frame, text="Scan VideoFiles Directory", command=self.run_video_scan)
        self.scan_btn.pack(side="left", padx=(0, 10))
        
        ttk.Button(btn_frame, text="Clear Results", command=self.clear_scanner_results).pack(side="left")
    
    def clear_scanner_results(self):
        """Clear the scanner results text area."""
        self.scanner_text.configure(state="normal")
        self.scanner_text.delete(1.0, tk.END)
        self.scanner_text.configure(state="disabled")
    
    def append_scanner_log(self, message):
        """Append a message to the scanner log."""
        self.scanner_text.configure(state="normal")
        self.scanner_text.insert(tk.END, message + "\n")
        self.scanner_text.see(tk.END)
        self.scanner_text.configure(state="disabled")
        self.root.update_idletasks()
    
    def run_video_scan(self):
        """Run the video file scanner."""
        self.scan_btn.config(state="disabled")
        self.clear_scanner_results()
        
        folder_path = os.path.join(self.base_dir, "Data", "VideoFiles")
        
        self.append_scanner_log("=" * 60)
        self.append_scanner_log("VIDEO FILE SCANNER")
        self.append_scanner_log("=" * 60)
        self.append_scanner_log(f"Scanning directory: {folder_path}")
        self.append_scanner_log("")
        
        try:
            # Check if directory exists
            if not os.path.isdir(folder_path):
                self.append_scanner_log(f"✗ ERROR: Directory '{folder_path}' not found")
                self.scan_btn.config(state="normal")
                return
            
            # Run the scan
            self.append_scanner_log("Scanning for .mp4 files...")
            added, removed = db_helper.scan_and_sync_videos(folder_path)
            
            self.append_scanner_log("")
            self.append_scanner_log("✓ Scan complete:")
            self.append_scanner_log(f"  • Added: {added} new videos")
            self.append_scanner_log(f"  • Removed: {removed} deleted videos")
            
            # Get all videos from database
            all_videos = db_helper.get_all_videos()
            self.append_scanner_log(f"  • Total videos in database: {len(all_videos)}")
            
            # Update "All Videos" playlist and refresh UI if changes occurred
            if added > 0 or removed > 0:
                # Create/update "All Videos" playlist with all videos
                self.append_scanner_log("")
                self.append_scanner_log("Updating 'All Videos' playlist...")
                existing_playlist = db_helper.get_playlist_by_name("All Videos")
                if not existing_playlist:
                    db_helper.create_playlist("All Videos", "Master playlist containing all videos in the database")
                    self.append_scanner_log("✓ Created 'All Videos' playlist")
                
                # Clear and repopulate All Videos playlist
                db_helper.clear_playlist("All Videos")
                
                for position, video in enumerate(sorted(all_videos, key=lambda v: v['filename']), 1):
                    db_helper.add_video_to_playlist("All Videos", video['filename'], position)
                
                self.append_scanner_log(f"✓ 'All Videos' playlist updated with {len(all_videos)} videos")
                
                # Refresh playlist list to show All Videos
                self.refresh_playlist_list()
                # Sync tags and genres from videos (silent)
                db_helper.sync_tags_from_videos()
                db_helper.sync_genres_from_videos()
                
                # Refresh all tabs (silent)
                self.all_rows = self.scan_video_files()
                self.refresh_tree()
                self.refresh_tags_list()
                self.refresh_genres_list()
            
            self.append_scanner_log("")
            self.append_scanner_log("=" * 60)
            self.append_scanner_log("✓ SCAN COMPLETED SUCCESSFULLY")
            self.append_scanner_log("=" * 60)
            
            self.status_var.set(f"Scan complete: {added} added, {removed} removed, {len(all_videos)} total")
            
        except Exception as e:
            self.append_scanner_log("")
            self.append_scanner_log(f"✗ ERROR: {e}")
            self.append_scanner_log("")
            import traceback
            self.append_scanner_log(traceback.format_exc())
            self.status_var.set("Scan failed - see log for details")
        
        finally:
            self.scan_btn.config(state="normal")
    
    # ========== Playlist Editor Tab ==========
    def create_playlist_editor_tab(self):
        """Create the playlist creator/editor tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Playlists")
        
        # Split into left (playlists) and right (videos)
        paned = ttk.PanedWindow(tab, orient="horizontal")
        paned.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left: Playlist list
        left_frame = ttk.Frame(paned)
        paned.add(left_frame, weight=1)
        
        playlist_frame = ttk.LabelFrame(left_frame, text="Playlists", padding=10)
        playlist_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        playlist_list_frame = ttk.Frame(playlist_frame)
        playlist_list_frame.pack(fill="both", expand=True)
        
        self.playlist_listbox = tk.Listbox(playlist_list_frame, selectmode="single",
                                          bg='#2d2d2d', fg='#e0e0e0',
                                          selectbackground='#404040', selectforeground='#e0e0e0',
                                          activestyle='none')
        self.playlist_listbox.pack(side="left", fill="both", expand=True)
        
        playlist_btns = tk.Frame(playlist_frame, bg='#414141')
        playlist_btns.pack(fill="x", pady=(5, 0))
        ttk.Button(playlist_btns, text="New Playlist", command=self.create_new_playlist).pack(side="left", padx=(0, 5))
        ttk.Button(playlist_btns, text="Delete", command=self.delete_selected_playlist).pack(side="left")
        
        # Import/Export buttons on the right
        ttk.Button(playlist_btns, text="Import Playlists", command=self.import_playlists).pack(side="right")
        ttk.Button(playlist_btns, text="Export Playlists", command=self.export_playlists).pack(side="right", padx=(0, 5))
        
        # Right: Videos in playlist
        right_frame = ttk.Frame(paned)
        paned.add(right_frame, weight=2)
        
        videos_frame = ttk.LabelFrame(right_frame, text="Playlist Videos", padding=10)
        videos_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        video_list_frame = ttk.Frame(videos_frame)
        video_list_frame.pack(fill="both", expand=True)
        
        self.playlist_videos_listbox = tk.Listbox(video_list_frame, selectmode="single",
                                                  bg='#2d2d2d', fg='#e0e0e0',
                                                  selectbackground='#404040', selectforeground='#e0e0e0',
                                                  activestyle='none')
        self.playlist_videos_listbox.pack(side="left", fill="both", expand=True)
        
        video_btns = tk.Frame(videos_frame, bg='#414141')
        video_btns.pack(fill="x", pady=(5, 0))
        ttk.Button(video_btns, text="Add Videos", command=self.add_videos_to_playlist).pack(side="left", padx=(0, 5))
        ttk.Button(video_btns, text="Remove", command=self.remove_video_from_playlist).pack(side="left", padx=(0, 5))
        ttk.Button(video_btns, text="Move Down", command=lambda: self.move_video_in_playlist(1)).pack(side="right")
        ttk.Button(video_btns, text="Move Up", command=lambda: self.move_video_in_playlist(-1)).pack(side="right", padx=(0, 5))
        
        # Track current playlist being edited
        self.current_playlist_name = None
        
        # Bindings
        self.playlist_listbox.bind("<<ListboxSelect>>", self.on_playlist_selected)
        
        # Load playlists
        self.refresh_playlist_list()
    
    def refresh_playlist_list(self):
        """Refresh the list of playlists."""
        # Save current selection
        selection = self.playlist_listbox.curselection()
        selected_name = None
        if selection:
            selected_name = self.playlist_listbox.get(selection[0])
        
        self.playlist_listbox.delete(0, tk.END)
        playlists = db_helper.list_playlists()
        for playlist in playlists:
            self.playlist_listbox.insert(tk.END, playlist['name'])
        
        # Restore selection if playlist still exists
        if selected_name:
            for i in range(self.playlist_listbox.size()):
                if self.playlist_listbox.get(i) == selected_name:
                    self.playlist_listbox.selection_set(i)
                    self.playlist_listbox.see(i)
                    break
    
    def on_playlist_selected(self, event=None):
        """Handle playlist selection."""
        selection = self.playlist_listbox.curselection()
        if not selection:
            # Don't clear videos if we just lost focus - only clear if truly deselected
            return
        
        playlist_name = self.playlist_listbox.get(selection[0])
        self.current_playlist_name = playlist_name  # Store current playlist
        
        # Load videos in playlist
        self.playlist_videos_listbox.delete(0, tk.END)
        videos = db_helper.get_playlist_videos(playlist_name)
        for video in videos:
            self.playlist_videos_listbox.insert(tk.END, video['filename'])
    
    def create_new_playlist(self):
        """Create a new playlist."""
        name = simpledialog.askstring("New Playlist", "Enter playlist name:", parent=self.root)
        if not name:
            return
        
        # Check if playlist exists
        if db_helper.get_playlist_by_name(name):
            messagebox.showerror("Error", f"Playlist '{name}' already exists!")
            return
        
        description = simpledialog.askstring("New Playlist", "Enter description (optional):", parent=self.root)
        
        try:
            db_helper.create_playlist(name, description or "")
            self.refresh_playlist_list()
            self.status_var.set(f"Created playlist: {name}")
            
            # Select the new playlist
            for i in range(self.playlist_listbox.size()):
                if self.playlist_listbox.get(i) == name:
                    self.playlist_listbox.selection_clear(0, tk.END)
                    self.playlist_listbox.selection_set(i)
                    self.playlist_listbox.see(i)
                    self.on_playlist_selected()
                    break
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create playlist:\n{e}")
    
    def delete_selected_playlist(self):
        """Delete the selected playlist."""
        selection = self.playlist_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a playlist to delete.")
            return
        
        playlist_name = self.playlist_listbox.get(selection[0])
        
        # Prevent deletion of All Videos playlist
        if playlist_name == "All Videos":
            messagebox.showwarning("Cannot Delete", "The 'All Videos' playlist cannot be deleted. It is automatically maintained by the Video Scanner.")
            return
        
        # Confirm deletion
        if not messagebox.askyesno("Confirm Delete", f"Delete playlist '{playlist_name}'?"):
            return
        
        try:
            # Get remaining playlists to determine fallback
            remaining_playlists = db_helper.list_playlists()
            # Exclude the one being deleted
            remaining_playlists = [p for p in remaining_playlists if p['name'] != playlist_name]
            # Always use All Videos as fallback (guaranteed to exist)
            fallback_playlist = "All Videos"
            
            # Check if this playlist is used in settings
            active_playlist = db_helper.get_setting("active_playlist", fallback_playlist)
            feature_playlist = db_helper.get_setting("feature_playlist", fallback_playlist)
            
            db_helper.delete_playlist(playlist_name)
            
            # Also delete text file if it exists
            playlist_file = os.path.join(self.base_dir, "Data", "Playlists", f"{playlist_name}.txt")
            if os.path.exists(playlist_file):
                os.remove(playlist_file)
            
            # Update settings if deleted playlist was in use
            if active_playlist == playlist_name:
                db_helper.set_setting("active_playlist", fallback_playlist, "Current playlist used by Media Player")
            if feature_playlist == playlist_name:
                db_helper.set_setting("feature_playlist", fallback_playlist, "Playlist used for commercials in Feature Player")
            
            # Refresh settings widgets if they exist
            if hasattr(self, 'settings_comboboxes'):
                playlist_names = [p['name'] for p in remaining_playlists]
                for key in ["active_playlist", "feature_playlist"]:
                    if key in self.settings_comboboxes:
                        combobox = self.settings_comboboxes[key]
                        current_value = db_helper.get_setting(key, fallback_playlist)
                        # Update the combobox values and selection
                        combobox['values'] = playlist_names
                        self.settings_widgets[key].set(current_value)
            
            self.refresh_playlist_list()
            self.playlist_videos_listbox.delete(0, tk.END)
            self.status_var.set(f"Deleted playlist: {playlist_name}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to delete playlist:\n{e}")
    
    def export_selected_playlist(self):
        """Export selected playlist to text file."""
        selection = self.playlist_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a playlist to export.")
            return
        
        playlist_name = self.playlist_listbox.get(selection[0])
        
        try:
            playlist_dir = os.path.join(self.base_dir, "Data", "Playlists")
            os.makedirs(playlist_dir, exist_ok=True)
            filename = f"{playlist_name}.txt"
            save_path = os.path.join(playlist_dir, filename)
            
            db_helper.export_playlist_to_file(playlist_name, save_path)
            
            messagebox.showinfo("Export Complete", f"Exported to:\n{save_path}")
            self.status_var.set(f"Exported: {playlist_name}")
        except Exception as e:
            messagebox.showerror("Export Failed", f"Could not export playlist:\n{e}")
    
    def add_videos_to_playlist(self):
        """Add videos to the selected playlist."""
        # Use stored playlist name instead of selection (which may be lost when clicking videos)
        if not self.current_playlist_name:
            messagebox.showwarning("No Selection", "Please select a playlist first.")
            return
        
        playlist_name = self.current_playlist_name
        
        # Get all videos
        all_videos = db_helper.get_all_videos()
        if not all_videos:
            messagebox.showinfo("No Videos", "No videos available in database.")
            return
        
        # Get videos already in playlist
        playlist_videos = db_helper.get_playlist_videos(playlist_name)
        playlist_filenames = {v['filename'] for v in playlist_videos}
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.title(f"Add Videos to '{playlist_name}'")
        dialog.attributes("-topmost", True)
        
        dialog.update_idletasks()
        dialog_width = 800
        dialog_height = 700
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        ttk.Label(dialog, text="Select videos to add (multiple allowed):").pack(anchor="w", padx=10, pady=(10, 5))
        
        # Search box
        search_frame = ttk.Frame(dialog)
        search_frame.pack(fill="x", padx=10, pady=(0, 5))
        ttk.Label(search_frame, text="Search:").pack(side="left", padx=(0, 5))
        search_var = tk.StringVar()
        search_entry = ttk.Entry(search_frame, textvariable=search_var)
        search_entry.pack(side="left", fill="x", expand=True)
        
        # Listbox with checkboxes (we'll use extended selection mode)
        list_frame = ttk.Frame(dialog)
        list_frame.pack(fill="both", expand=True, padx=10, pady=5)
        
        video_listbox = tk.Listbox(list_frame, selectmode="extended",
                                   bg='#2d2d2d', fg='#e0e0e0',
                                   selectbackground='#404040', selectforeground='#e0e0e0',
                                   activestyle='none')
        video_listbox.pack(side="left", fill="both", expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", command=video_listbox.yview)
        scrollbar.pack(side="right", fill="y")
        video_listbox.configure(yscrollcommand=scrollbar.set)
        
        # Populate listbox
        all_filenames = []
        for video in sorted(all_videos, key=lambda v: v['filename'].lower()):
            filename = video['filename']
            if filename not in playlist_filenames:
                display = filename
                if video['title']:
                    display = f"{filename} - {video['title']}"
                video_listbox.insert(tk.END, display)
                all_filenames.append(filename)
        
        # Search functionality
        def filter_videos(*args):
            search_text = search_var.get().lower()
            video_listbox.delete(0, tk.END)
            filtered_filenames = []
            for video in sorted(all_videos, key=lambda v: v['filename'].lower()):
                filename = video['filename']
                if filename not in playlist_filenames:
                    display = filename
                    if video['title']:
                        display = f"{filename} - {video['title']}"
                    if search_text in display.lower():
                        video_listbox.insert(tk.END, display)
                        filtered_filenames.append(filename)
            all_filenames.clear()
            all_filenames.extend(filtered_filenames)
        
        search_var.trace_add("write", filter_videos)
        
        # Buttons
        def on_add():
            selection_indices = video_listbox.curselection()
            if not selection_indices:
                messagebox.showwarning("No Selection", "Please select videos to add.")
                return
            
            selected_filenames = [all_filenames[i] for i in selection_indices]
            
            try:
                # Get current max position
                current_videos = db_helper.get_playlist_videos(playlist_name)
                next_position = len(current_videos) + 1
                
                for filename in selected_filenames:
                    db_helper.add_video_to_playlist(playlist_name, filename, next_position)
                    next_position += 1
                
                dialog.destroy()
                self.on_playlist_selected()
                self.status_var.set(f"Added {len(selected_filenames)} video(s) to {playlist_name}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to add videos:\n{e}")
        
        def on_cancel():
            dialog.destroy()
        
        btns = ttk.Frame(dialog)
        btns.pack(fill="x", padx=10, pady=(5, 10))
        ttk.Button(btns, text="Cancel", command=on_cancel).pack(side="right", padx=(5, 0))
        ttk.Button(btns, text="Add Selected", command=on_add).pack(side="right")
        
        dialog.grab_set()
        search_entry.focus()
    
    def remove_video_from_playlist(self):
        """Remove selected video from playlist."""
        if not self.current_playlist_name:
            messagebox.showwarning("No Playlist", "Please select a playlist first.")
            return
        
        video_selection = self.playlist_videos_listbox.curselection()
        if not video_selection:
            messagebox.showwarning("No Video", "Please select a video to remove.")
            return
        
        playlist_name = self.current_playlist_name
        filename = self.playlist_videos_listbox.get(video_selection[0])
        
        try:
            db_helper.remove_video_from_playlist(playlist_name, filename)
            self.on_playlist_selected()
            self.status_var.set(f"Removed from {playlist_name}: {filename}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove video:\n{e}")
    
    def move_video_in_playlist(self, direction):
        """Move video up (-1) or down (1) in playlist."""
        if not self.current_playlist_name:
            messagebox.showwarning("No Playlist", "Please select a playlist first.")
            return
        
        video_selection = self.playlist_videos_listbox.curselection()
        if not video_selection:
            messagebox.showwarning("No Video", "Please select a video to move.")
            return
        
        playlist_name = self.current_playlist_name
        current_index = video_selection[0]
        
        # Get all videos in playlist
        videos = db_helper.get_playlist_videos(playlist_name)
        if not videos:
            return
        
        # Check bounds
        new_index = current_index + direction
        if new_index < 0 or new_index >= len(videos):
            return
        
        # Swap positions
        video1 = videos[current_index]
        video2 = videos[new_index]
        
        try:
            # Update positions (1-based in database)
            db_helper.update_playlist_video_position(playlist_name, video1['filename'], new_index + 1)
            db_helper.update_playlist_video_position(playlist_name, video2['filename'], current_index + 1)
            
            # Refresh video list (not playlist list)
            self.playlist_videos_listbox.delete(0, tk.END)
            updated_videos = db_helper.get_playlist_videos(playlist_name)
            for video in updated_videos:
                self.playlist_videos_listbox.insert(tk.END, video['filename'])
            
            # Restore video selection at new position
            self.playlist_videos_listbox.selection_clear(0, tk.END)
            self.playlist_videos_listbox.selection_set(new_index)
            self.playlist_videos_listbox.see(new_index)
            self.playlist_videos_listbox.focus_set()
            
            self.status_var.set(f"Moved: {video1['filename']}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move video:\n{e}")
    
    # ========== Tags & Genres Tab ==========
    def create_tags_genres_tab(self):
        """Create the tags and genres management tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Tags & Genres")
        
        # Main container with two columns
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left column - Tags
        tags_frame = ttk.LabelFrame(main_frame, text="Tags", padding=10)
        tags_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Right column - Genres
        genres_frame = ttk.LabelFrame(main_frame, text="Genres", padding=10)
        genres_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # === Tags Section ===
        tags_list_frame = ttk.Frame(tags_frame)
        tags_list_frame.pack(fill="both", expand=True)
        
        self.tags_listbox = tk.Listbox(tags_list_frame,
                                       bg='#2d2d2d', fg='#e0e0e0',
                                       selectbackground='#404040', selectforeground='#e0e0e0',
                                       activestyle='none')
        self.tags_listbox.pack(side="left", fill="both", expand=True)
        
        tags_btn_frame = tk.Frame(tags_frame, bg='#414141')
        tags_btn_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(tags_btn_frame, text="Add", command=self.add_tag).pack(side="left", padx=(0, 5))
        ttk.Button(tags_btn_frame, text="Delete", command=self.delete_tag).pack(side="left", padx=(0, 5))
        ttk.Button(tags_btn_frame, text="Sync from Videos", command=self.sync_tags).pack(side="left")
        
        ttk.Button(tags_btn_frame, text="Export", command=self.export_tags).pack(side="right", padx=(5, 0))
        ttk.Button(tags_btn_frame, text="Import", command=self.import_tags).pack(side="right")
        
        # === Genres Section ===
        genres_list_frame = ttk.Frame(genres_frame)
        genres_list_frame.pack(fill="both", expand=True)
        
        self.genres_listbox = tk.Listbox(genres_list_frame,
                                         bg='#2d2d2d', fg='#e0e0e0',
                                         selectbackground='#404040', selectforeground='#e0e0e0',
                                         activestyle='none')
        self.genres_listbox.pack(side="left", fill="both", expand=True)
        
        genres_btn_frame = tk.Frame(genres_frame, bg='#414141')
        genres_btn_frame.pack(fill="x", pady=(5, 0))
        ttk.Button(genres_btn_frame, text="Add", command=self.add_genre).pack(side="left", padx=(0, 5))
        ttk.Button(genres_btn_frame, text="Delete", command=self.delete_genre).pack(side="left", padx=(0, 5))
        ttk.Button(genres_btn_frame, text="Sync from Videos", command=self.sync_genres).pack(side="left")
        
        ttk.Button(genres_btn_frame, text="Export", command=self.export_genres).pack(side="right", padx=(5, 0))
        ttk.Button(genres_btn_frame, text="Import", command=self.import_genres).pack(side="right")
        
        # Initial load
        self.refresh_tags_list()
        self.refresh_genres_list()
    
    def refresh_tags_list(self):
        self.tags_listbox.delete(0, tk.END)
        for tag in db_helper.get_all_tags():
            self.tags_listbox.insert(tk.END, tag)
    
    def add_tag(self):
        new_tag = simpledialog.askstring("Add Tag", "Enter new tag name:", parent=self.root)
        if new_tag:
            if db_helper.add_tag(new_tag):
                self.refresh_tags_list()
                self.status_var.set(f"Added tag: {new_tag}")
            else:
                messagebox.showerror("Error", "Failed to add tag")
    
    def delete_tag(self):
        selection = self.tags_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a tag to delete")
            return
        tag = self.tags_listbox.get(selection[0])
        if messagebox.askyesno("Confirm Delete", f"Delete tag '{tag}'?\n\nThis will remove it from all videos and their MP4 files."):
            try:
                # Get all videos that have this tag
                all_videos = db_helper.get_all_videos()
                updated_count = 0
                
                for video in all_videos:
                    if video['tags'] and tag in [t.strip() for t in video['tags'].split(',')]:
                        # Remove tag from video's tag list
                        video_tags = [t.strip() for t in video['tags'].split(',') if t.strip()]
                        video_tags = [t for t in video_tags if t != tag]
                        new_tags = ', '.join(video_tags) if video_tags else ''
                        
                        # Update database
                        db_helper.update_video_metadata(video['filename'], tags=new_tags)
                        
                        # Update MP4 file
                        file_path = db_helper.get_absolute_path(video['file_path'])
                        if os.path.exists(file_path):
                            update_metadata(file_path, tags=new_tags)
                        
                        updated_count += 1
                
                # Delete tag from tags table
                if db_helper.delete_tag(tag):
                    self.refresh_tags_list()
                    self.status_var.set(f"Deleted tag '{tag}' from {updated_count} video(s)")
                    messagebox.showinfo("Success", f"Removed tag '{tag}' from {updated_count} video(s) and their MP4 files.")
                else:
                    messagebox.showerror("Error", "Failed to delete tag")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete tag: {e}")
    
    def sync_tags(self):
        db_helper.sync_tags_from_videos()
        self.refresh_tags_list()
        messagebox.showinfo("Sync Complete", "Tags synced from all videos")
        self.status_var.set("Tags synced from videos")
    
    def refresh_genres_list(self):
        self.genres_listbox.delete(0, tk.END)
        for genre in db_helper.get_all_genres():
            self.genres_listbox.insert(tk.END, genre)
    
    def add_genre(self):
        new_genre = simpledialog.askstring("Add Genre", "Enter new genre name:", parent=self.root)
        if new_genre:
            if db_helper.add_genre(new_genre):
                self.refresh_genres_list()
                self.status_var.set(f"Added genre: {new_genre}")
            else:
                messagebox.showerror("Error", "Failed to add genre")
    
    def delete_genre(self):
        selection = self.genres_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a genre to delete")
            return
        genre = self.genres_listbox.get(selection[0])
        if messagebox.askyesno("Confirm Delete", f"Delete genre '{genre}'?\n\nThis will remove it from all videos and their MP4 files."):
            try:
                # Get all videos that have this genre
                all_videos = db_helper.get_all_videos()
                updated_count = 0
                
                for video in all_videos:
                    if video['genre'] and genre in [g.strip() for g in video['genre'].split(',')]:
                        # Remove genre from video's genre list
                        video_genres = [g.strip() for g in video['genre'].split(',') if g.strip()]
                        video_genres = [g for g in video_genres if g != genre]
                        new_genre = ', '.join(video_genres) if video_genres else ''
                        
                        # Update database
                        db_helper.update_video_metadata(video['filename'], genre=new_genre)
                        
                        # Update MP4 file
                        file_path = db_helper.get_absolute_path(video['file_path'])
                        if os.path.exists(file_path):
                            update_metadata(file_path, genre=new_genre)
                        
                        updated_count += 1
                
                # Delete genre from genres table
                if db_helper.delete_genre(genre):
                    self.refresh_genres_list()
                    self.status_var.set(f"Deleted genre '{genre}' from {updated_count} video(s)")
                    messagebox.showinfo("Success", f"Removed genre '{genre}' from {updated_count} video(s) and their MP4 files.")
                else:
                    messagebox.showerror("Error", "Failed to delete genre")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to delete genre: {e}")
    
    def sync_genres(self):
        db_helper.sync_genres_from_videos()
        self.refresh_genres_list()
        messagebox.showinfo("Sync Complete", "Genres synced from all videos")
        self.status_var.set("Genres synced from videos")
    
    # ========== Timestamp Manager Tab ==========
    def create_timestamp_tab(self):
        """Create the timestamp management tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Commercial Breaks")
        
        if vlc is None:
            # Show warning if VLC is not available
            warning_frame = ttk.Frame(tab)
            warning_frame.pack(fill="both", expand=True, padx=20, pady=20)
            
            ttk.Label(warning_frame, text="⚠️  VLC Library Required", 
                     font=('TkDefaultFont', 14, 'bold')).pack(pady=(0, 10))
            ttk.Label(warning_frame, text="The timestamp manager requires python-vlc to detect video durations.",
                     wraplength=600).pack(pady=(0, 5))
            ttk.Label(warning_frame, text="Install with: pip install python-vlc",
                     font=('TkDefaultFont', 10, 'bold')).pack(pady=(0, 20))
            ttk.Label(warning_frame, text="After installation, restart this application.",
                     font=('TkDefaultFont', 9, 'italic')).pack()
            return
        
        # Main container with two columns
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left column - Movie list
        movies_frame = ttk.LabelFrame(main_frame, text="Feature Movies", padding=10)
        movies_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Right column - Timestamps
        timestamps_frame = ttk.LabelFrame(main_frame, text="Commercial Breaks", padding=10)
        timestamps_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=2)
        
        # === Movies Section ===
        movies_list_frame = ttk.Frame(movies_frame)
        movies_list_frame.pack(fill="both", expand=True)
        
        self.movies_listbox = tk.Listbox(movies_list_frame,
                                         bg='#2d2d2d', fg='#e0e0e0',
                                         selectbackground='#404040', selectforeground='#e0e0e0',
                                         activestyle='none',
                                         borderwidth=0, highlightthickness=0)
        self.movies_listbox.pack(side="left", fill="both", expand=True)
        
        # Movie info display
        info_frame = ttk.Frame(movies_frame)
        info_frame.pack(fill="x", pady=(10, 0))
        ttk.Label(info_frame, text="Duration:").grid(row=0, column=0, sticky="w")
        self.duration_var = tk.StringVar(value="Select a movie")
        ttk.Label(info_frame, textvariable=self.duration_var).grid(row=0, column=1, sticky="w", padx=(5, 0))
        
        # === Timestamps Section ===
        # Start/End times in a LabelFrame
        start_end_frame = tk.LabelFrame(timestamps_frame, text="Movie Start/End Times", 
                                       bg='#1a1a1a', fg='#e0e0e0', 
                                       borderwidth=1, relief='flat')
        start_end_frame.pack(fill="x", pady=(0, 10), padx=10)
        
        ttk.Label(start_end_frame, text="When to begin/stop playback - Format: Hour : Minute : Second . Millisecond (00:00:00.00)", 
                  font=('TkDefaultFont', 8), background='#222222', foreground="gray").pack(anchor="w", pady=(10, 5), padx=10)
        
        times_frame = ttk.Frame(start_end_frame)
        times_frame.pack(fill="x", padx=10, pady=(0, 10))
        
        # Start Time
        ttk.Label(times_frame, text="Start Time:", font=('TkDefaultFont', 8), background='#222222').grid(row=0, column=0, sticky="w")
        self.start_hour = tk.StringVar(value="0")
        self.start_min = tk.StringVar(value="00")
        self.start_sec = tk.StringVar(value="00")
        self.start_ms = tk.StringVar(value="00")
        ttk.Entry(times_frame, textvariable=self.start_hour, width=3).grid(row=0, column=1, sticky="w", padx=(5, 2))
        ttk.Label(times_frame, text=":").grid(row=0, column=2, sticky="w")
        ttk.Entry(times_frame, textvariable=self.start_min, width=3).grid(row=0, column=3, sticky="w", padx=(2, 2))
        ttk.Label(times_frame, text=":").grid(row=0, column=4, sticky="w")
        ttk.Entry(times_frame, textvariable=self.start_sec, width=3).grid(row=0, column=5, sticky="w", padx=(2, 2))
        ttk.Label(times_frame, text=".").grid(row=0, column=6, sticky="w")
        ttk.Entry(times_frame, textvariable=self.start_ms, width=3).grid(row=0, column=7, sticky="w", padx=(2, 15))
        
        # End Time
        ttk.Label(times_frame, text="End Time (Duration):", font=('TkDefaultFont', 8), background='#222222').grid(row=0, column=8, sticky="w", padx=(10, 0))
        self.end_hour = tk.StringVar(value="0")
        self.end_min = tk.StringVar(value="00")
        self.end_sec = tk.StringVar(value="00")
        self.end_ms = tk.StringVar(value="00")
        ttk.Entry(times_frame, textvariable=self.end_hour, width=3).grid(row=0, column=9, sticky="w", padx=(5, 2))
        ttk.Label(times_frame, text=":").grid(row=0, column=10, sticky="w")
        ttk.Entry(times_frame, textvariable=self.end_min, width=3).grid(row=0, column=11, sticky="w", padx=(2, 2))
        ttk.Label(times_frame, text=":").grid(row=0, column=12, sticky="w")
        ttk.Entry(times_frame, textvariable=self.end_sec, width=3).grid(row=0, column=13, sticky="w", padx=(2, 2))
        ttk.Label(times_frame, text=".").grid(row=0, column=14, sticky="w")
        ttk.Entry(times_frame, textvariable=self.end_ms, width=3).grid(row=0, column=15, sticky="w", padx=(2, 15))
        
        ttk.Button(times_frame, text="Save Times", command=self.save_start_end_times).grid(row=0, column=16, sticky="w", padx=(10, 0))
        
        # Commercial breaks list
        breaks_list_frame = ttk.Frame(timestamps_frame)
        breaks_list_frame.pack(fill="both", expand=True, pady=(5, 0))
        
        self.breaks_listbox = tk.Listbox(breaks_list_frame,
                                         bg='#2d2d2d', fg='#e0e0e0',
                                         selectbackground='#404040', selectforeground='#e0e0e0',
                                         activestyle='none',
                                         borderwidth=0, highlightthickness=0)
        self.breaks_listbox.pack(side="left", fill="both", expand=True)
        
        # Buttons for managing breaks
        breaks_btn_frame = tk.Frame(timestamps_frame, bg='#414141')
        breaks_btn_frame.pack(fill="x", pady=(10, 0))
        
        ttk.Button(breaks_btn_frame, text="Add Break", command=self.add_break).pack(side="left", padx=(0, 5))
        ttk.Button(breaks_btn_frame, text="Delete Break", command=self.delete_break).pack(side="left", padx=(0, 5))
        ttk.Button(breaks_btn_frame, text="Reset", command=self.reset_movie_data).pack(side="left")
        
        # Import/Export buttons on the right side
        ttk.Button(breaks_btn_frame, text="Export Timestamps", command=self.export_timestamps).pack(side="right", padx=(5, 0))
        ttk.Button(breaks_btn_frame, text="Import Timestamps", command=self.import_timestamps).pack(side="right")
        
        # Store current movie
        self.current_movie = {"id": None, "filename": None}
        
        # Bind movie selection
        self.movies_listbox.bind('<<ListboxSelect>>', self.on_movie_select)
        
        # Initial load
        self.load_movies()
        
        # Instructions
        instructions = ttk.Label(tab, text="Select a movie, then add commercial break times. Start/end times are auto-detected.", 
                                font=('TkDefaultFont', 8, 'italic'))
        instructions.pack(pady=(5, 0))
    
    @staticmethod
    def format_time_from_seconds(seconds):
        """Convert seconds to MM:SS.MS format."""
        minutes = int(seconds // 60)
        secs = seconds % 60
        return f"{minutes}:{secs:05.2f}"
    
    @staticmethod
    def parse_time_to_seconds(time_str):
        """Parse MM:SS.MS or H:MM:SS format to seconds."""
        parts = time_str.split(':')
        if len(parts) == 2:
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 3:
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        return 0
    
    def get_video_duration(self, file_path: str) -> float | None:
        """Get video duration in seconds using VLC."""
        if vlc is None:
            return None
        try:
            # Run VLC headless - no video window, no audio, quiet mode
            instance = vlc.Instance('--no-video', '--no-audio', '--quiet', '--no-xlib')  # type: ignore
            media = instance.media_new(file_path)  # type: ignore
            
            # Parse the media file to get duration (no playback needed)
            media.parse_with_options(vlc.MediaParseFlag.local, 0)  # type: ignore
            
            # Wait for parsing to complete
            max_wait = 50
            while max_wait > 0:
                if media.get_duration() > 0:
                    break
                time.sleep(0.1)
                max_wait -= 1
            
            duration_ms = media.get_duration()
            
            if duration_ms > 0:
                return duration_ms / 1000.0
            return None
        except Exception as e:
            print(f"Error getting video duration: {e}")
            return None
    
    def load_movies(self):
        """Load feature movies from MediaFiles."""
        self.movies_listbox.delete(0, tk.END)
        media_folder = os.path.join(self.base_dir, "Data", "MediaFiles")
        
        if not os.path.exists(media_folder):
            return
        
        for filename in sorted(os.listdir(media_folder)):
            if filename.lower().endswith(('.mp4', '.avi', '.mkv', '.mov')):
                self.movies_listbox.insert(tk.END, filename)
    
    def load_timestamps(self, movie_id, filename):
        """Load timestamps for selected movie."""
        self.breaks_listbox.delete(0, tk.END)
        
        # Get timestamps from database
        timestamps = db_helper.get_timestamps(movie_id)
        if timestamps:
            self._set_time_fields(self._normalize_time_format(timestamps[0]['start_time']), 'start')
            self._set_time_fields(self._normalize_time_format(timestamps[0]['end_time']), 'end')
            self.duration_var.set(self._normalize_time_format(timestamps[0]['end_time']))
        else:
            # Auto-detect duration
            media_folder = os.path.join(self.base_dir, "Data", "MediaFiles")
            file_path = os.path.join(media_folder, filename)
            
            duration = self.get_video_duration(file_path)
            if duration:
                formatted_duration = self.format_time_from_seconds(duration)
                self._set_time_fields(self._normalize_time_format("0:00:00.00"), 'start')
                self._set_time_fields(self._normalize_time_format(formatted_duration), 'end')
                self.duration_var.set(self._normalize_time_format(formatted_duration))
            else:
                self._set_time_fields(self._normalize_time_format("0:00:00.00"), 'start')
                self._set_time_fields(self._normalize_time_format("0:00:00.00"), 'end')
                self.duration_var.set("Unknown")
        
        # Get commercial breaks and sort by time
        breaks = db_helper.get_commercial_breaks(movie_id)
        sorted_breaks = sorted(breaks, key=lambda b: self._time_to_seconds(b['break_time']))
        for i, break_data in enumerate(sorted_breaks, 1):
            # Normalize time to full H:MM:SS.MS format for display
            time_str = self._normalize_time_format(break_data['break_time'])
            self.breaks_listbox.insert(tk.END, f"Break {i}: {time_str}")
    
    def on_movie_select(self, event):
        """Handle movie selection."""
        selection = self.movies_listbox.curselection()
        if not selection:
            return
        
        filename = self.movies_listbox.get(selection[0])
        
        # Get or create movie in database
        movie = db_helper.get_feature_movie_by_filename(filename)
        if not movie:
            media_folder = os.path.join(self.base_dir, "Data", "MediaFiles")
            file_path = os.path.join(media_folder, filename)
            rel_path = os.path.join("Data", "MediaFiles", filename)
            title = os.path.splitext(filename)[0]
            
            movie_id = db_helper.add_feature_movie(filename, title, rel_path)
            movie = {"id": movie_id, "filename": filename, "title": title}
        
        self.current_movie["id"] = movie["id"]
        self.current_movie["filename"] = movie["filename"]
        
        # Check if timestamps exist, if not auto-detect and save
        timestamps = db_helper.get_timestamps(movie["id"])
        if not timestamps:
            self.status_var.set(f"Detecting duration for {filename}...")
            self.root.update_idletasks()
            
            media_folder = os.path.join(self.base_dir, "Data", "MediaFiles")
            file_path = os.path.join(media_folder, filename)
            duration = self.get_video_duration(file_path)
            
            if duration:
                formatted_duration = self.format_time_from_seconds(duration)
                # Normalize to full format before saving
                start_time = self._normalize_time_format("0:00:00.00")
                end_time = self._normalize_time_format(formatted_duration)
                # Save to database immediately
                db_helper.add_timestamp(movie["id"], start_time, end_time)
                self.status_var.set(f"Duration saved: {end_time}")
            else:
                self.status_var.set(f"Selected: {filename} (duration detection failed)")
        else:
            self.status_var.set(f"Selected: {filename}")
        
        self.load_timestamps(movie["id"], movie["filename"])
    
    def add_break(self):
        """Add a commercial break timestamp."""
        if self.current_movie["id"] is None:
            messagebox.showinfo("No Movie Selected", "Please select a movie first")
            return
        
        # Create custom dialog for time input
        time_str = self._show_time_picker_dialog("Add Commercial Break")
        
        if not time_str:
            return
        
        # Normalize to full format before saving
        time_str = self._normalize_time_format(time_str)
        
        # Add to database
        db_helper.add_commercial_break(self.current_movie["id"], time_str)
        
        # Save timestamps if they don't exist
        timestamps = db_helper.get_timestamps(self.current_movie["id"])
        if not timestamps:
            try:
                start_time = self._normalize_time_format(self._get_time_from_fields('start'))
                end_time = self._normalize_time_format(self._get_time_from_fields('end'))
                db_helper.add_timestamp(self.current_movie["id"], start_time, end_time)
            except ValueError:
                pass  # Skip if times aren't valid yet
        
        # Refresh display
        self.load_timestamps(self.current_movie["id"], self.current_movie["filename"])
        self.status_var.set(f"Added break at {time_str}")
    
    def delete_break(self):
        """Delete selected commercial break."""
        selection = self.breaks_listbox.curselection()
        if not selection:
            messagebox.showinfo("No Break Selected", "Please select a break to delete")
            return
        
        if self.current_movie["id"] is None:
            return
        
        break_index = selection[0]
        breaks = db_helper.get_commercial_breaks(self.current_movie["id"])
        
        if break_index < len(breaks):
            break_id = breaks[break_index]["id"]
            break_time = breaks[break_index]["break_time"]
            
            db_helper.delete_commercial_break(break_id)
            self.load_timestamps(self.current_movie["id"], self.current_movie["filename"])
            self.status_var.set(f"Deleted break at {break_time}")
    
    def export_timestamp_file(self, movie_id, filename):
        """Export timestamps to text file (for manual export/archival only)."""
        timestamps = db_helper.get_timestamps(movie_id)
        breaks = db_helper.get_commercial_breaks(movie_id)
        
        if not timestamps:
            return
        
        timestamp_dir = os.path.join(self.base_dir, "Data", "Timestamps")
        os.makedirs(timestamp_dir, exist_ok=True)
        
        base_name = os.path.splitext(filename)[0]
        output_file = os.path.join(timestamp_dir, f"{base_name}.txt")
        
        with open(output_file, 'w', encoding='utf-8') as f:
            # Use labeled format with H:MM:SS.MS (always include hour)
            start = self._normalize_time_format(timestamps[0]['start_time'])
            end = self._normalize_time_format(timestamps[0]['end_time'])
            
            f.write(f"Start: {start}\n")
            f.write(f"End: {end}\n")
            f.write("Timestamps:\n")
            for break_data in breaks:
                break_time = self._normalize_time_format(break_data['break_time'])
                f.write(f"{break_time}\n")
    
    def _normalize_time_format(self, time_str: str) -> str:
        """Normalize time to H:MM:SS.MS format with all fields."""
        try:
            time_str = time_str.strip()
            # Split by decimal to get milliseconds
            main_part, ms_part = time_str.split('.') if '.' in time_str else (time_str, '00')
            
            # Split by colon
            parts = main_part.split(':')
            hour, minute, second = 0, 0, 0
            
            if len(parts) == 3:
                hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
            elif len(parts) == 2:
                minute, second = int(parts[0]), int(parts[1])
            elif len(parts) == 1:
                second = int(parts[0])
            
            return f"{hour}:{minute:02d}:{second:02d}.{int(ms_part):02d}"
        except Exception:
            return "0:00:00.00"
    
    def import_from_file(self):
        """Import timestamps from existing text file."""
        if self.current_movie["id"] is None:
            messagebox.showinfo("No Movie Selected", "Please select a movie first")
            return
        
        if not self.current_movie["filename"]:
            return
        
        timestamp_dir = os.path.join(self.base_dir, "Data", "Timestamps")
        base_name = os.path.splitext(self.current_movie["filename"])[0]
        
        # Check for existing file (case-insensitive)
        found_file = None
        if os.path.exists(timestamp_dir):
            for f in os.listdir(timestamp_dir):
                if f.lower() == f"{base_name.lower()}.txt":
                    found_file = os.path.join(timestamp_dir, f)
                    break
        
        if not found_file:
            messagebox.showinfo("No File Found", f"No timestamp file found for {base_name}")
            return
        
        try:
            with open(found_file, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            # Parse labeled format (Start:, End:, Timestamps:, then break times)
            start_time = None
            end_time = None
            breaks = []
            
            i = 0
            while i < len(lines):
                line = lines[i]
                if line.startswith("Start:"):
                    start_time = line.split(":", 1)[1].strip()
                elif line.startswith("End:"):
                    end_time = line.split(":", 1)[1].strip()
                elif line == "Timestamps:":
                    # All following lines are break times
                    breaks = lines[i+1:]
                    break
                i += 1
            
            # Fallback: if no labels found, assume old simple format (first line=start, last=end, middle=breaks)
            if start_time is None or end_time is None:
                if len(lines) < 2:
                    messagebox.showerror("Invalid File", "Timestamp file must have at least start and end times")
                    return
                start_time = lines[0]
                end_time = lines[-1]
                breaks = lines[1:-1]
            
            # Normalize all times to add missing fields (.00 for MS if missing)
            start_time = self._normalize_time_format(start_time)
            end_time = self._normalize_time_format(end_time)
            breaks = [self._normalize_time_format(b) for b in breaks if b]
            
            # Clear existing
            db_helper.clear_commercial_breaks(self.current_movie["id"])
            db_helper.clear_timestamps(self.current_movie["id"])
            
            # Add start/end
            db_helper.add_timestamp(self.current_movie["id"], start_time, end_time)
            
            # Add breaks
            for break_time in breaks:
                db_helper.add_commercial_break(self.current_movie["id"], break_time)
            
            messagebox.showinfo("Import Complete", f"Imported {len(breaks)} commercial breaks from text file")
            self.load_timestamps(self.current_movie["id"], self.current_movie["filename"])
            self.status_var.set(f"Imported {len(breaks)} breaks from file")
            
        except Exception as e:
            messagebox.showerror("Import Failed", f"Error importing file: {e}")
    
    def save_start_end_times(self):
        """Save manually edited start/end times to database."""
        if self.current_movie["id"] is None:
            messagebox.showinfo("No Movie Selected", "Please select a movie first")
            return
        
        try:
            # Build time strings from structured fields
            start_time = self._get_time_from_fields('start')
            end_time = self._get_time_from_fields('end')
            
            # Normalize to full format before saving
            start_time = self._normalize_time_format(start_time)
            end_time = self._normalize_time_format(end_time)
            
            # Clear existing timestamps and add new ones
            db_helper.clear_timestamps(self.current_movie["id"])
            db_helper.add_timestamp(self.current_movie["id"], start_time, end_time)
            
            self.status_var.set(f"Start/End times saved: {start_time} - {end_time}")
            messagebox.showinfo("Saved", "Start and end times updated successfully")
        except ValueError as e:
            messagebox.showerror("Invalid Input", str(e))
        except Exception as e:
            messagebox.showerror("Save Failed", f"Error saving times: {e}")
    
    def _set_time_fields(self, time_str: str, prefix: str):
        """Parse time string and set hour/min/sec/ms fields."""
        try:
            time_str = time_str.strip()
            
            # Split by decimal to get milliseconds
            main_part, ms_part = time_str.split('.') if '.' in time_str else (time_str, '00')
            
            # Split by colon
            parts = main_part.split(':')
            hour, minute, second, millisecond = 0, 0, 0, int(ms_part)
            
            if len(parts) == 3:
                # Format: H:MM:SS
                hour = int(parts[0])
                minute = int(parts[1])
                second = int(parts[2])
            elif len(parts) == 2:
                # Format: MM:SS (treat as minutes:seconds, not hours:minutes)
                minute = int(parts[0])
                second = int(parts[1])
            elif len(parts) == 1:
                # Just seconds
                second = int(parts[0])
            
            if prefix == 'start':
                self.start_hour.set(str(hour))
                self.start_min.set(f"{minute:02d}")
                self.start_sec.set(f"{second:02d}")
                self.start_ms.set(f"{millisecond:02d}")
            else:
                self.end_hour.set(str(hour))
                self.end_min.set(f"{minute:02d}")
                self.end_sec.set(f"{second:02d}")
                self.end_ms.set(f"{millisecond:02d}")
        except Exception:
            # Default to zeros on parse error
            if prefix == 'start':
                self.start_hour.set("0")
                self.start_min.set("00")
                self.start_sec.set("00")
                self.start_ms.set("00")
            else:
                self.end_hour.set("0")
                self.end_min.set("00")
                self.end_sec.set("00")
                self.end_ms.set("00")
    
    def _get_time_from_fields(self, prefix: str) -> str:
        """Build time string from hour/min/sec/ms fields."""
        if prefix == 'start':
            hour = self.start_hour.get().strip()
            minute = self.start_min.get().strip()
            second = self.start_sec.get().strip()
            ms = self.start_ms.get().strip()
        else:
            hour = self.end_hour.get().strip()
            minute = self.end_min.get().strip()
            second = self.end_sec.get().strip()
            ms = self.end_ms.get().strip()
        
        # Validate numeric input
        try:
            h = int(hour) if hour else 0
            m = int(minute) if minute else 0
            s = int(second) if second else 0
            millisec = int(ms) if ms else 0
            
            if m > 59 or s > 59 or h < 0 or m < 0 or s < 0 or millisec > 99:
                raise ValueError("Minutes and seconds must be 0-59, milliseconds 0-99")
            
            # Always return full H:MM:SS.MS format
            return f"{h}:{m:02d}:{s:02d}.{millisec:02d}"
        except ValueError as e:
            raise ValueError(f"Invalid time input: {e}")
    
    def _time_to_seconds(self, time_str: str) -> float:
        """Convert time string (H:MM:SS.MS or MM:SS.MS) to seconds for sorting."""
        try:
            time_str = time_str.strip()
            # Split by decimal to get milliseconds
            main_part, ms_part = time_str.split('.') if '.' in time_str else (time_str, '0')
            
            # Split by colon
            parts = main_part.split(':')
            hour, minute, second = 0, 0, 0
            
            if len(parts) == 3:
                hour, minute, second = int(parts[0]), int(parts[1]), int(parts[2])
            elif len(parts) == 2:
                minute, second = int(parts[0]), int(parts[1])
            elif len(parts) == 1:
                second = int(parts[0])
            
            total_seconds = hour * 3600 + minute * 60 + second + int(ms_part) / 100.0
            return total_seconds
        except Exception:
            return 0.0
    
    def _show_time_picker_dialog(self, title: str) -> str | None:
        """Show custom time picker dialog with H:MM:SS.MS fields."""
        dialog = tk.Toplevel(self.root)
        dialog.title(title)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center the dialog
        dialog.update_idletasks()
        dialog_width = 450
        dialog_height = 170
        parent_x = self.root.winfo_rootx()
        parent_y = self.root.winfo_rooty()
        parent_width = self.root.winfo_width()
        parent_height = self.root.winfo_height()
        x = parent_x + (parent_width - dialog_width) // 2
        y = parent_y + (parent_height - dialog_height) // 2
        dialog.geometry(f"{dialog_width}x{dialog_height}+{x}+{y}")
        
        result = [None]  # type: list[str | None]
        
        # Instructions
        ttk.Label(dialog, text="Enter break time:", font=('TkDefaultFont', 10, 'bold')).pack(pady=(15, 5))
        ttk.Label(dialog, text="Format: Hour : Min : Sec . MS  (Example: 0:03:18.00)", 
                  font=('TkDefaultFont', 8), foreground="gray").pack(pady=(0, 10))
        
        # Time input frame
        input_frame = ttk.Frame(dialog)
        input_frame.pack(pady=10)
        
        ttk.Label(input_frame, text="Hour:").grid(row=0, column=0, padx=5)
        hour_var = tk.StringVar(value="0")
        ttk.Entry(input_frame, textvariable=hour_var, width=5).grid(row=0, column=1, padx=5)
        
        ttk.Label(input_frame, text="Min:").grid(row=0, column=2, padx=5)
        min_var = tk.StringVar(value="00")
        ttk.Entry(input_frame, textvariable=min_var, width=5).grid(row=0, column=3, padx=5)
        
        ttk.Label(input_frame, text="Sec:").grid(row=0, column=4, padx=5)
        sec_var = tk.StringVar(value="00")
        ttk.Entry(input_frame, textvariable=sec_var, width=5).grid(row=0, column=5, padx=5)
        
        ttk.Label(input_frame, text="MS:").grid(row=0, column=6, padx=5)
        ms_var = tk.StringVar(value="00")
        ttk.Entry(input_frame, textvariable=ms_var, width=5).grid(row=0, column=7, padx=5)
        
        # Buttons
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=15)
        
        def on_ok():
            try:
                h = int(hour_var.get() or 0)
                m = int(min_var.get() or 0)
                s = int(sec_var.get() or 0)
                millisec = int(ms_var.get() or 0)
                
                if m > 59 or s > 59 or h < 0 or m < 0 or s < 0 or millisec > 99:
                    messagebox.showerror("Invalid Input", "Minutes and seconds must be 0-59, MS 0-99", parent=dialog)
                    return
                
                # Always return full H:MM:SS.MS format
                result[0] = f"{h}:{m:02d}:{s:02d}.{millisec:02d}"
                dialog.destroy()
            except ValueError:
                messagebox.showerror("Invalid Input", "Please enter valid numbers", parent=dialog)
        
        def on_cancel():
            dialog.destroy()
        
        ttk.Button(btn_frame, text="OK", command=on_ok).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancel", command=on_cancel).pack(side="left", padx=5)
        
        # Center dialog
        dialog.update_idletasks()
        x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
        y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
        dialog.geometry(f"+{x}+{y}")
        
        dialog.wait_window()
        return result[0]
    
    def reset_movie_data(self):
        """Clear all timestamps and breaks for the current movie."""
        if self.current_movie["id"] is None:
            messagebox.showinfo("No Movie Selected", "Please select a movie first")
            return
        
        # Confirm reset
        confirm = messagebox.askyesno(
            "Confirm Reset",
            f"Clear all timestamps and commercial breaks for:\n{self.current_movie['filename']}\n\nThis cannot be undone.",
            icon='warning'
        )
        
        if not confirm:
            return
        
        try:
            # Clear database entries
            db_helper.clear_commercial_breaks(self.current_movie["id"])
            db_helper.clear_timestamps(self.current_movie["id"])
            
            # Reload to show cleared data
            self.load_timestamps(self.current_movie["id"], self.current_movie["filename"])
            self.status_var.set("Movie data reset - duration will be detected on next selection")
            
            messagebox.showinfo("Reset Complete", "All timestamps and breaks have been cleared")
        except Exception as e:
            messagebox.showerror("Reset Failed", f"Error clearing data: {e}")
    
    # ========== Now Playing Queue Tab ==========
    def create_now_playing_tab(self):
        """Create the Now Playing queue management tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Now Playing")
        
        # Main container
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # Left: Available Movies
        left_frame = ttk.LabelFrame(main_frame, text="Available Feature Movies", padding=10)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        
        # Right: Now Playing Queue
        right_frame = ttk.LabelFrame(main_frame, text="Now Playing Queue", padding=10)
        right_frame.grid(row=0, column=1, sticky="nsew", padx=(5, 0))
        
        main_frame.grid_rowconfigure(0, weight=1)
        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_columnconfigure(1, weight=1)
        
        # === Available Movies Section ===
        movies_list_frame = ttk.Frame(left_frame)
        movies_list_frame.pack(fill="both", expand=True)
        
        self.available_movies_listbox = tk.Listbox(movies_list_frame,
                                                    bg='#2d2d2d', fg='#e0e0e0',
                                                    selectbackground='#404040', selectforeground='#e0e0e0',
                                                    activestyle='none',
                                                    borderwidth=0, highlightthickness=0)
        self.available_movies_listbox.pack(side="left", fill="both", expand=True)
        
        avail_scroll = ttk.Scrollbar(movies_list_frame, orient="vertical", command=self.available_movies_listbox.yview)
        avail_scroll.pack(side="right", fill="y")
        self.available_movies_listbox.configure(yscrollcommand=avail_scroll.set)
        
        avail_btn_frame = tk.Frame(left_frame, bg='#414141')
        avail_btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(avail_btn_frame, text="Add to Queue →", command=self.add_to_now_playing).pack(side="left")
        
        # === Now Playing Queue Section ===
        queue_list_frame = ttk.Frame(right_frame)
        queue_list_frame.pack(fill="both", expand=True)
        
        self.now_playing_listbox = tk.Listbox(queue_list_frame,
                                               bg='#2d2d2d', fg='#e0e0e0',
                                               selectbackground='#404040', selectforeground='#e0e0e0',
                                               activestyle='none',
                                               borderwidth=0, highlightthickness=0)
        self.now_playing_listbox.pack(side="left", fill="both", expand=True)
        
        queue_scroll = ttk.Scrollbar(queue_list_frame, orient="vertical", command=self.now_playing_listbox.yview)
        queue_scroll.pack(side="right", fill="y")
        self.now_playing_listbox.configure(yscrollcommand=queue_scroll.set)
        
        queue_btn_frame = tk.Frame(right_frame, bg='#414141')
        queue_btn_frame.pack(fill="x", pady=(10, 0))
        ttk.Button(queue_btn_frame, text="Remove", command=self.remove_from_now_playing).pack(side="left", padx=(0, 5))
        ttk.Button(queue_btn_frame, text="Clear Queue", command=self.clear_now_playing_queue).pack(side="left", padx=(0, 5))
        ttk.Button(queue_btn_frame, text="Move Up", command=lambda: self.move_now_playing(-1)).pack(side="right")
        ttk.Button(queue_btn_frame, text="Move Down", command=lambda: self.move_now_playing(1)).pack(side="right", padx=(0, 5))
        
        # Instructions
        info_text = ("Add feature movies to the queue in the order you want them to play. "
                    "The Feature Player will play these movies with commercial breaks.")
        ttk.Label(tab, text=info_text, font=('TkDefaultFont', 9, 'italic'), wraplength=800).pack(pady=(10, 0))
        
        # Initial load
        self.refresh_now_playing_lists()
    
    def refresh_now_playing_lists(self):
        """Refresh both available movies and queue lists."""
        # Clear lists
        self.available_movies_listbox.delete(0, tk.END)
        self.now_playing_listbox.delete(0, tk.END)
        
        # Get queue (movies already in queue)
        queue = db_helper.get_now_playing_queue()
        queue_movie_ids = {item['movie_id'] for item in queue}
        
        # Load queue
        for i, item in enumerate(queue, 1):
            display = f"{i}. {item['title'] or item['filename']}"
            self.now_playing_listbox.insert(tk.END, display)
        
        # Load available movies (not in queue)
        all_movies = db_helper.get_all_feature_movies()
        for movie in sorted(all_movies, key=lambda m: m['title'] or m['filename']):
            if movie['id'] not in queue_movie_ids:
                display = movie['title'] or movie['filename']
                self.available_movies_listbox.insert(tk.END, display)
                # Store movie data for retrieval
                if not hasattr(self, '_available_movies_data'):
                    self._available_movies_data = []
                else:
                    # Find and update or append
                    pass
        
        # Store available movies for easy lookup
        self._available_movies_data = [
            movie for movie in all_movies
            if movie['id'] not in queue_movie_ids
        ]
        self._available_movies_data.sort(key=lambda m: m['title'] or m['filename'])
        
        # Store queue data for easy lookup
        self._queue_data = queue
    
    def add_to_now_playing(self):
        """Add selected movie to now playing queue."""
        selection = self.available_movies_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a movie to add to the queue.")
            return
        
        index = selection[0]
        if not hasattr(self, '_available_movies_data') or index >= len(self._available_movies_data):
            return
        
        movie = self._available_movies_data[index]
        
        try:
            db_helper.add_to_now_playing_queue(movie['id'])
            self.refresh_now_playing_lists()
            self.status_var.set(f"Added to queue: {movie['title'] or movie['filename']}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to add to queue:\n{e}")
    
    def remove_from_now_playing(self):
        """Remove selected movie from now playing queue."""
        selection = self.now_playing_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a movie to remove from the queue.")
            return
        
        index = selection[0]
        if not hasattr(self, '_queue_data') or index >= len(self._queue_data):
            return
        
        queue_item = self._queue_data[index]
        
        try:
            db_helper.remove_from_now_playing_queue(queue_item['id'])
            self.refresh_now_playing_lists()
            self.status_var.set(f"Removed from queue: {queue_item['title'] or queue_item['filename']}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to remove from queue:\n{e}")
    
    def clear_now_playing_queue(self):
        """Clear all movies from the now playing queue."""
        if not messagebox.askyesno("Confirm Clear", "Clear the entire Now Playing queue?"):
            return
        
        try:
            db_helper.clear_now_playing_queue()
            self.refresh_now_playing_lists()
            self.status_var.set("Now Playing queue cleared")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to clear queue:\n{e}")
    
    def move_now_playing(self, direction):
        """Move selected movie up (-1) or down (1) in the queue."""
        selection = self.now_playing_listbox.curselection()
        if not selection:
            messagebox.showwarning("No Selection", "Please select a movie to move.")
            return
        
        index = selection[0]
        if not hasattr(self, '_queue_data') or index >= len(self._queue_data):
            return
        
        new_index = index + direction
        if new_index < 0 or new_index >= len(self._queue_data):
            return  # Can't move beyond bounds
        
        queue_item = self._queue_data[index]
        current_position = queue_item['position']
        new_position = current_position + direction  # Move by direction in 1-based positions
        
        try:
            db_helper.move_in_now_playing_queue(queue_item['id'], new_position)
            self.refresh_now_playing_lists()
            
            # Restore selection at new position
            self.now_playing_listbox.selection_clear(0, tk.END)
            self.now_playing_listbox.selection_set(new_index)
            self.now_playing_listbox.see(new_index)
            self.now_playing_listbox.focus_set()
            
            self.status_var.set(f"Moved: {queue_item['title'] or queue_item['filename']}")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to move in queue:\n{e}")
            print(f"Debug: Error moving queue item {queue_item['id']} from {current_position} to {new_position}: {e}")
    
    # ========== Import/Export Methods ==========
    
    def export_playlists(self):
        """Export selected playlists to JSON file."""
        playlists = db_helper.list_playlists()
        if not playlists:
            messagebox.showinfo("No Playlists", "No playlists available to export.")
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Export Playlists")
        dialog.transient(self.root)
        dialog.grab_set()
        
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
        
        ttk.Label(dialog, text="Select playlists to export:", font=('TkDefaultFont', 10, 'bold')).pack(pady=10)
        
        # Listbox with multiple selection
        frame = ttk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        listbox = tk.Listbox(frame, selectmode="multiple",
                            bg='#2d2d2d', fg='#e0e0e0',
                            selectbackground='#404040', selectforeground='#e0e0e0')
        listbox.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        scroll.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scroll.set)
        
        for playlist in playlists:
            listbox.insert(tk.END, playlist['name'])
        
        def select_all():
            listbox.selection_set(0, tk.END)
        
        def on_export():
            selected = [playlists[i]['name'] for i in listbox.curselection()]
            if not selected:
                messagebox.showwarning("No Selection", "Please select at least one playlist.", parent=dialog)
                return
            
            filepath = filedialog.asksaveasfilename(
                parent=dialog,
                title="Export Playlists",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not filepath:
                return
            
            try:
                export_data = {"type": "playlists", "data": []}
                for name in selected:
                    videos = db_helper.get_playlist_videos(name)
                    playlist_info = db_helper.get_playlist_by_name(name)
                    export_data["data"].append({
                        "name": name,
                        "description": playlist_info.get('description', '') if playlist_info else '',
                        "videos": [v['filename'] for v in videos]
                    })
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Export Complete", f"Exported {len(selected)} playlist(s) to:\n{filepath}", parent=dialog)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Export Failed", f"Error exporting playlists:\n{e}", parent=dialog)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text="Select All", command=select_all).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Export", command=on_export).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left")
    
    def import_playlists(self):
        """Import playlists from JSON or text file."""
        filepath = filedialog.askopenfilename(
            title="Import Playlists",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            imported_count = 0
            
            if filepath.lower().endswith('.json'):
                # Import from JSON
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data.get('type') == 'playlists' and 'data' in data:
                    for playlist in data['data']:
                        name = playlist['name']
                        description = playlist.get('description', '')
                        videos = playlist.get('videos', [])
                        
                        # Create or update playlist
                        existing = db_helper.get_playlist_by_name(name)
                        if not existing:
                            db_helper.create_playlist(name, description)
                        else:
                            db_helper.clear_playlist(name)
                        
                        # Add videos
                        for position, filename in enumerate(videos, 1):
                            video = db_helper.get_video_by_filename(filename)
                            if video:
                                db_helper.add_video_to_playlist(name, filename, position)
                        
                        imported_count += 1
            else:
                # Import single playlist from text file (legacy)
                playlist_name = os.path.splitext(os.path.basename(filepath))[0]
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    videos = [line.strip() for line in f if line.strip() and line.strip().lower().endswith('.mp4')]
                
                if videos:
                    existing = db_helper.get_playlist_by_name(playlist_name)
                    if not existing:
                        db_helper.create_playlist(playlist_name, f"Imported from {os.path.basename(filepath)}")
                    else:
                        db_helper.clear_playlist(playlist_name)
                    
                    for position, filename in enumerate(videos, 1):
                        video = db_helper.get_video_by_filename(filename)
                        if video:
                            db_helper.add_video_to_playlist(playlist_name, filename, position)
                    
                    imported_count = 1
            
            self.refresh_playlist_list()
            messagebox.showinfo("Import Complete", f"Imported {imported_count} playlist(s).")
            self.status_var.set(f"Imported {imported_count} playlist(s)")
        except Exception as e:
            messagebox.showerror("Import Failed", f"Error importing playlists:\n{e}")
    
    def export_timestamps(self):
        """Export timestamps for selected movies to JSON file."""
        movies = db_helper.get_all_feature_movies()
        if not movies:
            messagebox.showinfo("No Movies", "No movies available to export.")
            return
        
        # Filter movies that have timestamps
        movies_with_timestamps = []
        for movie in movies:
            timestamps = db_helper.get_timestamps(movie['id'])
            breaks = db_helper.get_commercial_breaks(movie['id'])
            if timestamps or breaks:
                movies_with_timestamps.append(movie)
        
        if not movies_with_timestamps:
            messagebox.showinfo("No Timestamps", "No movies have timestamps to export.")
            return
        
        # Create selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.title("Export Timestamps")
        dialog.transient(self.root)
        dialog.grab_set()
        
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
        
        ttk.Label(dialog, text="Select movies to export:", font=('TkDefaultFont', 10, 'bold')).pack(pady=10)
        
        frame = ttk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        listbox = tk.Listbox(frame, selectmode="multiple",
                            bg='#2d2d2d', fg='#e0e0e0',
                            selectbackground='#404040', selectforeground='#e0e0e0',
                            activestyle='none')
        listbox.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        scroll.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scroll.set)
        
        for movie in movies_with_timestamps:
            listbox.insert(tk.END, movie['title'])
        
        def select_all():
            listbox.selection_set(0, tk.END)
        
        def on_export():
            selected = [movies_with_timestamps[i] for i in listbox.curselection()]
            if not selected:
                messagebox.showwarning("No Selection", "Please select at least one movie.", parent=dialog)
                return
            
            filepath = filedialog.asksaveasfilename(
                parent=dialog,
                title="Export Timestamps",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not filepath:
                return
            
            try:
                export_data = {"type": "timestamps", "data": []}
                for movie in selected:
                    timestamps = db_helper.get_timestamps(movie['id'])
                    breaks = db_helper.get_commercial_breaks(movie['id'])
                    
                    movie_data = {
                        "filename": movie['filename'],
                        "title": movie['title']
                    }
                    
                    if timestamps:
                        movie_data["start_time"] = timestamps[0]['start_time']
                        movie_data["end_time"] = timestamps[0]['end_time']
                    
                    if breaks:
                        movie_data["breaks"] = [b['break_time'] for b in breaks]
                    
                    export_data["data"].append(movie_data)
                
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Export Complete", f"Exported timestamps for {len(selected)} movie(s) to:\n{filepath}", parent=dialog)
                dialog.destroy()
            except Exception as e:
                messagebox.showerror("Export Failed", f"Error exporting timestamps:\n{e}", parent=dialog)
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=10)
        ttk.Button(btn_frame, text="Select All", command=select_all).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Export", command=on_export).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="left")
    
    def import_timestamps(self):
        """Import timestamps from JSON or text file."""
        filepath = filedialog.askopenfilename(
            title="Import Timestamps",
            filetypes=[("JSON files", "*.json"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            imported_count = 0
            
            if filepath.lower().endswith('.json'):
                # Import from JSON
                with open(filepath, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data.get('type') == 'timestamps' and 'data' in data:
                    for movie_data in data['data']:
                        filename = movie_data.get('filename')
                        if not filename:
                            continue
                        
                        # Find movie by filename
                        movie = db_helper.get_feature_movie_by_filename(filename)
                        if not movie:
                            continue
                        
                        movie_id = movie['id']
                        
                        # Clear existing
                        db_helper.clear_timestamps(movie_id)
                        db_helper.clear_commercial_breaks(movie_id)
                        
                        # Import start/end times
                        start_time = movie_data.get('start_time')
                        end_time = movie_data.get('end_time')
                        if start_time and end_time:
                            start_time = self._normalize_time_format(start_time)
                            end_time = self._normalize_time_format(end_time)
                            db_helper.add_timestamp(movie_id, start_time, end_time)
                        
                        # Import breaks
                        breaks = movie_data.get('breaks', [])
                        for break_time in breaks:
                            break_time = self._normalize_time_format(break_time)
                            db_helper.add_commercial_break(movie_id, break_time)
                        
                        imported_count += 1
            else:
                # Import from text file (legacy)
                movie_title = os.path.splitext(os.path.basename(filepath))[0]
                
                # Try to find movie by title (case-insensitive)
                movies = db_helper.get_all_feature_movies()
                movie = None
                for m in movies:
                    if m['title'].lower() == movie_title.lower():
                        movie = m
                        break
                
                if not movie:
                    messagebox.showwarning("Movie Not Found", f"No movie found matching: {movie_title}")
                    return
                
                with open(filepath, 'r', encoding='utf-8') as f:
                    lines = [line.strip() for line in f if line.strip()]
                
                # Parse labeled format
                start_time = None
                end_time = None
                breaks = []
                
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if line.startswith("Start:"):
                        start_time = line.split(":", 1)[1].strip()
                    elif line.startswith("End:"):
                        end_time = line.split(":", 1)[1].strip()
                    elif line == "Timestamps:":
                        breaks = lines[i+1:]
                        break
                    i += 1
                
                # Fallback to simple format
                if start_time is None or end_time is None:
                    if len(lines) >= 2:
                        start_time = lines[0]
                        end_time = lines[-1]
                        breaks = lines[1:-1]
                
                if start_time and end_time:
                    movie_id = movie['id']
                    
                    # Clear existing
                    db_helper.clear_timestamps(movie_id)
                    db_helper.clear_commercial_breaks(movie_id)
                    
                    # Normalize and add
                    start_time = self._normalize_time_format(start_time)
                    end_time = self._normalize_time_format(end_time)
                    db_helper.add_timestamp(movie_id, start_time, end_time)
                    
                    for break_time in breaks:
                        break_time = self._normalize_time_format(break_time)
                        db_helper.add_commercial_break(movie_id, break_time)
                    
                    imported_count = 1
            
            # Reload if current movie was updated
            if imported_count > 0 and self.current_movie["id"]:
                self.load_timestamps(self.current_movie["id"], self.current_movie["filename"])
            
            messagebox.showinfo("Import Complete", f"Imported timestamps for {imported_count} movie(s).")
            self.status_var.set(f"Imported {imported_count} timestamp(s)")
        except Exception as e:
            messagebox.showerror("Import Failed", f"Error importing timestamps:\n{e}")
    
    def export_tags(self):
        """Export tags to JSON file."""
        all_tags = db_helper.get_all_tags()
        if not all_tags:
            messagebox.showinfo("No Tags", "No tags available to export.")
            return
        
        # Show selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.title("Export Tags")
        dialog.geometry("400x500")
        
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
        
        ttk.Label(dialog, text="Select tags to export:", font=('TkDefaultFont', 10, 'bold')).pack(pady=10)
        
        # Listbox with multiple selection
        frame = ttk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        listbox = tk.Listbox(frame, selectmode="multiple",
                            bg='#2d2d2d', fg='#e0e0e0',
                            selectbackground='#404040', selectforeground='#e0e0e0',
                            activestyle='none')
        listbox.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        scroll.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scroll.set)
        
        for tag in sorted(all_tags):
            listbox.insert(tk.END, tag)
        
        # Select all by default
        listbox.select_set(0, tk.END)
        
        def on_export():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select at least one tag to export.")
                return
            
            selected_tags = [listbox.get(i) for i in selection]
            dialog.destroy()
            
            filepath = filedialog.asksaveasfilename(
                title="Export Tags",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not filepath:
                return
            
            try:
                export_data = {"type": "tags", "data": selected_tags}
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Export Complete", f"Exported {len(selected_tags)} tag(s) to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Error exporting tags:\n{e}")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="Select All", command=lambda: listbox.select_set(0, tk.END)).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Clear All", command=lambda: listbox.selection_clear(0, tk.END)).pack(side="left")
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="Export", command=on_export).pack(side="right")
        
        dialog.grab_set()
    
    def import_tags(self):
        """Import tags from JSON file."""
        filepath = filedialog.askopenfilename(
            title="Import Tags",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('type') != 'tags' or 'data' not in data:
                messagebox.showerror("Invalid Format", "File does not contain valid tag data.")
                return
            
            imported_count = 0
            for tag in data['data']:
                if tag and tag.strip():
                    try:
                        db_helper.add_tag(tag.strip())
                        imported_count += 1
                    except:
                        pass  # Tag already exists
            
            self.refresh_tags_list()
            messagebox.showinfo("Import Complete", f"Imported {imported_count} tag(s).")
            self.status_var.set(f"Imported {imported_count} tag(s)")
        except Exception as e:
            messagebox.showerror("Import Failed", f"Error importing tags:\n{e}")
    
    def export_genres(self):
        """Export genres to JSON file."""
        all_genres = db_helper.get_all_genres()
        if not all_genres:
            messagebox.showinfo("No Genres", "No genres available to export.")
            return
        
        # Show selection dialog
        dialog = tk.Toplevel(self.root)
        dialog.transient(self.root)
        dialog.title("Export Genres")
        dialog.geometry("400x500")
        
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
        
        ttk.Label(dialog, text="Select genres to export:", font=('TkDefaultFont', 10, 'bold')).pack(pady=10)
        
        # Listbox with multiple selection
        frame = ttk.Frame(dialog)
        frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        
        listbox = tk.Listbox(frame, selectmode="multiple",
                            bg='#2d2d2d', fg='#e0e0e0',
                            selectbackground='#404040', selectforeground='#e0e0e0',
                            activestyle='none')
        listbox.pack(side="left", fill="both", expand=True)
        
        scroll = ttk.Scrollbar(frame, orient="vertical", command=listbox.yview)
        scroll.pack(side="right", fill="y")
        listbox.configure(yscrollcommand=scroll.set)
        
        for genre in sorted(all_genres):
            listbox.insert(tk.END, genre)
        
        # Select all by default
        listbox.select_set(0, tk.END)
        
        def on_export():
            selection = listbox.curselection()
            if not selection:
                messagebox.showwarning("No Selection", "Please select at least one genre to export.")
                return
            
            selected_genres = [listbox.get(i) for i in selection]
            dialog.destroy()
            
            filepath = filedialog.asksaveasfilename(
                title="Export Genres",
                defaultextension=".json",
                filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
            )
            
            if not filepath:
                return
            
            try:
                export_data = {"type": "genres", "data": selected_genres}
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2)
                
                messagebox.showinfo("Export Complete", f"Exported {len(selected_genres)} genre(s) to:\n{filepath}")
            except Exception as e:
                messagebox.showerror("Export Failed", f"Error exporting genres:\n{e}")
        
        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(fill="x", padx=10, pady=(0, 10))
        ttk.Button(btn_frame, text="Select All", command=lambda: listbox.select_set(0, tk.END)).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="Clear All", command=lambda: listbox.selection_clear(0, tk.END)).pack(side="left")
        ttk.Button(btn_frame, text="Cancel", command=dialog.destroy).pack(side="right", padx=(5, 0))
        ttk.Button(btn_frame, text="Export", command=on_export).pack(side="right")
        
        dialog.grab_set()
    
    def import_genres(self):
        """Import genres from JSON file."""
        filepath = filedialog.askopenfilename(
            title="Import Genres",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not filepath:
            return
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if data.get('type') != 'genres' or 'data' not in data:
                messagebox.showerror("Invalid Format", "File does not contain valid genre data.")
                return
            
            imported_count = 0
            for genre in data['data']:
                if genre and genre.strip():
                    try:
                        db_helper.add_genre(genre.strip())
                        imported_count += 1
                    except:
                        pass  # Genre already exists
            
            self.refresh_genres_list()
            messagebox.showinfo("Import Complete", f"Imported {imported_count} genre(s).")
            self.status_var.set(f"Imported {imported_count} genre(s)")
        except Exception as e:
            messagebox.showerror("Import Failed", f"Error importing genres:\n{e}")
    
    # ========== Settings Tab ==========
    def create_settings_tab(self):
        """Create the settings management tab."""
        tab = ttk.Frame(self.notebook)
        self.notebook.add(tab, text="Settings")
        
        # Main container
        main_frame = ttk.Frame(tab)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title_label = ttk.Label(main_frame, text="Application Settings", font=("TkDefaultFont", 14, "bold"))
        title_label.pack(pady=(0, 20))
        
        # Use "All Videos" as default playlist
        default_playlist = "All Videos"
        
        # Settings descriptions organized by application
        self.media_player_settings = {
            "active_playlist": {
                "label": "Active Playlist",
                "description": "Current playlist used by Media Player",
                "type": "playlist",
                "default": default_playlist
            },
            "media_player_shuffle": {
                "label": "Shuffle Mode",
                "description": "Enable or disable shuffle playback in Media Player",
                "type": "boolean",
                "default": "OFF"
            }
        }
        
        self.feature_player_settings = {
            "feature_playlist": {
                "label": "Feature Playlist",
                "description": "Playlist used for commercials in Feature Player",
                "type": "playlist",
                "default": default_playlist
            },
            "ads_per_break": {
                "label": "Ads Per Break",
                "description": "Number of commercials to play during each break",
                "type": "integer",
                "default": "3"
            },
            "feature_player_shuffle": {
                "label": "Shuffle Mode",
                "description": "Enable or disable shuffle playback in Feature Player",
                "type": "boolean",
                "default": "OFF"
            }
        }
        
        # Settings container
        container_frame = ttk.LabelFrame(main_frame, text="Settings Configuration", padding=15)
        container_frame.pack(fill="both", expand=True)
        
        # Create storage for settings widgets
        self.settings_widgets = {}
        self.settings_comboboxes = {}  # Store combobox widgets for updating values
        
        # Media Player Settings Section
        media_player_frame = ttk.LabelFrame(container_frame, text="Media Player Settings", padding=15)
        media_player_frame.pack(fill="x", pady=(0, 15))
        
        self._create_settings_section(media_player_frame, self.media_player_settings)
        
        # Feature Player Settings Section
        feature_player_frame = ttk.LabelFrame(container_frame, text="Feature Player Settings", padding=15)
        feature_player_frame.pack(fill="x", pady=0)
        
        self._create_settings_section(feature_player_frame, self.feature_player_settings)
        
        # Separator
        ttk.Separator(main_frame, orient="horizontal").pack(fill="x", pady=20)
        
        # Buttons frame
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill="x")
        
        ttk.Button(btn_frame, text="Refresh from Database", command=self.refresh_settings).pack(side="left")
        
        # Info section
        info_frame = ttk.LabelFrame(main_frame, text="Information", padding=10)
        info_frame.pack(fill="x", pady=(20, 0))
        
        info_text = (
            "These settings control the behavior of the Media Player and Feature Player.\n"
            "✓ Changes are saved automatically when you make them.\n"
            "  Use 'Refresh from Database' to reload settings if needed."
        )
        ttk.Label(info_frame, text=info_text, font=("TkDefaultFont", 9), justify="left").pack(anchor="w")
    
    def _create_settings_section(self, parent_frame, settings_dict):
        """Helper method to create settings entries within a section."""
        for key, info in settings_dict.items():
            # Get current value from database
            current_value = db_helper.get_setting(key, info["default"])
            
            # Create row frame
            row_frame = ttk.Frame(parent_frame)
            row_frame.pack(fill="x", pady=8)
            
            # Label section
            label_frame = ttk.Frame(row_frame)
            label_frame.pack(side="left", fill="x", expand=True)
            
            tk.Label(label_frame, text=info["label"], font=("TkDefaultFont", 10, "bold"), bg='#222222', fg='#e0e0e0').pack(anchor="w")
            tk.Label(label_frame, text=info["description"], font=("TkDefaultFont", 9), bg='#222222', fg='#888888').pack(anchor="w")
            
            # Input section
            input_frame = ttk.Frame(row_frame)
            input_frame.pack(side="right", padx=(20, 0))
            
            if info["type"] == "playlist":
                # Dropdown for playlist selection
                playlists = db_helper.list_playlists()
                playlist_names = [p['name'] for p in playlists]
                
                var = tk.StringVar(value=current_value)
                dropdown = ttk.Combobox(input_frame, textvariable=var, values=playlist_names, state="readonly", width=30)
                dropdown.pack(side="left")
                dropdown.bind("<<ComboboxSelected>>", lambda e, k=key: self.auto_save_setting(k))
                self.settings_widgets[key] = var
                self.settings_comboboxes[key] = dropdown  # Store widget for updating values list
                
            elif info["type"] == "integer":
                # Spinbox for integer values
                var = tk.StringVar(value=current_value)
                spinbox = ttk.Spinbox(input_frame, from_=1, to=10, textvariable=var, width=10)
                spinbox.pack(side="left")
                var.trace_add("write", lambda *args, k=key: self.auto_save_setting(k))
                self.settings_widgets[key] = var
                
            elif info["type"] == "boolean":
                # Dropdown for ON/OFF
                var = tk.StringVar(value=current_value)
                dropdown = ttk.Combobox(input_frame, textvariable=var, values=["ON", "OFF"], state="readonly", width=10)
                dropdown.pack(side="left")
                dropdown.bind("<<ComboboxSelected>>", lambda e, k=key: self.auto_save_setting(k))
                self.settings_widgets[key] = var
            
            else:
                # Text entry for other types
                var = tk.StringVar(value=current_value)
                entry = ttk.Entry(input_frame, textvariable=var, width=30)
                entry.pack(side="left")
                var.trace_add("write", lambda *args, k=key: self.auto_save_setting(k))
                self.settings_widgets[key] = var
    
    def auto_save_setting(self, key: str):
        """Automatically save a setting when it changes."""
        try:
            # Combine all settings dictionaries
            all_settings = {**self.media_player_settings, **self.feature_player_settings}
            
            if key not in self.settings_widgets or key not in all_settings:
                return
            
            value = self.settings_widgets[key].get().strip()
            description = all_settings[key]["description"]
            db_helper.set_setting(key, value, description)
            
            self.status_var.set(f"Saved: {all_settings[key]['label']} = {value}")
        except Exception as e:
            self.status_var.set(f"Error saving setting: {e}")
    
    def refresh_settings(self):
        """Refresh settings from database."""
        try:
            # Combine all settings dictionaries
            all_settings = {**self.media_player_settings, **self.feature_player_settings}
            
            for key, info in all_settings.items():
                current_value = db_helper.get_setting(key, info["default"])
                self.settings_widgets[key].set(current_value)
            
            self.status_var.set("Settings refreshed from database")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh settings:\n{e}")
    
    def run(self):
        """Start the application."""
        self.root.mainloop()


if __name__ == "__main__":
    app = RetroViewerManager()
    app.run()
