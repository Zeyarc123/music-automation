"""
Music Automation Suite — GUI
Drag & drop files, analyze BPM/key/genre, per-platform titles via settings.
"""

import os
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

try:
    from tkinterdnd2 import TkinterDnD, DND_FILES
    HAS_DND = True
except ImportError:
    HAS_DND = False

from analyzer import analyze_file
from metadata import build_platform_titles, build_filename, rename_file, save_batch_metadata
from config import TRACK_TYPES, load_settings, save_settings


# ── Colors ──
BG = "#1e1e2e"
SURFACE = "#313244"
FG = "#cdd6f4"
ACCENT = "#89b4fa"
GREEN = "#a6e3a1"
ORANGE = "#fab387"
RED = "#f38ba8"
DIM = "#6c7086"


class App(TkinterDnD.Tk if HAS_DND else tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Automation Suite")
        self.geometry("950x750")
        self.configure(bg=BG)
        self.minsize(800, 600)

        self.files = []
        self.results = []
        self.batch_output = []
        self.settings = load_settings()

        self._build_styles()
        self._build_ui()

    # ── Styles ────────────────────────────────────────────────────

    def _build_styles(self):
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=BG, foreground=ACCENT,
                        font=("Segoe UI", 16, "bold"))
        style.configure("Dim.TLabel", background=BG, foreground=DIM, font=("Segoe UI", 9))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=6)
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), padding=10)
        style.configure("TCombobox", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background=BG, foreground=FG, font=("Segoe UI", 10))
        style.configure("green.Horizontal.TProgressbar", troughcolor=SURFACE,
                        background=GREEN, thickness=8)

    # ── Main UI ───────────────────────────────────────────────────

    def _build_ui(self):
        # Top bar
        top = ttk.Frame(self)
        top.pack(fill="x", padx=16, pady=(16, 4))
        ttk.Label(top, text="Music Automation Suite", style="Title.TLabel").pack(side="left")
        ttk.Button(top, text="Settings", command=self._open_settings).pack(side="right")

        # ── Drop zone ──
        self.drop_frame = tk.Frame(self, bg=SURFACE, highlightbackground=ACCENT,
                                   highlightthickness=2, cursor="hand2")
        self.drop_frame.pack(fill="x", padx=16, pady=8, ipady=20)

        self.drop_label = tk.Label(
            self.drop_frame, bg=SURFACE, fg=DIM, font=("Segoe UI", 12),
            text="Drag & drop audio files here\nor click to select" if HAS_DND
            else "Click to select audio files or folder"
        )
        self.drop_label.pack(expand=True)
        self.drop_frame.bind("<Button-1>", lambda e: self._select_files())
        self.drop_label.bind("<Button-1>", lambda e: self._select_files())

        if HAS_DND:
            self.drop_frame.drop_target_register(DND_FILES)
            self.drop_frame.dnd_bind('<<Drop>>', self._on_drop)
            self.drop_frame.dnd_bind('<<DragEnter>>', self._on_drag_enter)
            self.drop_frame.dnd_bind('<<DragLeave>>', self._on_drag_leave)

        # ── File list ──
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="x", padx=16)

        self.lbl_file_count = ttk.Label(list_frame, text="No files selected", style="Dim.TLabel")
        self.lbl_file_count.pack(side="left")

        ttk.Button(list_frame, text="Clear", command=self._clear_files).pack(side="right")
        ttk.Button(list_frame, text="Add Folder",
                   command=self._select_folder).pack(side="right", padx=4)

        # ── Options ──
        opts = ttk.Frame(self)
        opts.pack(fill="x", padx=16, pady=8)

        ttk.Label(opts, text="Track type:").pack(side="left")
        self.var_type = tk.StringVar(value=self.settings.get('default_track_type', 'loop'))
        ttk.Combobox(opts, textvariable=self.var_type, values=list(TRACK_TYPES.keys()),
                     state="readonly", width=12).pack(side="left", padx=(4, 16))

        self.var_rename = tk.BooleanVar(value=self.settings.get('rename_files', False))
        ttk.Checkbutton(opts, text="Rename files with BPM/key",
                        variable=self.var_rename).pack(side="left")

        # ── Analyze button + progress ──
        action_frame = ttk.Frame(self)
        action_frame.pack(fill="x", padx=16, pady=(0, 4))

        self.btn_analyze = ttk.Button(action_frame, text="Analyze",
                                      command=self._start_analysis, style="Accent.TButton")
        self.btn_analyze.pack(side="left")

        self.lbl_status = ttk.Label(action_frame, text="", style="Dim.TLabel")
        self.lbl_status.pack(side="left", padx=12)

        self.progress = ttk.Progressbar(self, style="green.Horizontal.TProgressbar",
                                        mode="determinate", maximum=100, value=0)
        self.progress.pack(fill="x", padx=16, pady=(0, 8))

        # ── Results ──
        result_frame = ttk.Frame(self)
        result_frame.pack(fill="both", expand=True, padx=16, pady=(0, 8))

        self.txt = tk.Text(result_frame, bg=SURFACE, fg=FG, font=("Consolas", 10),
                           wrap="word", insertbackground=FG, relief="flat", bd=0,
                           padx=12, pady=12)
        sb = ttk.Scrollbar(result_frame, command=self.txt.yview)
        self.txt.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")
        self.txt.pack(fill="both", expand=True)

        self.txt.tag_configure("h", foreground=ACCENT, font=("Consolas", 11, "bold"))
        self.txt.tag_configure("ok", foreground=GREEN)
        self.txt.tag_configure("warn", foreground=RED)
        self.txt.tag_configure("plat", foreground=ORANGE)
        self.txt.tag_configure("dim", foreground=DIM)
        self.txt.tag_configure("genre", foreground="#cba6f7")

        # ── Bottom ──
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=16, pady=(0, 16))
        ttk.Button(bottom, text="Save JSON", command=self._save_json).pack(side="left", padx=(0, 8))
        ttk.Button(bottom, text="Copy Results", command=self._copy).pack(side="left")

    # ── Drag & drop ───────────────────────────────────────────────

    def _on_drop(self, event):
        self.drop_frame.configure(highlightbackground=ACCENT)
        # tkinterdnd2 gives paths in {braces} if they contain spaces
        raw = event.data
        paths = []
        # Parse the tkdnd format
        i = 0
        while i < len(raw):
            if raw[i] == '{':
                end = raw.index('}', i)
                paths.append(raw[i+1:end])
                i = end + 2
            elif raw[i] == ' ':
                i += 1
            else:
                end = raw.find(' ', i)
                if end == -1:
                    end = len(raw)
                paths.append(raw[i:end])
                i = end + 1

        audio_ext = {'.wav', '.mp3', '.flac', '.ogg', '.aiff', '.aif'}
        new_files = []
        for p in paths:
            if os.path.isfile(p) and os.path.splitext(p)[1].lower() in audio_ext:
                new_files.append(p)
            elif os.path.isdir(p):
                for f in sorted(os.listdir(p)):
                    if os.path.splitext(f)[1].lower() in audio_ext:
                        new_files.append(os.path.join(p, f))

        if new_files:
            self.files.extend(new_files)
            self._update_file_count()

    def _on_drag_enter(self, event):
        self.drop_frame.configure(highlightbackground=GREEN)

    def _on_drag_leave(self, event):
        self.drop_frame.configure(highlightbackground=ACCENT)

    # ── File selection ────────────────────────────────────────────

    def _select_files(self):
        paths = filedialog.askopenfilenames(
            title="Select audio files",
            filetypes=[("Audio files", "*.wav *.mp3 *.flac *.ogg *.aiff *.aif"),
                       ("All", "*.*")])
        if paths:
            self.files.extend(paths)
            self._update_file_count()

    def _select_folder(self):
        folder = filedialog.askdirectory(title="Select folder")
        if folder:
            audio_ext = {'.wav', '.mp3', '.flac', '.ogg', '.aiff', '.aif'}
            for f in sorted(os.listdir(folder)):
                if os.path.splitext(f)[1].lower() in audio_ext:
                    self.files.append(os.path.join(folder, f))
            self._update_file_count()

    def _clear_files(self):
        self.files = []
        self.results = []
        self.batch_output = []
        self.lbl_file_count.config(text="No files selected")
        self.txt.delete("1.0", "end")
        self.progress["value"] = 0
        self.lbl_status.config(text="")

    def _update_file_count(self):
        n = len(self.files)
        self.lbl_file_count.config(text=f"{n} file(s) selected")
        self.drop_label.config(text=f"{n} file(s) ready", fg=GREEN)

    # ── Analysis ──────────────────────────────────────────────────

    def _start_analysis(self):
        if not self.files:
            messagebox.showwarning("No files", "Please select or drop audio files first.")
            return
        self.btn_analyze.config(state="disabled")
        self.progress["value"] = 0
        self.results = []
        self.batch_output = []
        self.txt.delete("1.0", "end")
        threading.Thread(target=self._run_analysis, daemon=True).start()

    def _run_analysis(self):
        total = len(self.files)
        track_type = self.var_type.get()
        do_rename = self.var_rename.get()
        settings = self.settings

        self._log_safe("ANALYSIS\n", "h")
        self._log_safe("=" * 60 + "\n\n")

        for i, path in enumerate(self.files):
            filename = os.path.basename(path)
            pct = int((i / total) * 100)
            self._set_progress(pct, f"[{i+1}/{total}] Analyzing {filename}...")

            self._log_safe(f"[{i+1}/{total}] {filename}\n", "h")

            try:
                result = analyze_file(path)
                self.results.append(result)

                bpm = int(result['bpm']['bpm'])
                bpm_conf = result['bpm']['confidence']
                key = f"{result['key']['key']} {result['key']['mode']}"
                key_fr = f"{result['key']['key_fr']} {result['key']['mode_fr']}"
                key_conf = result['key']['confidence']

                # Genre
                genre_info = result.get('genre', {})
                genre_str = genre_info.get('genre', '?')
                subgenre = genre_info.get('subgenre', '')
                genre_conf = genre_info.get('confidence', '?')
                genre_display = f"{subgenre}" if subgenre else genre_str

                # Display
                self._log_safe(f"  BPM:   {bpm}  ")
                self._log_safe(f"({bpm_conf})\n", "ok" if bpm_conf == "high" else "warn")

                self._log_safe(f"  Key:   {key}  /  {key_fr}  ")
                self._log_safe(f"({key_conf})\n", "ok" if key_conf == "high" else "warn")

                self._log_safe(f"  Genre: {genre_display}  ")
                self._log_safe(f"({genre_conf})\n", "genre")

                if genre_info.get('runner_up'):
                    self._log_safe(f"         runner-up: {genre_info['runner_up']}\n", "dim")

                # Titles per platform
                title_base = os.path.splitext(filename)[0]
                genre_for_title = subgenre or genre_str
                platform_titles = build_platform_titles(
                    result, title_base, settings, track_type, genre_for_title)

                if platform_titles:
                    self._log_safe("  Titles:\n")
                    for plat_name, data in platform_titles.items():
                        lang_tag = data['language'].upper()
                        self._log_safe(f"    [{plat_name}] ", "plat")
                        self._log_safe(f"({lang_tag}) ", "dim")
                        self._log_safe(f"{data['title']}\n")

                # Rename
                if do_rename:
                    new_path = rename_file(path, result, title_base, track_type)
                    self._log_safe(f"  Renamed: ", "dim")
                    self._log_safe(f"{os.path.basename(new_path)}\n", "ok")
                    self.files[i] = new_path

                # Batch output entry
                entry = {
                    'file': filename,
                    'path': path,
                    'bpm': bpm,
                    'bpm_confidence': bpm_conf,
                    'key': key,
                    'key_fr': key_fr,
                    'key_confidence': key_conf,
                    'genre': genre_display,
                    'genre_confidence': genre_conf,
                    'track_type': track_type,
                    'platforms': platform_titles,
                }
                if do_rename:
                    entry['renamed_to'] = self.files[i]
                self.batch_output.append(entry)

            except Exception as e:
                self._log_safe(f"  ERROR: {e}\n", "warn")
                self.results.append({'file': filename, 'error': str(e)})

            self._log_safe("\n")

        self._set_progress(100, "Done!")
        self._log_safe("=" * 60 + "\n", "h")
        self._log_safe(f"Done! {len(self.results)} file(s) analyzed.\n", "ok")
        self.after(0, lambda: self.btn_analyze.config(state="normal"))

    # ── Thread-safe helpers ───────────────────────────────────────

    def _log_safe(self, text, tag=""):
        self.after(0, self._log, text, tag)

    def _log(self, text, tag=""):
        self.txt.insert("end", text, tag)
        self.txt.see("end")

    def _set_progress(self, pct, status_text):
        self.after(0, lambda: (
            self.progress.configure(value=pct),
            self.lbl_status.config(text=status_text),
        ))

    # ── Settings window ───────────────────────────────────────────

    def _open_settings(self):
        SettingsWindow(self, self.settings)

    # ── Actions ───────────────────────────────────────────────────

    def _save_json(self):
        if not self.batch_output:
            messagebox.showinfo("Nothing to save", "Analyze files first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json", filetypes=[("JSON", "*.json")],
            initialfile="batch_metadata.json")
        if path:
            save_batch_metadata(self.batch_output, path)
            messagebox.showinfo("Saved", f"Saved to:\n{path}")

    def _copy(self):
        text = self.txt.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.lbl_status.config(text="Copied!")


