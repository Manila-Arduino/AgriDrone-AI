# Yolov11nSeg.py

from typing import Callable, List, Sequence, Tuple
import cv2
import numpy as np
from ultralytics import YOLO

from classes.SegmentedObject import SegmentedObject

MatLike = np.ndarray


class YoloV11nSeg:
    def __init__(
        self,
        model_path: str,
        objects: List[Tuple[str, Tuple[int, int, int]]],
        threshold: float = 0.5,
        img_width: int = 512,
        img_height: int = 512,
        max_object_size_percent: float = 0.8,
        allowed: List[str] = [],
    ) -> None:
        self.model = YOLO(model_path)
        self.objects = objects
        self.threshold = threshold
        self.img_width = img_width
        self.img_height = img_height
        self.img_area = img_width * img_height
        self.max_object_size_percent = max_object_size_percent
        self.allowed = allowed
        self.last_detections: List[SegmentedObject] = []

    def detect(
        self,
        img: MatLike,
        on_yolov11n_seg_receive: Callable[
            [SegmentedObject, Sequence[SegmentedObject]], None
        ],
    ) -> Sequence[SegmentedObject]:
        # run inference
        r = self.model.predict(
            source=img,
            conf=self.threshold,
            imgsz=(self.img_width, self.img_height),
            save=False,
            verbose=False,
        )[0]

        xyxy = r.boxes.xyxy.cpu().numpy()  # type: ignore
        scores = r.boxes.conf.cpu().numpy()  # type: ignore
        classes = r.boxes.cls.cpu().numpy().astype(int)  # type: ignore
        masks_xy = getattr(r, "masks", None)
        masks = masks_xy.xy if masks_xy and masks_xy.xy else [[] for _ in xyxy]

        detections: List[SegmentedObject] = []
        for (x1, y1, x2, y2), cls, score, polys in zip(xyxy, classes, scores, masks):
            if score < self.threshold:
                continue
            area = (x2 - x1) * (y2 - y1)
            if area / self.img_area > self.max_object_size_percent:
                continue

            label, color = self.objects[cls]
            if self.allowed and label not in self.allowed:
                continue

            if isinstance(polys, np.ndarray) and polys.ndim == 2:
                pts = polys.astype(np.int32)
                area_percent = cv2.contourArea(pts) / self.img_area
                point_list = [(int(x), int(y)) for x, y in pts]
            else:
                point_list = []
                area_percent = 0.0

            detections.append(
                SegmentedObject(
                    entity=label,
                    score=float(score),
                    points=point_list,
                    area_percent=area_percent,
                )
            )

        detections.sort(key=lambda o: o.score, reverse=True)
        if detections:
            on_yolov11n_seg_receive(detections[0], detections)
        self.last_detections = detections
        return detections

    def display(self, img: MatLike) -> MatLike:
        overlay = img.copy()
        alpha = 0.3

        for obj in self.last_detections:
            idx = [lbl for lbl, _ in self.objects].index(obj.entity)
            bgr = self.objects[idx][1][::-1]
            pts = np.array(obj.points, dtype=np.int32)
            if pts.size:
                cv2.fillPoly(overlay, [pts], bgr)
                cv2.polylines(overlay, [pts], True, bgr, 1)

                M = cv2.moments(pts)
                if M["m00"]:
                    cx, cy = int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"])
                else:
                    cx, cy = pts[:, 0].mean().astype(int), pts[:, 1].mean().astype(int)

                text = f"{obj.entity}: {int(obj.score*100)}%"
                (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
                x, y = cx - w // 2, cy + h // 2
                cv2.rectangle(
                    overlay, (x, y - h - 4), (x + w, y), (255, 255, 255), cv2.FILLED
                )
                cv2.putText(
                    overlay,
                    text,
                    (x, y - 2),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.5,
                    (0, 0, 0),
                    1,
                )

        cv2.addWeighted(overlay, alpha, img, 1 - alpha, 0, img)
        return img
