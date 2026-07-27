"""
webcam-transcoder
Captures from a webcam, encodes to H.264 (output.mp4) via ffmpeg's libx264,
and shows a live preview via ffplay -- both fed from a single ffmpeg process
so Python only has to write each frame's bytes once.

Pass --no-save to skip writing output.mp4 and only show the live preview.

Live controls (type the letter + Enter in the terminal while running):
  h  toggle horizontal flip
  v  toggle vertical flip
  i  toggle color invert
  +  zoom in
  -  zoom out
  r  reset zoom
  q  quit
"""

import argparse
import cv2
import subprocess
import threading
import sys
import os

def get_cameras(max_index=10):
    cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_SILENT)
    arr = []
    devnull_fd = os.open(os.devnull, os.O_WRONLY)
    saved_stderr_fd = os.dup(2)
    os.dup2(devnull_fd, 2)
    try:
        for index in range(max_index):
            cap = cv2.VideoCapture(index)
            if cap.isOpened() and cap.read()[0]:
                arr.append(index)
            cap.release()
    finally:
        os.dup2(saved_stderr_fd, 2)
        os.close(devnull_fd)
        os.close(saved_stderr_fd)
    return arr

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--no-save", action="store_true",
        help="Don't write output.mp4 -- only show the live preview.",
    )
    args = parser.parse_args()

    def print_help():
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

    def input_thread():
        print_help()
        while running["value"]:
            try:
                cmd = input().strip().lower()
            except EOFError:
                break
            if cmd == "":
                continue
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
                else:
                    print(f"Unknown command: {cmd!r}")
                    print_help()

    cam_list = get_cameras()
    if not cam_list:
        print("No cameras found.")
        sys.exit(1)
    print(f"Cameras: {cam_list}")
    if len(cam_list) == 1:
        cam_choice = cam_list[0]
        print(f"Only one camera found, using camera {cam_choice}")
    else:
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

    ffmpeg_cmd = [
        "ffmpeg", "-y",
        "-f", "rawvideo", "-vcodec", "rawvideo",
        "-pix_fmt", "bgr24", "-s", size, "-r", str(frame_fps),
        "-i", "-",
    ]
    if args.no_save:
        ffmpeg_cmd += ["-f", "nut", "-pix_fmt", "yuv420p", "pipe:1"]
    else:
        ffmpeg_cmd += [
            "-filter_complex", "[0:v]split=2[enc][disp]",
            "-map", "[enc]",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            "output.mp4",
            "-map", "[disp]",
            "-f", "nut", "-pix_fmt", "yuv420p",
            "pipe:1",
        ]

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

        try:
            proc1.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc1.kill()
            proc1.wait()
        try:
            proc2.wait(timeout=2)
        except subprocess.TimeoutExpired:
            proc2.terminate()
            try:
                proc2.wait(timeout=2)
            except subprocess.TimeoutExpired:
                proc2.kill()
                proc2.wait()

        if not args.no_save:
            print("Saved output.mp4")


if __name__ == "__main__":
    main()
