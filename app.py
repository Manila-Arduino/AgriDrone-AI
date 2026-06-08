from datetime import datetime, timezone
import math
import os
import random
from dotenv import load_dotenv

from classes.DH import DH
from classes.firebase_helper import Firebase
from classes.p import P
import socket

load_dotenv()

from classes.ClassificationObject import ClassificationObject

from classes.Yolov11nCls import Yolov11nCls
from classes.ScreenCapture import ScreenCapture

import numpy as np
from typing import List, Literal, Optional, Sequence, Tuple
from pydantic import BaseModel
from classes.Wrapper import Wrapper
import logging
from classes.Video import Video

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

# input_source = "screen"
input_source = "video"
TESTING = True


# ? -------------------------------- CLASSES
def get_ip_default_route() -> str:
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))  # no packets actually sent
        return s.getsockname()[0]
    finally:
        s.close()


if input_source == "screen":  # type: ignore
    left = int(os.getenv("left", 700))
    top = int(os.getenv("top", 200))
    width = int(os.getenv("width", 400))
    height = int(os.getenv("height", 800))

    img_width = width
    img_height = height

    capture_source = ScreenCapture(left, top, width, height, will_record=False)

elif input_source == "video":  # type: ignore
    cam_index = int(os.getenv("CAM_INDEX", 0))
    width = int(os.getenv("VIDEO_WIDTH", 1280))
    height = int(os.getenv("VIDEO_HEIGHT", 720))
    stream_url = os.getenv("STREAM_URL", "")

    img_width = width
    img_height = height

    if TESTING:
        capture_source = Video(
            cam_index=cam_index,
            width=img_width,
            height=img_height,
        )
    else:
        capture_source = Video(
            cam_index=cam_index,
            width=img_width,
            height=img_height,
            stream_url=f"rtmp://{get_ip_default_route()}/live/key",
        )


else:
    raise ValueError("INPUT_SOURCE must be either 'screen' or 'video'")

# screen_capture = ScreenCapture(left, top, width, height, will_record=False)


yolo = Yolov11nCls(
    "best.pt",
    [
        "Asian Corn Borer worm",
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
firebase = Firebase(
    "credentials.json",
    use_storage=True,
    use_firestore=True,
    storage_bucket="agri-drone-pole.firebasestorage.app",
)


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

    if input_source == "screen":
        capture_source.overlay.update_text(
            f"{prediction.entity} ({prediction.score:.2f})"
        )

    P(f"CLS: ", "g", end="")
    P(f"{prediction.entity}, {prediction.score:.2f}")

    if will_save:
        will_save = False

        P("SAVE: reading firestore...", "y")
        data_boxes = firebase.read_firestore("data/boxes", DataBoxes)
        P("SAVE: read done", "g")

        if data_boxes is None:
            data_boxes = DataBoxes(id="boxes", boxes=[])

        P("SAVE: generating box...", "y")
        boxes = generate_box(data_boxes.boxes, label=prediction.entity)
        P("SAVE: writing firestore...", "y")

        firebase.write_firestore(
            "data/boxes",
            DataBoxes(id="boxes", boxes=boxes),
        )

        #! SAVE IMAGE
        P("SAVE: capturing image...", "y")
        local_img_filename = f"temp_drone_img"
        id = DH.to_YYYY()
        firebase_img_path = rf"pictures/{id}.jpg"
        capture_source.save_image(local_img_filename)
        # save to firebase storage and get public URL
        img_url = firebase.upload_storage(
            f"captures/{local_img_filename}.jpg", firebase_img_path
        )
        P(f"SAVE: image uploaded to {img_url}", "g")
        firebase.write_firestore(
            f"images/{id}",
            {"id": id, "url": img_url, "timestamp": datetime.now(timezone.utc)},
        )
        P(f"SAVE: firestore updated with image metadata", "g")

        P("SAVE: write done", "g")


# ? -------------------------------- SETUP
def setup():
    pass


# ? -------------------------------- LOOP
def loop():
    global img

    if input_source == "screen":
        img = capture_source.capture()  # type: ignore
    else:
        img = capture_source.capture(display=False)  # type: ignore

    if img is None:
        return

    yolo.detect(img, on_yolov11n_cls_receive=on_yolov11n_cls_receive)

    if input_source == "video":
        img = yolo.display(img)
        capture_source.displayImg(img)

    if input_source == "screen":
        capture_source.pump_events()


# ? -------------------------------- ETC
setup()


def onExit():
    if input_source == "screen":
        capture_source.cleanup()
    else:
        capture_source.release()


Wrapper(
    loop,
    onExit=onExit,
    keyboardEvents=[
        ("s", save_box),
        ("q", onExit),
        # ("d", video.save_image),  # type: ignore
    ],
)
