import numpy as np
from typing import List, Sequence

from pydantic import BaseModel
from classes.Arduino import Arduino
from classes.BoxedObject import BoxedObject
from classes.CNNImage import CNNImage
from classes.OD_Custom import OD_Custom
from classes.OD_Default import OD_Default
from classes.SegmentedObject import SegmentedObject
from classes.Video import Video
from classes.Wrapper import Wrapper
from classes.Yolov11nSeg import YoloV11nSeg

MatLike = np.ndarray

# ? -------------------------------- CONSTANTS
cam_index = 0
img_width = 512
img_height = 512
input_layer_name = "input_layer_4"
output_layer_name = "output_0"

arduino_port = ""


# ? -------------------------------- CLASSES
arduino = Arduino(arduino_port)
video = Video(cam_index, img_width, img_height)
cnn = CNNImage(
    ["no_oil", "oil"],
    r"model.tflite",
    img_width,
    img_height,
    input_layer_name=input_layer_name,
    output_layer_name=output_layer_name,
)
od_default = OD_Default(0.8)
od_custom = OD_Custom(
    "detect.tflite",
    ["crop", "weed"],
    0.9,
    img_width=img_width,
    img_height=img_height,
    max_object_size_percent=0.80,
)
yolo = YoloV11nSeg(
    "plants.pt",
    [("plant", (255, 0, 0))],
    threshold=0.5,
    img_width=img_width,
    img_height=img_height,
    max_object_size_percent=1.0,
    allowed=["plant"],
)


class AdminSettings(BaseModel):
    id: str
    quasar: bool
    start_now: bool


# ? -------------------------------- VARIABLES


# ? -------------------------------- FUNCTIONS
def on_cnn_predict(predicted_class: str, confidence: float):
    # TODO 2 -------------------------------------------------
    pass


def on_od_receive(max_object: BoxedObject, results: Sequence[BoxedObject]):
    # TODO 3 ------------------------------------------------
    pass


def on_yolo_predict(max_object: SegmentedObject, results: Sequence[SegmentedObject]):
    # TODO 3 ------------------------------------------------
    pass


def on_arduino_receive(s: str):
    # TODO 3 ------------------------------------------------
    pass


# ? -------------------------------- SETUP
def setup():
    pass


# ? -------------------------------- LOOP
def loop():
    #! VIDEO
    img = video.capture(display=False)

    #! CNN
    # predicted_class, confidence = cnn.predict(img, isBatch=False)
    # print(predicted_class, confidence)
    # on_cnn_predict(predicted_class, confidence)

    #! OBJECT DETECTION
    img = od_default.detect(img, on_od_receive=on_od_receive)
    img2 = od_custom.detect(img, on_od_receive=on_od_receive)

    #! INSTANCE SEGMENTATION
    yolo.detect(img, on_yolov11n_seg_receive=on_yolo_predict)

    #! DISPLAY VIDEO
    yolo.display(img)
    video.displayImg(img)

    #! ARDUINO
    if arduino.available():
        arduino_str = arduino.read()
        print(f"Arduino received: {arduino_str}")
        on_arduino_receive(arduino_str)


# ? -------------------------------- ETC
setup()


def onExit():
    arduino.close()


Wrapper(
    loop,
    onExit=onExit,
    keyboardEvents=[
        # ["d", video.save_image],  # type: ignore
    ],
)