# ── Settings Window ───────────────────────────────────────────────

class SettingsWindow(tk.Toplevel):
    def __init__(self, parent, settings):
        super().__init__(parent)
        self.parent = parent
        self.settings = settings
        self.title("Settings — Platforms & Languages")
        self.geometry("550x500")
        self.configure(bg=BG)
        self.resizable(False, False)
        self.grab_set()

        self._build()

    def _build(self):
        # Title
        tk.Label(self, text="Platform Settings", bg=BG, fg=ACCENT,
                 font=("Segoe UI", 14, "bold")).pack(pady=(16, 8))

        tk.Label(self, text="Configure which language to use for each platform.",
                 bg=BG, fg=DIM, font=("Segoe UI", 9)).pack()

        # ── Fixed platforms ──
        section = tk.LabelFrame(self, text="Platforms", bg=BG, fg=FG,
                                font=("Segoe UI", 10, "bold"), padx=12, pady=8)
        section.pack(fill="x", padx=16, pady=(12, 4))

        self.platform_vars = {}
        for name, config in self.settings.get('platforms', {}).items():
            row = tk.Frame(section, bg=BG)
            row.pack(fill="x", pady=2)

            enabled_var = tk.BooleanVar(value=config.get('enabled', True))
            tk.Checkbutton(row, bg=BG, fg=FG, selectcolor=SURFACE,
                           variable=enabled_var, activebackground=BG).pack(side="left")
            tk.Label(row, text=name, bg=BG, fg=FG, font=("Segoe UI", 10),
                     width=12, anchor="w").pack(side="left")

            lang_var = tk.StringVar(value=config.get('language', 'en'))
            combo = ttk.Combobox(row, textvariable=lang_var, values=['en', 'fr'],
                                 state="readonly", width=6)
            combo.pack(side="left", padx=8)

            self.platform_vars[name] = {'enabled': enabled_var, 'language': lang_var}

        # ── Discord servers ──
        discord_section = tk.LabelFrame(self, text="Discord Servers", bg=BG, fg=FG,
                                        font=("Segoe UI", 10, "bold"), padx=12, pady=8)
        discord_section.pack(fill="x", padx=16, pady=(12, 4))

        self.discord_frame = tk.Frame(discord_section, bg=BG)
        self.discord_frame.pack(fill="x")

        self.discord_rows = []
        for server in self.settings.get('discord_servers', []):
            self._add_discord_row(server.get('name', ''), server.get('language', 'fr'),
                                  server.get('enabled', True))

        btn_row = tk.Frame(discord_section, bg=BG)
        btn_row.pack(fill="x", pady=(8, 0))
        tk.Button(btn_row, text="+ Add Server", bg=SURFACE, fg=FG,
                  font=("Segoe UI", 9), relief="flat", cursor="hand2",
                  command=lambda: self._add_discord_row('', 'fr', True)).pack(side="left")

        # ── Defaults ──
        defaults_section = tk.LabelFrame(self, text="Defaults", bg=BG, fg=FG,
                                         font=("Segoe UI", 10, "bold"), padx=12, pady=8)
        defaults_section.pack(fill="x", padx=16, pady=(12, 4))

        row = tk.Frame(defaults_section, bg=BG)
        row.pack(fill="x", pady=2)
        tk.Label(row, text="Default track type:", bg=BG, fg=FG,
                 font=("Segoe UI", 10)).pack(side="left")
        self.var_default_type = tk.StringVar(
            value=self.settings.get('default_track_type', 'loop'))
        ttk.Combobox(row, textvariable=self.var_default_type,
                     values=list(TRACK_TYPES.keys()), state="readonly",
                     width=12).pack(side="left", padx=8)

        # ── Save / Cancel ──
        btn_frame = tk.Frame(self, bg=BG)
        btn_frame.pack(fill="x", padx=16, pady=16)

        tk.Button(btn_frame, text="Save", bg=ACCENT, fg="#1e1e2e",
                  font=("Segoe UI", 11, "bold"), relief="flat", padx=20, pady=6,
                  cursor="hand2", command=self._save).pack(side="right")
        tk.Button(btn_frame, text="Cancel", bg=SURFACE, fg=FG,
                  font=("Segoe UI", 10), relief="flat", padx=16, pady=6,
                  cursor="hand2", command=self.destroy).pack(side="right", padx=8)

    def _add_discord_row(self, name='', language='fr', enabled=True):
        row = tk.Frame(self.discord_frame, bg=BG)
        row.pack(fill="x", pady=2)

        enabled_var = tk.BooleanVar(value=enabled)
        tk.Checkbutton(row, bg=BG, fg=FG, selectcolor=SURFACE,
                       variable=enabled_var, activebackground=BG).pack(side="left")

        name_var = tk.StringVar(value=name)
        tk.Entry(row, textvariable=name_var, bg=SURFACE, fg=FG, font=("Segoe UI", 10),
                 insertbackground=FG, relief="flat", width=20).pack(side="left", padx=4)

        lang_var = tk.StringVar(value=language)
        ttk.Combobox(row, textvariable=lang_var, values=['en', 'fr'],
                     state="readonly", width=6).pack(side="left", padx=4)

        def remove():
            row.destroy()
            self.discord_rows = [r for r in self.discord_rows if r['row'] is not row]

        tk.Button(row, text="X", bg=RED, fg="#1e1e2e", font=("Segoe UI", 8, "bold"),
                  relief="flat", padx=4, cursor="hand2", command=remove).pack(side="left", padx=4)

        self.discord_rows.append({
            'row': row, 'name': name_var, 'language': lang_var, 'enabled': enabled_var
        })

    def _save(self):
        # Platforms
        for name, vars_dict in self.platform_vars.items():
            self.settings['platforms'][name] = {
                'language': vars_dict['language'].get(),
                'enabled': vars_dict['enabled'].get(),
            }

        # Discord servers
        servers = []
        for r in self.discord_rows:
            n = r['name'].get().strip()
            if n:
                servers.append({
                    'name': n,
                    'language': r['language'].get(),
                    'enabled': r['enabled'].get(),
                })
        self.settings['discord_servers'] = servers

        # Defaults
        self.settings['default_track_type'] = self.var_default_type.get()

        # Persist
        save_settings(self.settings)
        self.parent.settings = self.settings
        self.parent.var_type.set(self.settings['default_track_type'])

        self.destroy()
        messagebox.showinfo("Settings saved", "Your platform settings have been saved.")


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
