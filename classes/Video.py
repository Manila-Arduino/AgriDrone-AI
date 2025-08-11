import os
from dataclasses import dataclass
from urllib.parse import urlparse
import cv2
from typing import Any, Literal, Callable, Tuple
import uuid
import threading
import queue
import time
import numpy as np

MatLike = np.ndarray

# Try to import Picamera2; fall back to OpenCV if unavailable
try:
    from picamera2 import Picamera2

    PICAMERA2_AVAILABLE = True
except ImportError:
    PICAMERA2_AVAILABLE = False


@dataclass
class Video:
    cam_index: int = 0
    width: int = 256
    height: int = 256
    window_name: str = "Capture"
    with_window: bool = True
    full_screen: bool = False
    rtmp_url: str = ""
    # apiPreference: int = cv2.CAP_DSHOW

    def __post_init__(self):
        if not os.path.exists("captures"):
            os.makedirs("captures")

        if self.rtmp_url:

            def _open(url_try: str, is_rtmp: bool) -> cv2.VideoCapture:
                if is_rtmp:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                        "rtmp_buffer;0|timeout;5000000"
                    )
                else:
                    os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                        "rtsp_transport;tcp|stimeout;5000000|max_delay;0"
                    )
                cap = cv2.VideoCapture(url_try, cv2.CAP_FFMPEG)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                return cap

            # Try RTMP first
            self.cap = _open(self.rtmp_url, is_rtmp=True)

            # Fallback to RTSP if RTMP fails
            if not self.cap.isOpened():
                p = urlparse(self.rtmp_url)
                host = p.hostname or "127.0.0.1"
                path = p.path or ""
                rtsp_url = f"rtsp://{host}:8554{path}"
                self.cap = _open(rtsp_url, is_rtmp=False)

            if not self.cap.isOpened():
                raise Exception(f"Error: Could not open stream from {self.rtmp_url}")

            self.use_picamera = False
            self.q = queue.Queue()
            threading.Thread(target=self._reader, daemon=True).start()

        elif PICAMERA2_AVAILABLE:
            self.picam2 = Picamera2()
            config = self.picam2.create_still_configuration(
                main={"size": (self.width, self.height)}
            )
            self.picam2.configure(config)
            self.picam2.start()
            self.use_picamera = True
        else:
            self.cap = cv2.VideoCapture(0)
            self.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            self.cap.set(cv2.CAP_PROP_FPS, 5)
            if not self.cap.isOpened():
                raise Exception("Error: Could not open camera.")
            self.use_picamera = False
            self.q = queue.Queue()
            threading.Thread(target=self._reader, daemon=True).start()

        if self.with_window:
            cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
            cv2.setMouseCallback(self.window_name, self._on_mouse)
            if self.full_screen:
                cv2.setWindowProperty(
                    self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
                )

        self.frame = None
        self.buttons = []

    def change_cam_index(self, cam_index: int):
        if self.cap.isOpened():
            self.cap.release()
        self.cam_index = cam_index
        self.cap = cv2.VideoCapture(self.cam_index)
        if not self.cap.isOpened():
            raise Exception("Error: Could not open camera.")
        self.frame = None

    def _on_mouse(self, event, x, y, flags, param):
        if event == cv2.EVENT_LBUTTONDOWN:
            for x1, y1, x2, y2, callback in self.buttons:
                if x1 <= x <= x2 and y1 <= y <= y2:
                    callback()

    # read frames as soon as they are available, keeping only most recent one
    def _reader(self):
        while True:
            ret, frame = self.cap.read()
            if not ret:
                time.sleep(0.01)
                continue
                # break
            if not self.q.empty():
                try:
                    self.q.get_nowait()  # discard previous (unprocessed) frame
                except queue.Empty:
                    pass

            self.q.put(frame)

    def read(self):
        if self.use_picamera:
            rgb = self.picam2.capture_array()
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            return bgr
        else:
            return self.q.get()

    def capture(self, display: bool) -> MatLike:
        img = self._capture()
        cv2.waitKey(1)
        if display:
            self.displayImg(img)
        return img

    # def release(self):
    #     self.release()

    def _capture(self):
        frame = self.read()

        # Resize
        resized_frame = cv2.resize(frame, (self.width, self.height))

        self.frame = resized_frame
        return resized_frame

        # Overlay yellow circle

        # Display

    def circle(self, color: Any):
        if color == "yellow":
            color = (63, 201, 248)
        elif color == "green":
            color = (8, 240, 8)

        radius = 12
        x = self.width - radius - 10  # 10 pixels from the right edge
        y = radius + 10  # 10 pixels from the top edge
        cv2.circle(self.frame, (x, y), radius, color, -1)  # type: ignore

    def displayImg(self, img: Any):
        if not self.with_window:
            return
        cv2.imshow(self.window_name, img)  # type: ignore

    def release(self):
        if hasattr(self, "_rtmp_cap") and self._rtmp_cap:
            try:
                self._rtmp_cap.release()
            except Exception:
                pass
        if hasattr(self, "cap"):
            try:
                self.cap.release()
            except Exception:
                pass
        cv2.destroyAllWindows()

    def is_pressed(self, key: str) -> bool:
        return cv2.waitKey(1) & 0xFF == ord(key)

    def save_image(self, name: str = ""):
        print("Saving image...")
        if name == "":
            # name = f"{uuid.uuid4().hex}"
            name = str(int(time.time() * 1000))

        if self.frame is not None:
            filename = f"captures/{name}.jpg"
            cv2.imwrite(filename, self.frame)
            print(f"Image saved as {filename}")
        else:
            print("Error: No frame captured.")

    def text(
        self,
        img: Any,
        text: str,
        pos: tuple[int, int] = (0, 0),
        scale: float = 1.0,
        color: tuple[int, int, int] = (0, 255, 0),
        thickness: int = 2,
    ) -> Any:
        font = cv2.FONT_HERSHEY_SIMPLEX
        cv2.putText(
            img,
            text,
            pos,
            font,
            scale,
            color,
            thickness,
            cv2.LINE_AA,
        )
        return img

    def resize(self, img: Any, size: tuple[int, int]) -> Any:
        return cv2.resize(img, size)

    def padding(
        self,
        img: Any,
        top: int = 0,
        bottom: int = 0,
        left: int = 0,
        right: int = 0,
        color: tuple[int, int, int] = (0, 0, 0),
    ) -> Any:
        return cv2.copyMakeBorder(
            img, top, bottom, left, right, cv2.BORDER_CONSTANT, value=color
        )

    def button(
        self,
        img: Any,
        text: str,
        pos: tuple[int, int] = (0, 0),
        size: tuple[int, int] = (200, 50),  # new: (width, height)
        scale: float = 1.0,
        thickness: int = 2,
        color: tuple[int, int, int] = (0, 255, 0),
        bg_color: tuple[int, int, int] = (0, 100, 0),
        on_click: Callable[[], None] | None = None,
    ) -> Any:
        x, y = pos
        w, h = size
        cv2.rectangle(img, (x, y), (x + w, y + h), bg_color, -1)
        cv2.putText(
            img,
            text,
            (x + 10, y + h // 2 + 10),
            cv2.FONT_HERSHEY_SIMPLEX,
            scale,
            color,
            thickness,
            cv2.LINE_AA,
        )
        if on_click:
            # remove old region if same
            self.buttons = [b for b in self.buttons if b[:4] != (x, y, x + w, y + h)]
            self.buttons.append((x, y, x + w, y + h, on_click))

        return img
