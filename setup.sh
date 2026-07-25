#!/usr/bin/env bash
# Sets up everything needed to run app.py on Linux:
#   - opencv-python installed for the current user (no venv)
#   - system ffmpeg/ffplay with libx264 support
set -euo pipefail

echo "== webcam-transcoder setup =="

# --- system packages (ffmpeg/ffplay are not pip-installable) ---
if command -v ffmpeg >/dev/null 2>&1 && command -v ffplay >/dev/null 2>&1; then
    echo "[ok] ffmpeg and ffplay already installed"
else
    echo "[..] ffmpeg/ffplay not found, installing via apt (requires sudo)"
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y ffmpeg
    else
        echo "[!!] apt-get not found. Install ffmpeg and ffplay manually for your distro, then re-run."
        exit 1
    fi
fi

if ! ffmpeg -encoders 2>/dev/null | grep libx264; then
    echo "[!!] Your ffmpeg build has no libx264 encoder."
    echo "     On Debian/Ubuntu the default 'ffmpeg' package includes it -- if this warning"
    echo "     appears, you may have a minimal/custom build. Try: sudo apt-get install --reinstall ffmpeg"
    exit 1
fi
echo "[ok] libx264 encoder present"

# --- pip itself (not installed by default on some distros, e.g. Ubuntu 26) ---
if command -v pip3 >/dev/null 2>&1; then
    echo "[ok] pip3 already installed"
else
    echo "[..] pip3 not found, installing via apt (requires sudo)"
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y python3-pip
    else
        echo "[!!] apt-get not found. Install pip3 manually for your distro, then re-run."
        exit 1
    fi
fi

# --- python dependencies (no venv) ---
echo "[..] installing Python dependencies for the current user"
# --break-system-packages is required on Debian/Ubuntu (PEP 668) since
# the system Python is externally managed; --user keeps it out of
# system site-packages so it won't need sudo or touch other projects.
pip3 install --user --break-system-packages -r requirements.txt

echo
echo "Setup complete. Run the app with:"
echo "    make run"
echo "or manually:"
echo "    python3 app.py"

