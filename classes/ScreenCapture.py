import threading
import time
import keyboard
import numpy as np
import mss
from typing import Callable
import cv2
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt, QRect, pyqtSignal
from PyQt6.QtGui import QPainter, QPen, QBrush, QColor
import sys
from classes.folder_helper import FolderHelper


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

    def capture(self):
        with mss.mss() as sct:
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
            return frame

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
        cv2.destroyAllWindows()
        try:
            self.overlay.close()
        except Exception:
            pass
        self.overlay_app.quit()
        print("Done Capturing!")

    def loop(self, func: Callable):
        self.overlay_thread = threading.Thread(target=self._loop, args=(func,))
        self.overlay_thread.daemon = True
        self.overlay_thread.start()

        # sys.exit(self.overlay_app.exec())

    def pump_events(self):
        # Call this each iteration of your Wrapper loop
        self.overlay_app.processEvents()


class RedSquareOverlay(QMainWindow):
    quit_signal = pyqtSignal()

    def __init__(self, left=300, top=100, width=200, height=400):
        super().__init__()
        self.boundary_thickness = 8
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_NoSystemBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(1)  # Adjust transparency if needed
        self.label_height = 30

        # Define the boundary position and size
        self.boundary = QRect(
            left - self.boundary_thickness // 2,
            top - self.boundary_thickness // 2 - self.label_height,
            width + self.boundary_thickness,
            height + self.boundary_thickness,
        )
        self.setGeometry(self.boundary)
        self.pred_text = ""

    def update_text(self, text: str):
        self.pred_text = text
        self.update()

    def paintEvent(self, a0):
        #! RED BORDER
        painter = QPainter(self)
        pen = QPen(Qt.GlobalColor.red, self.boundary_thickness)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(0, self.label_height, 0, 0))

        #! YELLOW BORDER
        pen = QPen(Qt.GlobalColor.yellow, self.boundary_thickness)
        painter.setPen(pen)
        painter.drawRect(
            self.rect().adjusted(
                0,
                0,
                0,
                -self.height() + self.label_height,
            )
        )

        #! PREDICTION TEXT
        if self.pred_text:
            font = painter.font()
            font.setPointSize(14)
            font.setBold(True)
            painter.setFont(font)
            # painter.setPen(QColor(255, 255, 255))  # white text
            # painter.setBrush(QBrush(QColor(0, 0, 0, 160)))  # semi-transparent bg
            # text_rect = self.rect().adjusted(0, -30, 0, -self.height() + 30)
            # painter.drawRect(text_rect)
            # painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, self.pred_text)
            font = painter.font()
            font.setPointSize(13)
            font.setBold(True)
            painter.setFont(font)

            painter.setPen(Qt.PenStyle.NoPen)
            bg = QRect(
                self.boundary_thickness // 2,  # x
                self.boundary_thickness,  # y (just under the red border)
                self.width() - self.boundary_thickness,  # w
                self.label_height - self.boundary_thickness,  # h
            )
            painter.setBrush(QColor(20, 20, 20, 180))  # sleek semi-transparent
            painter.drawRoundedRect(bg, 0, 0)

            painter.setPen(QColor(255, 255, 255))  # white text
            painter.drawText(
                bg.adjusted(10, -2, 0, 0),
                Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                self.pred_text,
            )

    def keyPressEvent(self, a0):
        if a0.key() == Qt.Key.Key_Q:
            self.quit_signal.emit()
            # QApplication.quit()  # Quit the application
