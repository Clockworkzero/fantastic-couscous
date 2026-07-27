"""
webcam-transcoder
Captures from a webcam, encodes to H.264 (output.mp4) via ffmpeg's libx264,
and shows a live preview via ffplay -- both fed from a single ffmpeg process
so Python only has to write each frame's bytes once.

Live controls (type the letter + Enter in the terminal while running):
  h  toggle horizontal flip
  v  toggle vertical flip
  i  toggle color invert
  +  zoom in
  -  zoom out
  r  reset zoom
  q  quit
"""

import cv2
import subprocess
import threading
import sys

def get_cameras(max_index=10):
    """Probe camera indices 0..max_index-1 and return the ones that open."""
    cv2.setLogLevel(cv2.LOG_LEVEL_SILENT)
    arr = []
    for index in range(max_index):
        cap = cv2.VideoCapture(index)
        if cap.isOpened() and cap.read()[0]:
            arr.append(index)
        cap.release()
    return arr

def main():
    def input_thread():
        print(
            "\nControls (press Enter after each):\n"
            "  h  = toggle horizontal flip\n"
            "  v  = toggle vertical flip\n"
            "  i  = toggle color invert\n"
            "  +  = zoom in\n"
            "  -  = zoom out\n"
            "  r  = reset zoom\n"
            "  q  = quit\n"
        )
        while running["value"]:
            try:
                cmd = input().strip().lower()
            except EOFError:
                break
            with state_lock:
                if cmd == "h":
                    state["flip_h"] = not state["flip_h"]
                elif cmd == "v":
                    state["flip_v"] = not state["flip_v"]
                elif cmd == "i":
                    state["invert"] = not state["invert"]
                elif cmd == "+":
                    state["scale"] = round(min(state["scale"] + 0.1, 3.0), 2)
                elif cmd == "-":
                    state["scale"] = round(max(state["scale"] - 0.1, 0.2), 2)
                elif cmd == "r":
                    state["scale"] = 1.0
                elif cmd == "q":
                    running["value"] = False

    cam_list = get_cameras()
    if not cam_list:
        print("No cameras found.")
        sys.exit(1)
    print(f"Cameras: {cam_list}")
    cam_choice = int(input("What camera would you like to use? "))

    cam = cv2.VideoCapture(cam_choice)

    frame_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    frame_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))
    frame_fps = int(cam.get(cv2.CAP_PROP_FPS))
    print(f"FPS: {frame_fps}, height: {frame_height}, width: {frame_width}")

    size = f"{frame_width}x{frame_height}"

    # --- shared live-toggle state ---
    state = {"flip_h": False, "flip_v": False, "invert": False, "scale": 1.0}
    state_lock = threading.Lock()
    running = {"value": True}



    threading.Thread(target=input_thread, daemon=True).start()

    # Process 1: read raw frames on stdin, encode H.264 to file,
    # and emit a preview stream (nut container -- carries frame boundaries,
    # so the reader never has to guess how many bytes make up a frame).
    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24", "-s", size, "-r", str(frame_fps),
        "-i", "-",
        "-filter_complex", "[0:v]split=2[enc][disp]",
        "-map", "[enc]",
        "-c:v", "libx264", "-preset", "fast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "output.mp4",
        "-map", "[disp]",
        "-f", "nut", "-pix_fmt", "yuv420p",
        "pipe:1",
    ]

    # Process 2: display whatever it receives on stdin.
    ffplay_cmd = ["ffplay", "-f", "nut", "-window_title", "Camera Preview", "-i", "-"]

    proc1 = subprocess.Popen(ffmpeg_cmd, stdin=subprocess.PIPE,
                              stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    proc2 = subprocess.Popen(ffplay_cmd, stdin=proc1.stdout, stderr=subprocess.DEVNULL)
    proc1.stdout.close()

    try:
        while running["value"] and proc1.poll() is None and proc2.poll() is None:
            ret, frame = cam.read()
            if not ret:
                break

            with state_lock:
                fh, fv, inv, sc = (state["flip_h"], state["flip_v"],
                                    state["invert"], state["scale"])

            if fh and fv:
                frame = cv2.flip(frame, -1)
            elif fh:
                frame = cv2.flip(frame, 1)
            elif fv:
                frame = cv2.flip(frame, 0)

            if inv:
                frame = cv2.bitwise_not(frame)

            if sc != 1.0:
                new_w = max(1, int(frame_width * sc))
                new_h = max(1, int(frame_height * sc))
                resized = cv2.resize(frame, (new_w, new_h))
                canvas = cv2.copyMakeBorder(
                    resized,
                    0, max(0, frame_height - new_h),
                    0, max(0, frame_width - new_w),
                    cv2.BORDER_CONSTANT, value=(0, 0, 0),
                )
                frame = canvas[:frame_height, :frame_width]

            try:
                proc1.stdin.write(frame.tobytes())
                proc1.stdin.flush()
            except BrokenPipeError:
                break
    finally:
        running["value"] = False
        cam.release()
        if proc1.stdin and not proc1.stdin.closed:
            try:
                proc1.stdin.close()
            except BrokenPipeError:
                pass
        proc1.wait()
        proc2.wait()
        print("Saved output.mp4")


if __name__ == "__main__":
    main()

