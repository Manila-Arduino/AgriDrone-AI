from datetime import datetime
from typing import overload, Literal, Union, Optional
import re


class DH:
    # Overloads (no defaults here, and output_type is keyword-only)
    @overload
    @staticmethod
    def from_YYYY(text: Optional[str] = ...) -> str: ...
    @overload
    @staticmethod
    def from_YYYY(text: Optional[str], *, output_type: Literal["string"]) -> str: ...
    @overload
    @staticmethod
    def from_YYYY(text: Optional[str], *, output_type: Literal["Date"]) -> datetime: ...

    @staticmethod
    def from_YYYY(
        text: Optional[str] = None,
        *,
        output_type: Literal["string", "Date"] = "string",
    ) -> Union[str, datetime]:
        if not text:
            return ""

        m = re.match(r"^(\d{4})_(\d{2})_(\d{2})_(\d{2})_(\d{2})_(\d{2})$", text)
        if not m:
            raise ValueError("Invalid format. Expected YYYY_MM_DD_HH_MM_SS")

        y, mo, d, h, mi, s = map(int, m.groups())
        try:
            date = datetime(y, mo, d, h, mi, s)
        except ValueError:
            return "N/A"

        if output_type == "Date":
            return date
        return date.strftime("%b %d, %Y - %I:%M %p")

    @staticmethod
    def to_YYYY(date: Optional[datetime] = None) -> str:
        if not date:
            date = datetime.now()
        return date.strftime("%Y_%m_%d_%H_%M_%S")
