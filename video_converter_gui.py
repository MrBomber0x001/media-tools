import os
import subprocess
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, ttk

SUPPORTED_INPUT_EXTENSIONS = (
    ".mp4", ".webm", ".mkv", ".avi", ".mov",
    ".flv", ".m4v", ".ogg", ".wmv", ".mpeg", ".mpg"
)


class VideoConverterApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Video → 3GP Converter")
        self.geometry("520x460")
        self.resizable(False, False)

        self.folder_path = tk.StringVar()

        self._build_ui()

    def _build_ui(self):
        frame = tk.Frame(self, padx=12, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        tk.Label(frame, text="Select folder containing video files:",
                 anchor="w").pack(fill=tk.X)
        tk.Label(frame, text="Supported formats: mp4, webm, mkv, avi, mov, flv, m4v, ogg, wmv, mpeg",
                 anchor="w", fg="gray").pack(fill=tk.X, pady=(2, 8))

        path_frame = tk.Frame(frame)
        path_frame.pack(fill=tk.X, pady=(4, 10))

        path_entry = tk.Entry(
            path_frame, textvariable=self.folder_path, width=54)
        path_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        browse_button = tk.Button(
            path_frame, text="Browse", width=10, command=self.choose_folder)
        browse_button.pack(side=tk.LEFT, padx=(8, 0))

        convert_button = tk.Button(frame, text="Convert video files",
                                   command=self.start_conversion, bg="#4CAF50", fg="white", padx=8, pady=6)
        convert_button.pack(fill=tk.X)

        self.progress_bar = ttk.Progressbar(
            frame, mode="determinate", length=420)
        self.progress_bar.pack(fill=tk.X, pady=(12, 8))

        tk.Label(frame, text="Output log:", anchor="w").pack(
            fill=tk.X, pady=(8, 0))

        self.log_box = scrolledtext.ScrolledText(
            frame, width=64, height=16, state=tk.DISABLED)
        self.log_box.pack(fill=tk.BOTH, expand=True)

        self.status_label = tk.Label(frame, text="Ready", anchor="w")
        self.status_label.pack(fill=tk.X, pady=(8, 0))

    def choose_folder(self):
        folder = filedialog.askdirectory(
            title="Select folder with video files")
        if folder:
            self.folder_path.set(folder)

    def start_conversion(self):
        folder = self.folder_path.get().strip()
        if not folder:
            messagebox.showwarning(
                "No folder selected", "Please select a folder containing supported video files.")
            return

        if not os.path.isdir(folder):
            messagebox.showerror(
                "Invalid folder", "The selected path is not a valid folder.")
            return

        self.log_box.configure(state=tk.NORMAL)
        self.log_box.delete("1.0", tk.END)
        self.log_box.configure(state=tk.DISABLED)

        self.progress_bar.config(value=0)
        self.status_label.config(text="Converting...")
        thread = threading.Thread(
            target=self.convert_folder, args=(folder,), daemon=True)
        thread.start()

    def _is_supported_input(self, file_name):
        return file_name.lower().endswith(SUPPORTED_INPUT_EXTENSIONS)

    def convert_folder(self, folder):
        input_files = [f for f in os.listdir(folder)
                       if self._is_supported_input(f) and not f.lower().endswith(".3gp")]
        if not input_files:
            self.append_log(
                "No supported video files found in the selected folder.")
            self.after(0, lambda: self.status_label.config(
                text="No files converted"))
            return

        self.after(0, lambda: self.progress_bar.config(
            maximum=len(input_files), value=0))
        for index, file_name in enumerate(input_files, start=1):
            source_path = os.path.join(folder, file_name)
            output_name = os.path.splitext(file_name)[0] + ".3gp"
            output_path = os.path.join(folder, output_name)
            self.append_log(f"Converting {file_name} → {output_name}...")

            cmd = [
                "ffmpeg",
                "-y",
                "-i",
                source_path,
                "-vf",
                "scale=240:320",
                "-c:v",
                "mpeg4",
                "-b:v",
                "600k",
                "-c:a",
                "aac",
                "-b:a",
                "128k",
                "-ar",
                "44100",
                "-ac",
                "1",
                output_path,
            ]

            try:
                result = subprocess.run(cmd, capture_output=True, text=True)
                if result.returncode != 0:
                    self.append_log(f"Failed: {file_name}")
                    self.append_log(result.stderr.strip())
                else:
                    self.append_log(f"Finished converting {file_name}")
            except FileNotFoundError:
                self.append_log(
                    "Error: ffmpeg command not found. Please install ffmpeg and make sure it is on your PATH.")
                self.after(0, lambda: self.status_label.config(
                    text="ffmpeg not found"))
                return
            except Exception as exc:
                self.append_log(f"Error converting {file_name}: {exc}")

            self.after(
                0, lambda value=index: self.progress_bar.config(value=value))

        self.append_log("All conversions completed.")
        self.after(0, lambda: self.status_label.config(text="Done"))

    def append_log(self, message: str):
        def _append():
            self.log_box.configure(state=tk.NORMAL)
            self.log_box.insert(tk.END, message + "\n")
            self.log_box.see(tk.END)
            self.log_box.configure(state=tk.DISABLED)
        self.after(0, _append)


if __name__ == "__main__":
    app = VideoConverterApp()
    app.mainloop()
