# webcam-transcoder

Captures video from a webcam, encodes it to H.264 (`output.mp4`) using
ffmpeg's `libx264`, and shows a live preview via `ffplay` — both fed from
a single ffmpeg process so no double rendering work happens on the Python
side.

## Requirements

- Linux
- Python 3.9+
- `ffmpeg` / `ffplay` with `libx264` support (installed automatically by
  `setup.sh` on Debian/Ubuntu; install manually on other distros)

## Setup

```bash
make setup
```

This will:
1. Install `ffmpeg`/`ffplay` via `apt` if not already present (asks for
   `sudo`), and confirm `libx264` is available.
2. Install Python dependencies (`opencv-python`) for the current user
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

You'll be asked to pick a camera index, then a preview window opens.
While it's running, you can type these commands (+ Enter) in the
terminal:

| Key | Action              |
|-----|----------------------|
| h   | toggle horizontal flip |
| v   | toggle vertical flip |
| i   | toggle color invert  |
| +   | zoom in              |
| -   | zoom out             |
| r   | reset zoom           |
| q   | quit                 |

Recording stops and `output.mp4` is finalized when you quit (via `q`,
or by closing the preview window).

## Cleaning up

```bash
make clean
```

Removes any generated `output.mp4` and cached bytecode.

## How it works

- OpenCV grabs frames from the camera and applies any active
  flip/invert/zoom transform.
- Each frame's raw bytes are written to a single `ffmpeg` subprocess,
  which uses `split` in a filter graph to send the same frame down two
  paths: one encoded to `output.mp4` via `libx264`, the other piped
  (in the `nut` container, which preserves frame boundaries over a
  pipe) into `ffplay` for live preview.
- This avoids OpenCV's `VideoWriter`, whose default H.264 path
  (`h264_v4l2m2m`) is a hardware encoder not available on most
  desktops/laptops — `libx264` is a reliable software encoder instead.

