import os


class Path:
    @staticmethod
    def join(*args: str) -> str:
        """
        Joins multiple path components into a single path.
        """
        return os.path.join(*args)
