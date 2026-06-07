import os
from dataclasses import dataclass
import platform
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
    cam_index: Any = 0
    width: int = 256
    height: int = 256
    window_name: str = "Capture"
    with_window: bool = True
    full_screen: bool = False
    stream_url: str = ""
    reconnect_delay_sec: float = 1.0
    read_timeout_sec: float = 5.0
    # apiPreference: int = cv2.CAP_DSHOW

    def __post_init__(self):
        if not os.path.exists("captures"):
            os.makedirs("captures")

        self.frame = None
        self.buttons = []
        self.q = queue.Queue(maxsize=1)
        self._stop_reader = False
        self._reader_thread = None
        self._open_lock = threading.Lock()
        self.use_picamera = False

        # if self.rtmp_url:

        #     def _open(url_try: str, is_rtmp: bool) -> cv2.VideoCapture:
        #         if is_rtmp:
        #             os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        #                 "rtmp_buffer;0|timeout;5000000"
        #             )
        #         else:
        #             os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
        #                 "rtsp_transport;tcp|stimeout;5000000|max_delay;0"
        #             )
        #         cap = cv2.VideoCapture(url_try, cv2.CAP_FFMPEG)
        #         cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        #         return cap

        #     # Try RTMP first
        #     self.cap = _open(self.rtmp_url, is_rtmp=True)

        #     # Fallback to RTSP if RTMP fails
        #     if not self.cap.isOpened():
        #         p = urlparse(self.rtmp_url)
        #         host = p.hostname or "127.0.0.1"
        #         path = p.path or ""
        #         rtsp_url = f"rtsp://{host}:8554{path}"
        #         self.cap = _open(rtsp_url, is_rtmp=False)

        #     if not self.cap.isOpened():
        #         raise Exception(f"Error: Could not open stream from {self.rtmp_url}")

        #     self.use_picamera = False
        #     self.q = queue.Queue()
        #     threading.Thread(target=self._reader, daemon=True).start()

        if self.stream_url:
            self.cap = self._make_capture()
            if not self.cap.isOpened():
                raise Exception(f"Error: Could not open stream from {self.stream_url}")
            self._start_reader_thread()

        elif PICAMERA2_AVAILABLE:
            self.picam2 = Picamera2()
            config = self.picam2.create_still_configuration(
                main={"size": (self.width, self.height)}
            )
            self.picam2.configure(config)
            self.picam2.start()
            self.use_picamera = True

        else:
            self.cap = self._make_capture()
            print(f"Cam Index: {self.cam_index}")
            if not self.cap.isOpened():
                raise Exception("Error: Could not open camera.")
            self._start_reader_thread()

        #! FOR FULL SCREEN
        # if self.with_window:
        #     cv2.namedWindow(self.window_name, cv2.WINDOW_NORMAL)
        #     cv2.setMouseCallback(self.window_name, self._on_mouse)
        #     if self.full_screen:
        #         cv2.setWindowProperty(
        #             self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
        #         )

        #! FOR TRUE ASPECT RATIO
        if self.with_window:
            cv2.namedWindow(self.window_name, cv2.WINDOW_AUTOSIZE)
            cv2.setMouseCallback(self.window_name, self._on_mouse)
            if self.full_screen:
                cv2.setWindowProperty(
                    self.window_name, cv2.WND_PROP_FULLSCREEN, cv2.WINDOW_FULLSCREEN
                )
            else:
                cv2.resizeWindow(self.window_name, self.width, self.height)

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
        last_ok_time = time.time()

        while not self._stop_reader:
            try:
                ret, frame = self.cap.read()
            except Exception:
                ret, frame = False, None

            if ret and frame is not None:
                last_ok_time = time.time()

                if self.q.full():
                    try:
                        self.q.get_nowait()
                    except queue.Empty:
                        pass

                try:
                    self.q.put_nowait(frame)
                except queue.Full:
                    pass

                continue

            if time.time() - last_ok_time >= self.read_timeout_sec:
                print(
                    f"[Video] Reconnecting stream: {self.stream_url or self.cam_index}"
                )
                reopened = self._reopen_capture()
                last_ok_time = time.time() if reopened else 0

            time.sleep(0.05)

    def read(self):
        if self.use_picamera:
            rgb = self.picam2.capture_array()
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            return bgr

        try:
            return self.q.get(timeout=self.read_timeout_sec)
        except queue.Empty:
            return None

    def capture(self, display: bool) -> MatLike | None:
        img = self._capture()
        cv2.waitKey(1)
        if display and img is not None:
            self.displayImg(img)
        return img

    def _capture(self):
        frame = self.read()
        if frame is None:
            return None

        resized_frame = cv2.resize(frame, (self.width, self.height))
        self.frame = resized_frame
        return resized_frame

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
        return cv2.waitKey(1) & 0xFF

    def release(self):
        self._stop_reader = True

        if hasattr(self, "_reader_thread") and self._reader_thread is not None:
            self._reader_thread.join(timeout=1.0)

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
        color: str = "#00FF00",
        thickness: int = 2,
    ) -> Any:
        font = cv2.FONT_HERSHEY_SIMPLEX
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        color_bgr = (b, g, r)

        cv2.putText(
            img,
            text,
            pos,
            font,
            scale,
            color_bgr,
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

    def progress_bar(
        self,
        img: Any,
        progress: float,
        pos: tuple[int, int] | None = None,
        size: tuple[int, int] | None = None,
        bg: str = "#222222",
        fg: str = "#2AB6B5",
        border: str = "#555555",
    ) -> Any:
        """
        Draw a horizontal progress bar on the image.
        progress: 0.0..1.0
        pos: (x, y) top-left of the bar (defaults near bottom)
        size: (w, h) size of the bar (defaults to window width)
        """

        def hex_to_bgr(h: str) -> tuple[int, int, int]:
            r = int(h[1:3], 16)
            g = int(h[3:5], 16)
            b = int(h[5:7], 16)
            return (b, g, r)

        p = max(0.0, min(1.0, float(progress)))
        if pos is None:
            pos = (10, max(0, self.height - 18))
        if size is None:
            size = (max(20, self.width - 20), 8)

        x, y = pos
        w, h = size

        # background
        cv2.rectangle(img, (x, y), (x + w, y + h), hex_to_bgr(bg), -1)
        # border
        cv2.rectangle(img, (x, y), (x + w, y + h), hex_to_bgr(border), 1)
        # fill
        fill_w = int(w * p)
        if fill_w > 0:
            cv2.rectangle(img, (x, y), (x + fill_w, y + h), hex_to_bgr(fg), -1)

        return img

    def square(
        self,
        img: Any,
        x1: int,
        y1: int,
        x2: int,
        y2: int,
        color: str = "#00FF00",
        thickness: int = 2,
        filled: bool = False,
    ) -> Any:
        """
        Draw a square/rectangle from (x1, y1) to (x2, y2).
        `color` accepts hex format like '#A10000'.
        """
        # convert hex color to BGR tuple
        r = int(color[1:3], 16)
        g = int(color[3:5], 16)
        b = int(color[5:7], 16)
        color_bgr = (b, g, r)

        if filled:
            cv2.rectangle(img, (x1, y1), (x2, y2), color_bgr, -1)
        else:
            cv2.rectangle(img, (x1, y1), (x2, y2), color_bgr, thickness)
        return img

    def _make_capture(self):
        if self.stream_url:
            if self.stream_url.startswith("rtsp://"):
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                    "rtsp_transport;tcp|stimeout;5000000|max_delay;0"
                )
            else:
                os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = (
                    "rtmp_buffer;0|timeout;5000000"
                )

            cap = cv2.VideoCapture(self.stream_url, cv2.CAP_FFMPEG)
        else:
            is_windows = platform.system().lower() == "windows"
            if is_windows:
                cap = cv2.VideoCapture(self.cam_index)
            else:
                cap = cv2.VideoCapture(self.cam_index, cv2.CAP_V4L2)

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.height)
            cap.set(cv2.CAP_PROP_FPS, 5)

        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return cap

    def _reopen_capture(self):
        with self._open_lock:
            try:
                if hasattr(self, "cap"):
                    self.cap.release()
            except Exception:
                pass

            time.sleep(self.reconnect_delay_sec)
            self.cap = self._make_capture()
            return self.cap.isOpened()

    def _start_reader_thread(self):
        self._reader_thread = threading.Thread(target=self._reader, daemon=True)
        self._reader_thread.start()
