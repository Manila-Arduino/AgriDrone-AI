from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class SegmentedObject:
    entity: str
    score: float
    points: List[Tuple[int, int]]
    area_percent: float
