"""
SoundCloud Downloader GUI
Wraps scdl CLI with a modern tkinter interface
Requirements: pip install scdl
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import subprocess
import threading
import os
import sys
import shutil
from pathlib import Path

try:
    from scdl.scdl import SoundCloud
except ImportError:
    SoundCloud = None

# ─── Color Palette ──────────────────────────────────────────────────────────
DARK = {
    "bg":         "#0e0e10",
    "surface":    "#18181b",
    "surface2":   "#1f1f23",
    "border":     "#2e2e34",
    "divider":    "#26262c",
    "text":       "#e4e4e7",
    "muted":      "#71717a",
    "faint":      "#3f3f46",
    "primary":    "#f26722",   # SoundCloud orange
    "primary_h":  "#ff8040",
    "primary_bg": "#2a1a0e",
    "success":    "#4ade80",
    "success_bg": "#052e16",
    "error":      "#f87171",
    "error_bg":   "#2d0a0a",
    "warning":    "#fbbf24",
}

FONTS = {
    "display": ("Segoe UI", 20, "bold"),
    "heading": ("Segoe UI", 13, "bold"),
    "body":    ("Segoe UI", 10),
    "small":   ("Segoe UI", 9),
    "mono":    ("Consolas", 9),
    "label":   ("Segoe UI", 9, "bold"),
}

# ─── Main App ────────────────────────────────────────────────────────────────


class SoundCloudDownloaderApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("SoundCloud Downloader")
        self.geometry("780x720")
        self.minsize(700, 680)
        self.configure(bg=DARK["bg"])
        self.resizable(True, True)

        self._download_path = str(Path.home() / "Music" / "SoundCloud")
        self._processes = []
        self._downloading = False
        self._downloads_running = 0
        self._downloads_lock = threading.Lock()
        self._download_semaphore = None
        self._stop_requested = False
        self._playlist_tracks = []
        self._playlist_track_vars = []

        self._build_ui()
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self._check_scdl()

    # ── Check dependency ─────────────────────────────────────────────────────
    def _check_scdl(self):
        if shutil.which("scdl") is None:
            self._log("⚠  scdl not found in PATH.", "warning")
            self._log("   Install it with:  pip install scdl", "muted")
            self._log("   Also ensure ffmpeg is installed.\n", "muted")
        else:
            result = subprocess.run(
                ["scdl", "--version"], capture_output=True, text=True)
            ver = result.stdout.strip() or result.stderr.strip()
            self._log(f"✓ scdl ready — {ver}\n", "success")

    # ── UI construction ───────────────────────────────────────────────────────
    def _build_ui(self):
        self._style_ttk()

        # ── Header
        header = tk.Frame(self, bg=DARK["surface"], pady=0)
        header.pack(fill="x")

        logo_row = tk.Frame(header, bg=DARK["surface"], padx=24, pady=16)
        logo_row.pack(fill="x")

        logo_dot = tk.Canvas(logo_row, width=28, height=28, bg=DARK["surface"],
                             highlightthickness=0)
        logo_dot.create_oval(2, 2, 26, 26, fill=DARK["primary"], outline="")
        logo_dot.create_oval(9, 9, 19, 19, fill=DARK["surface"], outline="")
        logo_dot.pack(side="left", padx=(0, 10))

        tk.Label(logo_row, text="SoundCloud", font=FONTS["display"],
                 fg=DARK["text"], bg=DARK["surface"]).pack(side="left")
        tk.Label(logo_row, text="Downloader", font=("Segoe UI", 20),
                 fg=DARK["muted"], bg=DARK["surface"]).pack(side="left", padx=(6, 0))

        tk.Frame(self, bg=DARK["border"], height=1).pack(fill="x")

        # ── Content area with scroll support
        content_wrapper = tk.Frame(self, bg=DARK["bg"])
        content_wrapper.pack(fill="both", expand=True)

        self._content_canvas = tk.Canvas(
            content_wrapper, bg=DARK["bg"], bd=0, highlightthickness=0)
        self._content_canvas.pack(side="left", fill="both", expand=True)

        content_scrollbar = ttk.Scrollbar(
            content_wrapper, orient="vertical", command=self._content_canvas.yview)
        content_scrollbar.pack(side="right", fill="y")

        self._content_canvas.configure(yscrollcommand=content_scrollbar.set)

        content = tk.Frame(self._content_canvas,
                           bg=DARK["bg"], padx=24, pady=20)
        self._content_window = self._content_canvas.create_window(
            (0, 0), window=content, anchor="nw")

        content.bind(
            "<Configure>",
            lambda e: self._content_canvas.configure(
                scrollregion=self._content_canvas.bbox("all")))
        self._content_canvas.bind(
            "<Configure>",
            lambda e: self._content_canvas.itemconfig(
                self._content_window, width=e.width))

        self._content_canvas.bind("<Enter>",
                                  lambda e: self._content_canvas.bind_all(
                                      "<MouseWheel>", self._on_mousewheel))
        self._content_canvas.bind("<Leave>",
                                  lambda e: self._content_canvas.unbind_all(
                                      "<MouseWheel>"))

        self._build_url_section(content)
        self._build_playlist_section(content)
        self._build_options_section(content)
        self._build_path_section(content)
        self._build_action_row(content)
        self._build_log_section(content)

    def _style_ttk(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=DARK["surface2"],
                        background=DARK["surface2"],
                        foreground=DARK["text"],
                        selectbackground=DARK["primary"],
                        selectforeground=DARK["text"],
                        bordercolor=DARK["border"],
                        arrowcolor=DARK["muted"],
                        relief="flat")
        style.configure("TCheckbutton",
                        background=DARK["bg"],
                        foreground=DARK["text"],
                        selectcolor=DARK["primary"],
                        relief="flat")
        style.map("TCheckbutton",
                  background=[("active", DARK["bg"])],
                  foreground=[("active", DARK["text"])])

    # ── URL ──────────────────────────────────────────────────────────────────
    def _build_url_section(self, parent):
        self._label(parent, "Track / Playlist / User URLs")
        url_frame = tk.Frame(parent, bg=DARK["surface2"], highlightbackground=DARK["border"],
                             highlightthickness=1)
        url_frame.pack(fill="both", pady=(4, 14))

        self._url_text = scrolledtext.ScrolledText(
            url_frame, height=4, font=FONTS["body"], bg=DARK["surface2"],
            fg=DARK["text"], insertbackground=DARK["primary"], relief="flat",
            wrap="word", bd=0, padx=12, pady=10
        )
        self._url_text.pack(fill="both", expand=True)
        self._url_text.bind("<FocusIn>", lambda e: url_frame.config(
            highlightbackground=DARK["primary"]))
        self._url_text.bind("<FocusOut>", lambda e: url_frame.config(
            highlightbackground=DARK["border"]))

        self._label(parent, "Use one URL per line for multiple downloads")

    def _build_playlist_section(self, parent):
        self._label(parent, "Playlist selection")
        playlist_outer = tk.Frame(parent, bg=DARK["surface"], highlightbackground=DARK["border"],
                                  highlightthickness=1)
        playlist_outer.pack(fill="x", pady=(4, 14))

        playlist_row = tk.Frame(
            playlist_outer, bg=DARK["surface"], padx=14, pady=12)
        playlist_row.pack(fill="x")

        self._playlist_option_var = tk.StringVar(value="direct")
        direct_rb = tk.Radiobutton(
            playlist_row, text="Download playlist directly", variable=self._playlist_option_var,
            value="direct", bg=DARK["surface"], fg=DARK["text"], selectcolor=DARK["surface2"],
            activebackground=DARK["surface"], activeforeground=DARK["text"], indicatoron=0,
            width=24, padx=8, pady=6, bd=0, relief="flat", command=self._refresh_playlist_mode
        )
        direct_rb.pack(side="left", padx=(0, 8))

        select_rb = tk.Radiobutton(
            playlist_row, text="Select tracks from playlist", variable=self._playlist_option_var,
            value="select", bg=DARK["surface"], fg=DARK["text"], selectcolor=DARK["surface2"],
            activebackground=DARK["surface"], activeforeground=DARK["text"], indicatoron=0,
            width=24, padx=8, pady=6, bd=0, relief="flat", command=self._refresh_playlist_mode
        )
        select_rb.pack(side="left")

        self._playlist_fetch_btn = self._btn(
            playlist_row, "Load playlist tracks", self._fetch_playlist_tracks,
            width=18, secondary=True)
        self._playlist_fetch_btn.pack(side="right")

        controls_row = tk.Frame(
            playlist_outer, bg=DARK["surface"], padx=14)
        controls_row.pack(fill="x", pady=(0, 6))
        self._select_all_btn = self._btn(controls_row, "Select all", self._select_all_tracks,
                                         width=12, secondary=True)
        self._select_all_btn.pack(side="left", padx=(0, 6))
        self._unselect_all_btn = self._btn(controls_row, "Unselect all", self._unselect_all_tracks,
                                           width=12, secondary=True)
        self._unselect_all_btn.pack(side="left")

        self._playlist_listbox_container = tk.Frame(
            playlist_outer, bg=DARK["surface2"], highlightbackground=DARK["border"],
            highlightthickness=1, height=180)
        self._playlist_listbox_container.pack_propagate(False)
        self._playlist_list_label = tk.Label(
            self._playlist_listbox_container, text="Playlist tracks:",
            font=FONTS["label"], fg=DARK["text"], bg=DARK["surface2"], anchor="w"
        )
        self._playlist_list_label.pack(fill="x", padx=12, pady=(8, 2))

        self._playlist_list_canvas = tk.Canvas(
            self._playlist_listbox_container, bg=DARK["surface2"], bd=0,
            highlightthickness=0, relief="flat")
        self._playlist_list_canvas.pack(side="left", fill="both", expand=True,
                                        padx=(12, 0), pady=(0, 12))

        self._playlist_tracks_frame = tk.Frame(self._playlist_list_canvas,
                                               bg=DARK["surface2"])
        self._playlist_scroll_window = self._playlist_list_canvas.create_window(
            (0, 0), window=self._playlist_tracks_frame, anchor="nw")

        scrollbar = tk.Scrollbar(
            self._playlist_listbox_container, command=self._playlist_list_canvas.yview)
        scrollbar.pack(side="right", fill="y", pady=(0, 12))
        self._playlist_list_canvas.config(yscrollcommand=scrollbar.set)

        self._playlist_tracks_frame.bind(
            "<Configure>",
            lambda e: self._playlist_list_canvas.configure(
                scrollregion=self._playlist_list_canvas.bbox("all")))
        self._playlist_list_canvas.bind(
            "<Configure>",
            lambda e: self._playlist_list_canvas.itemconfig(
                self._playlist_scroll_window, width=e.width))

        self._playlist_listbox_container.pack_forget()

    def _refresh_playlist_mode(self):
        if self._playlist_option_var.get() == "select":
            self._playlist_listbox_container.pack(fill="x", pady=(0, 14))
        else:
            self._playlist_listbox_container.pack_forget()

    def _resolve_playlist_tracks(self, client, track_list):
        ids_to_resolve = [getattr(track, "id", None) for track in track_list
                          if getattr(track, "id", None) and not getattr(track, "title", None)]
        if not ids_to_resolve:
            return track_list

        try:
            resolved = client.get_tracks(ids_to_resolve)
            resolved_by_id = {getattr(track, "id", None): track for track in resolved
                              if getattr(track, "id", None) is not None}
            return [resolved_by_id.get(getattr(track, "id", None), track)
                    for track in track_list]
        except Exception:
            return track_list

    def _select_all_tracks(self):
        for var in getattr(self, "_playlist_track_vars", []):
            var.set(True)

    def _unselect_all_tracks(self):
        for var in getattr(self, "_playlist_track_vars", []):
            var.set(False)

    # ── Options ──────────────────────────────────────────────────────────────
    def _build_options_section(self, parent):
        self._label(parent, "Download Options")

        opts_outer = tk.Frame(parent, bg=DARK["surface"], highlightbackground=DARK["border"],
                              highlightthickness=1)
        opts_outer.pack(fill="x", pady=(4, 14))

        opts = tk.Frame(opts_outer, bg=DARK["surface"], padx=14, pady=12)
        opts.pack(fill="x")

        # Row 1 — mode
        row1 = tk.Frame(opts, bg=DARK["surface"])
        row1.pack(fill="x", pady=(0, 10))

        tk.Label(row1, text="Mode", font=FONTS["label"], fg=DARK["muted"],
                 bg=DARK["surface"], width=10, anchor="w").pack(side="left")

        self._mode_var = tk.StringVar(value="Single track (URL)")
        mode_map = [
            ("Single track (URL)", ""),
            ("All uploads",        "-t"),
            ("All tracks + reposts", "-a"),
            ("All favorites/likes", "-f"),
            ("All playlists",      "-p"),
            ("All reposts",        "-r"),
            ("All commented",      "-C"),
        ]
        self._mode_map = {label: flag for label, flag in mode_map}
        mode_combo = ttk.Combobox(row1, textvariable=self._mode_var,
                                  values=[l for l, _ in mode_map],
                                  state="readonly", width=28, font=FONTS["body"])
        mode_combo.pack(side="left", padx=(0, 20))

        # Max tracks
        tk.Label(row1, text="Max tracks", font=FONTS["label"], fg=DARK["muted"],
                 bg=DARK["surface"]).pack(side="left", padx=(0, 6))
        self._max_tracks_var = tk.StringVar(value="")
        mt_frame = tk.Frame(row1, bg=DARK["border"], highlightbackground=DARK["border"],
                            highlightthickness=1)
        mt_frame.pack(side="left")
        tk.Entry(mt_frame, textvariable=self._max_tracks_var, width=6,
                 font=FONTS["body"], bg=DARK["surface2"], fg=DARK["text"],
                 relief="flat", insertbackground=DARK["primary"]).pack(padx=8, pady=4)

        tk.Label(row1, text="Parallel", font=FONTS["label"], fg=DARK["muted"],
                 bg=DARK["surface"]).pack(side="left", padx=(12, 6))
        self._parallel_var = tk.StringVar(value="3")
        parallel_combo = ttk.Combobox(row1, textvariable=self._parallel_var,
                                      values=["1", "2", "3",
                                              "4", "5", "6", "8"],
                                      state="readonly", width=3, font=FONTS["body"])
        parallel_combo.pack(side="left")

        # Row 2 — checkboxes
        row2 = tk.Frame(opts, bg=DARK["surface"])
        row2.pack(fill="x")

        self._only_mp3 = self._checkbox(row2, "Only MP3")
        self._continue_ = self._checkbox(row2, "Skip existing (-c)")
        self._orig_art = self._checkbox(row2, "Original artwork")
        self._add_ts = self._checkbox(row2, "Add timestamp")
        self._flac = self._checkbox(row2, "FLAC (lossless)")
        self._no_orig = self._checkbox(row2, "No original file")

    # ── Output path ──────────────────────────────────────────────────────────
    def _build_path_section(self, parent):
        self._label(parent, "Save To")
        path_row = tk.Frame(parent, bg=DARK["bg"])
        path_row.pack(fill="x", pady=(4, 14))

        path_frame = tk.Frame(path_row, bg=DARK["surface2"], highlightbackground=DARK["border"],
                              highlightthickness=1)
        path_frame.pack(side="left", fill="x", expand=True)

        self._path_var = tk.StringVar(value=self._download_path)
        tk.Entry(path_frame, textvariable=self._path_var, font=FONTS["body"],
                 bg=DARK["surface2"], fg=DARK["text"], relief="flat",
                 insertbackground=DARK["primary"]).pack(side="left", fill="x",
                                                        expand=True, padx=12, pady=9)

        self._btn(path_row, "Browse", self._browse, width=8, secondary=True).pack(
            side="left", padx=(8, 0))

    # ── Action row ───────────────────────────────────────────────────────────
    def _build_action_row(self, parent):
        row = tk.Frame(parent, bg=DARK["bg"])
        row.pack(fill="x", pady=(0, 14))

        self._dl_btn = self._btn(
            row, "⬇  Download", self._start_download, width=16)
        self._dl_btn.pack(side="left")

        self._stop_btn = self._btn(
            row, "✕  Stop", self._stop_download, width=8, danger=True)
        self._stop_btn.pack(side="left", padx=(10, 0))
        self._stop_btn.config(state="disabled")

        self._clear_btn = self._btn(
            row, "Clear log", self._clear_log, width=8, secondary=True)
        self._clear_btn.pack(side="right")

        self._progress = ttk.Progressbar(row, mode="indeterminate", length=140)
        self._progress.pack(side="right", padx=(0, 14))

    # ── Log ──────────────────────────────────────────────────────────────────
    def _build_log_section(self, parent):
        self._label(parent, "Output")
        log_frame = tk.Frame(parent, bg=DARK["surface2"], highlightbackground=DARK["border"],
                             highlightthickness=1)
        log_frame.pack(fill="both", expand=True, pady=(4, 0))

        self._log_text = scrolledtext.ScrolledText(
            log_frame, font=FONTS["mono"], bg=DARK["surface2"], fg=DARK["text"],
            insertbackground=DARK["primary"], relief="flat", state="disabled",
            wrap="word", padx=12, pady=10
        )
        self._log_text.pack(fill="both", expand=True)
        # tag colors
        self._log_text.tag_config("success", foreground=DARK["success"])
        self._log_text.tag_config("error",   foreground=DARK["error"])
        self._log_text.tag_config("warning", foreground=DARK["warning"])
        self._log_text.tag_config("muted",   foreground=DARK["muted"])
        self._log_text.tag_config("primary", foreground=DARK["primary"])

    # ── Helpers ───────────────────────────────────────────────────────────────
    def _label(self, parent, text):
        tk.Label(parent, text=text.upper(), font=FONTS["label"],
                 fg=DARK["muted"], bg=DARK["bg"]).pack(anchor="w", pady=(0, 2))

    def _on_mousewheel(self, event):
        self._content_canvas.yview_scroll(-int(event.delta / 120), "units")

    def _on_close(self):
        if self._downloading:
            if messagebox.askyesno(
                    "Exit", "Downloads are running. Quit anyway?"):
                self._stop_download()
                self.destroy()
        else:
            self.destroy()

    def _checkbox(self, parent, text):
        var = tk.BooleanVar()
        cb = ttk.Checkbutton(
            parent, text=text, variable=var, style="TCheckbutton")
        cb.pack(side="left", padx=(0, 16))
        return var

    def _btn(self, parent, text, cmd, width=10, secondary=False, danger=False):
        if danger:
            bg, fg, hbg = DARK["error_bg"], DARK["error"], "#3d0a0a"
        elif secondary:
            bg, fg, hbg = DARK["surface2"], DARK["text"], DARK["border"]
        else:
            bg, fg, hbg = DARK["primary"], "#fff", DARK["primary_h"]

        b = tk.Button(parent, text=text, command=cmd, font=FONTS["body"],
                      bg=bg, fg=fg, activebackground=hbg, activeforeground=fg,
                      relief="flat", padx=14, pady=8, cursor="hand2", width=width,
                      bd=0)
        b.bind("<Enter>", lambda e: b.config(bg=hbg))
        b.bind("<Leave>", lambda e: b.config(bg=bg))
        return b

    # ── Actions ───────────────────────────────────────────────────────────────
    def _browse(self):
        path = filedialog.askdirectory(title="Select download folder",
                                       initialdir=self._path_var.get())
        if path:
            self._path_var.set(path)

    def _get_urls(self):
        text = self._url_text.get("1.0", "end").strip()
        return [line.strip() for line in text.splitlines() if line.strip()]

    def _build_command(self, url):
        if not url:
            return None

        cmd = ["scdl", "-l", url]

        # mode flag
        mode_flag = self._mode_map.get(self._mode_var.get(), "")
        if mode_flag:
            cmd.append(mode_flag)

        # max tracks
        mt = self._max_tracks_var.get().strip()
        if mt.isdigit():
            cmd += ["-n", mt]

        # checkboxes
        if self._only_mp3.get():
            cmd.append("--onlymp3")
        if self._continue_.get():
            cmd.append("-c")
        if self._orig_art.get():
            cmd.append("--original-art")
        if self._add_ts.get():
            cmd.append("--addtimestamp")
        if self._flac.get():
            cmd.append("--flac")
        if self._no_orig.get():
            cmd.append("--no-original")

        # path
        path = self._path_var.get().strip()
        if path:
            os.makedirs(path, exist_ok=True)
            cmd += ["--path", path]

        return cmd

    def _fetch_playlist_tracks(self):
        urls = self._get_urls()
        if not urls:
            messagebox.showerror(
                "No URL", "Please enter a SoundCloud playlist URL first.")
            return

        if SoundCloud is None:
            messagebox.showerror(
                "Missing dependency", "Playlist selection requires scdl package support.")
            return

        playlist_url = urls[0]
        self._log(f"▶ Resolving playlist: {playlist_url}", "primary")

        try:
            client = SoundCloud()
            item = client.resolve(playlist_url)
            if not item or getattr(item, "kind", "") != "playlist":
                raise ValueError("URL is not a playlist")

            tracks = getattr(item, "tracks", []) or []
            tracks = self._resolve_playlist_tracks(client, tracks)
            self._playlist_tracks = []
            self._playlist_track_vars = []
            for child in self._playlist_tracks_frame.winfo_children():
                child.destroy()

            for idx, track in enumerate(tracks, start=1):
                title = getattr(track, "title", "Unknown title")
                user = getattr(track, "user", None)
                artist = getattr(user, "username", "") if user else ""
                track_url = getattr(track, "permalink_url",
                                    None) or getattr(track, "uri", "")
                display = f"{idx}. {artist} — {title}" if artist else f"{idx}. {title}"
                self._playlist_tracks.append(track_url)

                track_var = tk.BooleanVar(value=True)
                row = tk.Frame(self._playlist_tracks_frame,
                               bg=DARK["surface2"])
                cb = ttk.Checkbutton(
                    row, text=display, variable=track_var,
                    style="TCheckbutton", onvalue=True, offvalue=False)
                cb.pack(side="left", fill="x", expand=True, padx=12, pady=2)
                row.pack(fill="x")
                self._playlist_track_vars.append(track_var)

            if not self._playlist_tracks:
                messagebox.showinfo(
                    "Playlist empty", "No tracks were found in that playlist.")
                return

            self._playlist_option_var.set("select")
            self._refresh_playlist_mode()
            self._log(
                f"✓ Loaded {len(self._playlist_tracks)} tracks from playlist.", "success")
        except Exception as ex:
            self._log(f"\n✗ Failed to load playlist: {ex}\n", "error")
            messagebox.showerror(
                "Playlist error", f"Could not load playlist: {ex}")

    def _start_download(self):
        if self._downloading:
            return

        commands = []
        if self._playlist_option_var.get() == "select":
            selected = [url for url, var in zip(
                self._playlist_tracks, self._playlist_track_vars) if var.get()]
            if not selected:
                messagebox.showerror(
                    "No tracks selected", "Please select playlist tracks to download.")
                return
            for url in selected:
                cmd = self._build_command(url)
                if cmd:
                    commands.append(cmd)
        else:
            for url in self._get_urls():
                cmd = self._build_command(url)
                if cmd:
                    commands.append(cmd)

        if not commands:
            messagebox.showerror(
                "No URL", "Please enter at least one SoundCloud URL.")
            return

        parallel = 3
        try:
            parallel = max(1, int(self._parallel_var.get()))
        except Exception:
            parallel = 3

        self._download_semaphore = threading.BoundedSemaphore(parallel)
        self._downloads_running = len(commands)
        self._stop_requested = False
        self._processes = []
        self._downloading = True
        self._dl_btn.config(state="disabled")
        self._stop_btn.config(state="normal")
        self._progress.start(12)

        self._log(
            f"▶ Starting {len(commands)} download(s) with {parallel} threads.", "primary")
        for cmd in commands:
            self._log(f"▶ Running: {' '.join(cmd)}", "primary")
            thread = threading.Thread(
                target=self._run_with_slot, args=(cmd,), daemon=True)
            thread.start()

    def _run_with_slot(self, cmd):
        self._download_semaphore.acquire()
        try:
            self._run(cmd)
        finally:
            self._download_semaphore.release()

    def _run(self, cmd):
        process = None
        try:
            process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, bufsize=1
            )
            with self._downloads_lock:
                self._processes.append(process)

            for line in process.stdout:
                line = line.rstrip()
                if not line:
                    continue
                tag = "success" if any(w in line.lower() for w in ["done", "downloaded", "complete", "finish"]) \
                    else "error" if any(w in line.lower() for w in ["error", "fail", "traceback", "exception"]) \
                    else "warning" if "warn" in line.lower() \
                    else None
                self._log(line, tag)
            process.wait()
            rc = process.returncode
            self._log(f"\n{'✓ Download complete!' if rc == 0 else f'✗ Exited with code {rc}'}\n",
                      "success" if rc == 0 else "error")
        except FileNotFoundError:
            self._log(
                "\n✗ scdl not found. Install with: pip install scdl\n", "error")
        except Exception as ex:
            self._log(f"\n✗ Error: {ex}\n", "error")
        finally:
            if process is not None:
                with self._downloads_lock:
                    if process in self._processes:
                        self._processes.remove(process)
                    self._downloads_running = max(
                        0, self._downloads_running - 1)
                    remaining = self._downloads_running
                if remaining == 0:
                    self.after(0, self._on_done)

    def _on_done(self):
        self._downloading = False
        self._progress.stop()
        self._dl_btn.config(state="normal")
        self._stop_btn.config(state="disabled")
        self._processes = []

    def _stop_download(self):
        with self._downloads_lock:
            procs = list(self._processes)
            self._stop_requested = True

        for proc in procs:
            try:
                proc.terminate()
            except Exception:
                pass

        if procs:
            self._log("\n⏹ Download stopped by user.\n", "warning")

    def _clear_log(self):
        self._log_text.config(state="normal")
        self._log_text.delete("1.0", "end")
        self._log_text.config(state="disabled")

    def _log(self, msg, tag=None):
        def _append():
            self._log_text.config(state="normal")
            if tag:
                self._log_text.insert("end", msg + "\n", tag)
            else:
                self._log_text.insert("end", msg + "\n")
            self._log_text.see("end")
            self._log_text.config(state="disabled")
        self.after(0, _append)


# ─── Entry point ─────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = SoundCloudDownloaderApp()
    try:
        app.mainloop()
    except KeyboardInterrupt:
        pass
