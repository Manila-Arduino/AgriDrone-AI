# Yolov11nCls.py — Top-1 only
from typing import Callable, List, Optional
import cv2
import numpy as np
from ultralytics import YOLO
from classes.ClassificationObject import ClassificationObject

MatLike = np.ndarray


class Yolov11nCls:
    def __init__(
        self,
        model_path: str,
        objects: List[str],
        threshold: float = 0.0,
        img_width: int = 224,
        img_height: int = 224,
    ) -> None:
        self.model = YOLO(model_path)
        self.objects = objects
        self.threshold = float(threshold)
        self.img_width = int(img_width)
        self.img_height = int(img_height)
        self.last_prediction: Optional[ClassificationObject] = None

    def detect(
        self,
        img: MatLike,
        on_yolov11n_cls_receive: Callable[[Optional[ClassificationObject]], None],
    ) -> None:
        r = self.model.predict(
            source=img,
            imgsz=(self.img_width, self.img_height),
            save=False,
            verbose=False,
        )[0]

        # No probabilities → no prediction
        if getattr(r, "probs", None) is None:
            self.last_prediction = None
            on_yolov11n_cls_receive(None)
            return

        # names = r.names  # index -> class name

        # Prefer built-ins if present, else fallback to argmax
        try:
            idx = int(r.probs.top1)
            score = float(r.probs.top1conf)
        except Exception:
            p = r.probs.data.detach().cpu().numpy().ravel()
            idx = int(p.argmax())
            score = float(p[idx])

        if score < self.threshold:
            self.last_prediction = None
            on_yolov11n_cls_receive(None)
            return

        pred = ClassificationObject(entity=str(self.objects[idx]), score=score)
        self.last_prediction = pred
        on_yolov11n_cls_receive(pred)

    def display(self, img: MatLike) -> MatLike:
        """Draw a single Top-1 label (no colors)."""
        if not self.last_prediction:
            return img

        overlay = img.copy()
        text = f"{self.last_prediction.entity}: {self.last_prediction.score*100:.1f}%"
        (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)

        x, y = 10, 28
        cv2.rectangle(
            overlay, (x, y - h - 8), (x + w + 12, y + 6), (255, 255, 255), cv2.FILLED
        )
        cv2.rectangle(overlay, (x, y - h - 8), (x + w + 12, y + 6), (0, 0, 0), 1)
        cv2.putText(
            overlay,
            text,
            (x + 6, y - 2),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 0, 0),
            1,
            cv2.LINE_AA,
        )

        out = img.copy()
        cv2.addWeighted(overlay, 0.25, out, 0.75, 0, out)
        return out
