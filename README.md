# webcam-transcoder

Captures video from a webcam, encodes it to H.264 (`output.mp4`) using
ffmpeg's `libx264`, and shows a live preview via `ffplay` — both fed from
a single ffmpeg process so no double rendering work happens on the Python
side.

## Requirements

- Linux
- Python 3.9+
- `pip3` (installed automatically by `setup.sh` if missing)
- `ffmpeg` / `ffplay` with `libx264` support (installed automatically by
  `setup.sh` on Debian/Ubuntu; install manually on other distros)

## Setup

```bash
make setup
```

This will:
1. Install `ffmpeg`/`ffplay` via `apt` if not already present (asks for
   `sudo`), and confirm `libx264` is available.
2. Install `pip3` via `apt` if not already present — it isn't bundled
   by default on some distros (e.g. Ubuntu 26).
3. Install Python dependencies (`opencv-python`) for the current user
   via `pip3 install --user --break-system-packages`, with no virtual
   environment.

If you're not on a Debian/Ubuntu system, install `ffmpeg` (with
`libx264`) through your distro's package manager first, then re-run
`make setup` — it will skip the apt step once it detects both binaries.

## Running

```bash
make run
```

or manually:

```bash
python3 app.py
```

If more than one camera is found, you'll be asked to pick a camera
index; if only one is found, it's used automatically. A preview
window then opens. While it's running, you can type these commands
(+ Enter) in the terminal:

| Key | Action                 |
|-----|----------------------  |
| h   | toggle horizontal flip |
| v   | toggle vertical flip   |
| i   | toggle color invert    |
| +   | zoom in                |
| -   | zoom out               |
| r   | reset zoom             |
| q   | quit                   |

## Cleaning up

```bash
make clean
```

Removes cached bytecode.

## How it works

- OpenCV grabs frames from the camera and applies any active
  flip/invert/zoom transform.
- Each frame's raw bytes are written to a single `ffmpeg` subprocess,
  which encodes them to H.264 (`libx264`, `ultrafast` preset,
  `zerolatency` tune to keep encoding overhead low) and wraps the
  result in the `nut` container (which preserves frame boundaries
  over a pipe), piping that straight into `ffplay` for live preview.
  Nothing touches disk.
