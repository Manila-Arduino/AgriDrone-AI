import os
from dotenv import load_dotenv

from classes.p import P

load_dotenv()

from classes.ClassificationObject import ClassificationObject

from classes.Yolov11nCls import Yolov11nCls
from classes.ScreenCapture import ScreenCapture

import numpy as np
from typing import List, Optional, Sequence
from pydantic import BaseModel
from classes.Wrapper import Wrapper
import logging

logging.getLogger("ultralytics").setLevel(logging.ERROR)

MatLike = np.ndarray

# ? -------------------------------- CONSTANTS
cam_index = 0

input_layer_name = "input_layer_4"
output_layer_name = "output_0"

left = int(os.getenv("left", 700))
top = int(os.getenv("top", 200))
width = int(os.getenv("width", 400))
height = int(os.getenv("height", 800))
img_width = width
img_height = height

# ? -------------------------------- CLASSES
screen_capture = ScreenCapture(left, top, width, height, will_record=False)


yolo = Yolov11nCls(
    "best.pt",
    [
        "Asian Corn Border worm",
        "Ear rot Grade 0",
        "Ear rot Grade 1",
        "Ear rot Grade 2",
        "Ear rot Grade 3",
        "Fall Armyworm",
        "Healthy",
        "Yellow Paint with black spots",
    ],
    threshold=0.0,
    img_width=img_width,
    img_height=img_height,
)

# ? -------------------------------- VARIABLES


# ? -------------------------------- FUNCTIONS


def on_yolov11n_cls_receive(prediction: Optional[ClassificationObject]) -> None:
    if prediction is None:
        return

    screen_capture.overlay.update_text(f"{prediction.entity} ({prediction.score:.2f})")
    P(f"CLS: ", "g", end="")
    P(f"{prediction.entity}, {prediction.score:.2f}")


# ? -------------------------------- SETUP
def setup():
    pass


# ? -------------------------------- LOOP
def loop():
    #! VIDEO
    img = screen_capture.capture()

    #! YOLO IMAGE CLASSIFICATION
    yolo.detect(img, on_yolov11n_cls_receive=on_yolov11n_cls_receive)

    #! DISPLAY LABEL
    # yolo.display(img)

    #! PROCESS EVENTS
    screen_capture.pump_events()


# ? -------------------------------- ETC
setup()


def onExit():
    pass


Wrapper(
    loop,
    onExit=onExit,
    keyboardEvents=[
        ("q", screen_capture.cleanup),
        # ("d", video.save_image),  # type: ignore
    ],
)
