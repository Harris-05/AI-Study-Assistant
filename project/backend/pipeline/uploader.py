"""
Simple "upload" helper -- opens a native OS file picker so you can browse to
and select your lecture file instead of typing/pasting a full path.

Falls back to a manual path prompt automatically if no display is available
(e.g. running over SSH on a headless server, where tkinter can't open a
window) -- so this is safe to call in any environment.
"""
from pathlib import Path

AUDIO_VIDEO_FILETYPES = [
    ("Audio/Video files", "*.mp3 *.wav *.m4a *.aac *.mp4 *.mov *.mkv"),
    ("All files", "*.*"),
]


def upload_file() -> str:
    """
    Open a native file picker dialog and return the selected file path.

    Returns:
        Absolute path to the selected file (string).

    Raises:
        FileNotFoundError: if no file was selected/found via either the
            dialog or the fallback manual prompt.
    """
    try:
        import tkinter as tk
        from tkinter import filedialog

        root = tk.Tk()
        root.withdraw()                     # don't show the empty root window
        root.attributes("-topmost", True)   # bring the dialog to the front

        selected_path = filedialog.askopenfilename(
            title="Select lecture audio/video file to upload",
            filetypes=AUDIO_VIDEO_FILETYPES,
        )
        root.destroy()

        if not selected_path:
            raise ValueError("No file was selected in the file picker.")

        print(f"Selected: {selected_path}")
        return selected_path

    except Exception as e:
        # tkinter isn't available (headless env, no display, not installed, etc.)
        print(f"(File picker unavailable here: {e})")
        manual_path = input("Enter the full path to your audio/video file instead: ").strip().strip('"')
        if not manual_path or not Path(manual_path).exists():
            raise FileNotFoundError(f"File not found: {manual_path}")
        return manual_path