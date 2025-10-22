import threading
import time
import keyboard
import numpy as np
import mss
from typing import Callable
import cv2
from PyQt5.QtWidgets import QApplication, QMainWindow
from PyQt5.QtCore import Qt, QRect, pyqtSignal
from PyQt5.QtGui import QPainter, QPen, QBrush, QColor
import sys
from classes.FolderHelper import FolderHelper


class ScreenCapture:
    def __init__(
        self, left: int, top: int, width: int, height: int, will_record=False
    ) -> None:
        self.left = left
        self.top = top
        self.width = width
        self.height = height
        self.will_record = will_record
        self.should_exit = False

        if self.will_record:
            fps = 20.0
            fourcc = cv2.VideoWriter_fourcc(*"XVID")

            FolderHelper.create("screen_captures")
            output_file_name = str(int(time.time() * 1000))
            output_file = f"screen_captures/{output_file_name}.avi"

            self.out = cv2.VideoWriter(
                output_file, fourcc, fps, (self.width, self.height)
            )

        #! Initialize the overlay
        self.overlay_app = QApplication(sys.argv)
        self.overlay = RedSquareOverlay(left, top, width, height)
        self.overlay.quit_signal.connect(self.cleanup)
        self.overlay.show()

        keyboard.add_hotkey("q", self._set_exit_flag)

    def _loop(self, func: Callable):
        with mss.mss() as sct:
            try:
                while not self.should_exit:
                    # Capture the screen
                    img = np.array(
                        sct.grab(
                            {
                                "top": self.top,
                                "left": self.left,
                                "width": self.width,
                                "height": self.height,
                            }
                        )
                    )
                    frame = cv2.cvtColor(img, cv2.COLOR_BGRA2BGR)
                    key = cv2.waitKey(1) & 0xFF  # Read the key press once per loop

                    func(frame)

                    # Show the capture (optional)
                    # cv2.imshow("Screen Capture", frame)

                    if key == ord("q"):  # Exit key
                        break

                    # Write the frame to the video file
                    if self.will_record:
                        self.out.write(frame)

            finally:
                self.cleanup()

    def _set_exit_flag(self):
        self.should_exit = True

    def cleanup(self):
        if self.will_record:
            self.out.release()

        cv2.destroyAllWindows()
        self.overlay_app.quit()
        print("Done Capturing!")

    def loop(self, func: Callable):
        self.overlay_thread = threading.Thread(target=self._loop, args=(func,))
        self.overlay_thread.daemon = True
        self.overlay_thread.start()

        sys.exit(self.overlay_app.exec_())


class RedSquareOverlay(QMainWindow):
    quit_signal = pyqtSignal()

    def __init__(self, left=300, top=100, width=200, height=400):
        super().__init__()
        self.boundary_thickness = 8
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WA_NoSystemBackground)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowOpacity(1)  # Adjust transparency if needed

        # Define the boundary position and size
        self.boundary = QRect(
            left - self.boundary_thickness // 2,
            top - self.boundary_thickness // 2,
            width + self.boundary_thickness,
            height + self.boundary_thickness,
        )
        self.setGeometry(self.boundary)

    def paintEvent(self, event):
        # Draw the red boundary
        painter = QPainter(self)
        pen = QPen(Qt.red, self.boundary_thickness)
        painter.setPen(pen)
        painter.drawRect(self.rect())

    def keyPressEvent(self, event):
        if event.key() == ord("Q"):  # Check if the key pressed is 'q'
            self.quit_signal.emit()
            # QApplication.quit()  # Quit the application
