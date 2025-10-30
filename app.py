from datetime import datetime, timezone
import math
import os
import random
from dotenv import load_dotenv

from classes.firebase_helper import Firebase
from classes.p import P

load_dotenv()

from classes.ClassificationObject import ClassificationObject

from classes.Yolov11nCls import Yolov11nCls
from classes.ScreenCapture import ScreenCapture

import numpy as np
from typing import List, Literal, Optional, Sequence, Tuple
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
firebase = Firebase("credentials.json", use_storage=False, use_firestore=True)


class DataBox(BaseModel):
    class_str: str
    norm_x_center: float
    norm_y_center: float
    norm_width: float
    norm_height: float


class DataBoxes(BaseModel):
    id: Literal["boxes"]
    boxes: List[DataBox]


# ? -------------------------------- VARIABLES
will_save = False
img: Optional[MatLike] = None


# ? -------------------------------- FUNCTIONS
def save_box() -> None:
    global will_save
    will_save = True


def _to_edges(xc: float, yc: float, w: float, h: float):
    half_w, half_h = w / 2.0, h / 2.0
    return (
        xc - half_w,
        yc - half_h,
        xc + half_w,
        yc + half_h,
    )  # (xmin, ymin, xmax, ymax)


def _overlaps(a, b) -> bool:
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    return not (ax2 <= bx1 or bx2 <= ax1 or ay2 <= by1 or by2 <= ay1)


def generate_box(
    boxes: List[DataBox],
    min_area: float = 0.02,
    max_area: float = 0.10,
    max_tries: int = 5000,
    label: str = "Healthy",
) -> List[DataBox]:
    """
    Generate one random YOLO-format box (normalized xc,yc,w,h in [0,1]) that:
      - has area in [min_area, max_area], and
      - does not overlap with any existing box in `boxes`.

    Returns a new list with the appended DataBox.
    Raises ValueError if no valid box is found after `max_tries`.
    """
    existing_edges = [
        _to_edges(b.norm_x_center, b.norm_y_center, b.norm_width, b.norm_height)
        for b in boxes
    ]

    for _ in range(max_tries):
        A = random.uniform(min_area, max_area)
        r = math.exp(
            random.uniform(math.log(0.5), math.log(2.0))
        )  # aspect ratio ~[0.5, 2.0]
        w = math.sqrt(A * r)
        h = A / w

        if w >= 1.0 or h >= 1.0:
            continue

        xc = random.uniform(w / 2.0, 1.0 - w / 2.0)
        yc = random.uniform(h / 2.0, 1.0 - h / 2.0)

        new_edges = _to_edges(xc, yc, w, h)
        if any(_overlaps(new_edges, e) for e in existing_edges):
            continue

        return boxes + [
            DataBox(
                class_str=label,
                norm_x_center=xc,
                norm_y_center=yc,
                norm_width=w,
                norm_height=h,
            )
        ]

    P("Failed to generate non-overlapping box", "r")
    return boxes


def on_yolov11n_cls_receive(prediction: Optional[ClassificationObject]) -> None:
    global will_save, img

    if prediction is None:
        return

    screen_capture.overlay.update_text(f"{prediction.entity} ({prediction.score:.2f})")
    P(f"CLS: ", "g", end="")
    P(f"{prediction.entity}, {prediction.score:.2f}")

    if will_save:
        will_save = False
        data_boxes = firebase.read_firestore("data/boxes", DataBoxes)

        if data_boxes is None:
            data_boxes = DataBoxes(id="boxes", boxes=[])

        boxes = generate_box(data_boxes.boxes, label=prediction.entity)
        firebase.write_firestore(
            f"data/boxes",
            DataBoxes(
                id="boxes",
                boxes=boxes,
            ),
        )


# ? -------------------------------- SETUP
def setup():
    pass


# ? -------------------------------- LOOP
def loop():
    global img

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
        ("s", save_box),
        ("q", screen_capture.cleanup),
        # ("d", video.save_image),  # type: ignore
    ],
)
