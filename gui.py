"""
Music Automation Suite — GUI
Drop-in friendly interface: select files, analyze, see results.
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

from analyzer import analyze_file
from metadata import build_all_titles, build_filename, rename_file, save_batch_metadata
from config import PLATFORMS, TRACK_TYPES


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Music Automation Suite")
        self.geometry("900x700")
        self.configure(bg="#1e1e2e")
        self.resizable(True, True)

        self.files = []          # list of file paths
        self.results = []        # analysis results
        self.batch_output = []   # processed metadata

        self._build_ui()

    # ── UI ────────────────────────────────────────────────────────

    def _build_ui(self):
        style = ttk.Style(self)
        style.theme_use("clam")

        # Dark theme colors
        bg = "#1e1e2e"
        fg = "#cdd6f4"
        accent = "#89b4fa"
        surface = "#313244"
        green = "#a6e3a1"
        red = "#f38ba8"

        style.configure("TFrame", background=bg)
        style.configure("TLabel", background=bg, foreground=fg, font=("Segoe UI", 10))
        style.configure("Title.TLabel", background=bg, foreground=accent,
                        font=("Segoe UI", 16, "bold"))
        style.configure("TButton", font=("Segoe UI", 10, "bold"), padding=8)
        style.configure("Accent.TButton", font=("Segoe UI", 11, "bold"), padding=10)
        style.configure("TCombobox", font=("Segoe UI", 10))
        style.configure("TCheckbutton", background=bg, foreground=fg,
                        font=("Segoe UI", 10))

        # ── Top bar ──
        top = ttk.Frame(self)
        top.pack(fill="x", padx=16, pady=(16, 8))

        ttk.Label(top, text="Music Automation Suite", style="Title.TLabel").pack(
            side="left")

        # ── File selection ──
        file_frame = ttk.Frame(self)
        file_frame.pack(fill="x", padx=16, pady=4)

        btn_select = ttk.Button(file_frame, text="Select Files",
                                command=self._select_files, style="Accent.TButton")
        btn_select.pack(side="left", padx=(0, 8))

        btn_folder = ttk.Button(file_frame, text="Select Folder",
                                command=self._select_folder)
        btn_folder.pack(side="left", padx=(0, 8))

        btn_clear = ttk.Button(file_frame, text="Clear", command=self._clear_files)
        btn_clear.pack(side="left")

        self.lbl_file_count = ttk.Label(file_frame, text="No files selected")
        self.lbl_file_count.pack(side="left", padx=16)

        # ── Options row ──
        opts = ttk.Frame(self)
        opts.pack(fill="x", padx=16, pady=8)

        ttk.Label(opts, text="Track type:").pack(side="left")
        self.var_type = tk.StringVar(value="loop")
        combo_type = ttk.Combobox(opts, textvariable=self.var_type,
                                  values=list(TRACK_TYPES.keys()), state="readonly",
                                  width=12)
        combo_type.pack(side="left", padx=(4, 16))

        ttk.Label(opts, text="Genre:").pack(side="left")
        self.var_genre = tk.StringVar()
        ttk.Entry(opts, textvariable=self.var_genre, width=14).pack(
            side="left", padx=(4, 16))

        self.var_rename = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Rename files with BPM/key",
                        variable=self.var_rename).pack(side="left", padx=(0, 16))

        # ── Analyze button ──
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=16, pady=4)

        self.btn_analyze = ttk.Button(btn_frame, text="Analyze & Generate Titles",
                                      command=self._start_analysis,
                                      style="Accent.TButton")
        self.btn_analyze.pack(side="left")

        self.lbl_status = ttk.Label(btn_frame, text="")
        self.lbl_status.pack(side="left", padx=16)

        # ── Progress bar ──
        self.progress = ttk.Progressbar(self, mode="determinate")
        self.progress.pack(fill="x", padx=16, pady=4)

        # ── Results area ──
        result_frame = ttk.Frame(self)
        result_frame.pack(fill="both", expand=True, padx=16, pady=(4, 8))

        self.txt_results = tk.Text(result_frame, bg=surface, fg=fg,
                                   font=("Consolas", 10), wrap="word",
                                   insertbackground=fg, relief="flat", bd=0,
                                   padx=12, pady=12)
        scrollbar = ttk.Scrollbar(result_frame, command=self.txt_results.yview)
        self.txt_results.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.txt_results.pack(fill="both", expand=True)

        # Tag configs for colored output
        self.txt_results.tag_configure("header", foreground=accent,
                                       font=("Consolas", 11, "bold"))
        self.txt_results.tag_configure("good", foreground=green)
        self.txt_results.tag_configure("warn", foreground=red)
        self.txt_results.tag_configure("platform", foreground="#fab387")

        # ── Bottom buttons ──
        bottom = ttk.Frame(self)
        bottom.pack(fill="x", padx=16, pady=(0, 16))

        ttk.Button(bottom, text="Save Metadata JSON",
                   command=self._save_json).pack(side="left", padx=(0, 8))
        ttk.Button(bottom, text="Copy Results",
                   command=self._copy_results).pack(side="left")

        # Welcome message
        self._log("Welcome! Select audio files or a folder to get started.\n\n"
                  "Supported formats: WAV, MP3, FLAC, OGG, AIFF\n", "header")

    # ── File selection ────────────────────────────────────────────

    def _select_files(self):
        paths = filedialog.askopenfilenames(
            title="Select audio files",
            filetypes=[
                ("Audio files", "*.wav *.mp3 *.flac *.ogg *.aiff *.aif"),
                ("WAV", "*.wav"), ("MP3", "*.mp3"), ("All", "*.*"),
            ],
        )
        if paths:
            self.files = list(paths)
            self._update_file_count()

    def _select_folder(self):
        folder = filedialog.askdirectory(title="Select folder with audio files")
        if folder:
            extensions = {'.wav', '.mp3', '.flac', '.ogg', '.aiff', '.aif'}
            self.files = [
                os.path.join(folder, f) for f in sorted(os.listdir(folder))
                if os.path.splitext(f)[1].lower() in extensions
            ]
            self._update_file_count()

    def _clear_files(self):
        self.files = []
        self.results = []
        self.batch_output = []
        self._update_file_count()
        self.txt_results.delete("1.0", "end")
        self._log("Cleared. Select new files to analyze.\n", "header")

    def _update_file_count(self):
        n = len(self.files)
        if n == 0:
            self.lbl_file_count.config(text="No files selected")
        else:
            self.lbl_file_count.config(text=f"{n} file(s) selected")
            self._log(f"\n{n} file(s) ready:\n", "header")
            for f in self.files:
                self._log(f"  {os.path.basename(f)}\n")

    # ── Analysis ──────────────────────────────────────────────────

    def _start_analysis(self):
        if not self.files:
            messagebox.showwarning("No files", "Please select audio files first.")
            return

        self.btn_analyze.config(state="disabled")
        self.lbl_status.config(text="Analyzing...")
        self.progress["value"] = 0
        self.progress["maximum"] = len(self.files)
        self.results = []
        self.batch_output = []

        # Run analysis in a background thread so the UI stays responsive
        thread = threading.Thread(target=self._run_analysis, daemon=True)
        thread.start()

    def _run_analysis(self):
        track_type = self.var_type.get()
        genre = self.var_genre.get()
        do_rename = self.var_rename.get()

        self._log_safe("\n" + "=" * 60 + "\n", "header")
        self._log_safe("ANALYSIS RESULTS\n", "header")
        self._log_safe("=" * 60 + "\n\n")

        for i, path in enumerate(self.files):
            filename = os.path.basename(path)
            self._log_safe(f"[{i+1}/{len(self.files)}] {filename}\n", "header")
            self._update_progress(i)

            try:
                result = analyze_file(path)
                self.results.append(result)

                bpm = result['bpm']['bpm']
                bpm_conf = result['bpm']['confidence']
                key = f"{result['key']['key']} {result['key']['mode']}"
                key_fr = f"{result['key']['key_fr']} {result['key']['mode_fr']}"
                key_conf = result['key']['confidence']

                conf_tag = "good" if bpm_conf == "high" else "warn"
                self._log_safe(f"  BPM:  {bpm}  ", "")
                self._log_safe(f"({bpm_conf} confidence)\n", conf_tag)

                conf_tag = "good" if key_conf == "high" else "warn"
                self._log_safe(f"  Key:  {key}  /  {key_fr}  ", "")
                self._log_safe(f"({key_conf} confidence)\n", conf_tag)

                # Build titles
                title = os.path.splitext(filename)[0]
                titles = build_all_titles(result, title, track_type, genre)

                self._log_safe("  Titles:\n")
                for platform, data in titles.items():
                    self._log_safe(f"    [{platform}] ", "platform")
                    self._log_safe(f"{data['title']}\n")

                # Rename if requested
                if do_rename:
                    new_path = rename_file(path, result, title, track_type)
                    new_name = os.path.basename(new_path)
                    self._log_safe(f"  Renamed: ", "")
                    self._log_safe(f"{new_name}\n", "good")
                    # Update the file path in our list
                    self.files[i] = new_path

                # Build batch output entry
                entry = {
                    'file': filename,
                    'path': path,
                    'bpm': bpm,
                    'bpm_confidence': bpm_conf,
                    'key': key,
                    'key_fr': key_fr,
                    'key_confidence': key_conf,
                    'track_type': track_type,
                    'genre': genre,
                    'platforms': titles,
                }
                if do_rename:
                    entry['renamed_to'] = new_path
                self.batch_output.append(entry)

            except Exception as e:
                self._log_safe(f"  ERROR: {e}\n", "warn")
                self.results.append({'file': filename, 'error': str(e)})

            self._log_safe("\n")

        self._update_progress(len(self.files))
        self._log_safe("=" * 60 + "\n", "header")
        self._log_safe(f"Done! {len(self.results)} file(s) analyzed.\n", "good")
        self._finish_analysis()

    # ── Thread-safe UI updates ────────────────────────────────────

    def _log(self, text, tag=""):
        self.txt_results.insert("end", text, tag)
        self.txt_results.see("end")

    def _log_safe(self, text, tag=""):
        """Log from a background thread."""
        self.after(0, self._log, text, tag)

    def _update_progress(self, value):
        self.after(0, lambda: self.progress.configure(value=value))

    def _update_status(self, text):
        self.after(0, lambda: self.lbl_status.config(text=text))

    def _finish_analysis(self):
        self.after(0, lambda: self.btn_analyze.config(state="normal"))
        self._update_status("Done!")

    # ── Actions ───────────────────────────────────────────────────

    def _save_json(self):
        if not self.batch_output:
            messagebox.showinfo("Nothing to save", "Analyze files first.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
            initialfile="batch_metadata.json",
        )
        if path:
            save_batch_metadata(self.batch_output, path)
            messagebox.showinfo("Saved", f"Metadata saved to:\n{path}")

    def _copy_results(self):
        text = self.txt_results.get("1.0", "end").strip()
        if text:
            self.clipboard_clear()
            self.clipboard_append(text)
            self.lbl_status.config(text="Copied to clipboard!")


def main():
    app = App()
    app.mainloop()


if __name__ == '__main__':
    main()
