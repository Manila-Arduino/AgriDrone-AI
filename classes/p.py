from typing import Literal, Optional
from rich.console import Console

console = Console(stderr=True)


class P:

    def __init__(
        self,
        text: str,
        color: Optional[
            Literal["r", "rb", "g", "gb", "b", "bb", "c", "cb", "y", "yb", "o", "ob"]
        ] = None,
        end="\n",
    ):
        if color is None:
            console.print(text, end=end)
            return

        console.print(
            f"[{_colorMapping[color]}]{text}[/{_colorMapping[color]}]", end=end
        )


_colorMapping = {
    "r": "red",
    "rb": "red bold",
    "g": "green",
    "gb": "green bold",
    "b": "blue",
    "bb": "blue bold",
    "c": "cyan",
    "cb": "cyan bold",
    "y": "yellow",
    "yb": "yellow bold",
    "o": "orange1",
    "ob": "orange1 bold",
}
