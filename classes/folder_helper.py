import os
import shutil
import subprocess
from typing import List, Literal

from automation.path import Path


class FolderHelper:
    @staticmethod
    def parse_folder_name(path: str, type: Literal["folder", "file"] = "file") -> str:
        if type == "folder":
            return os.path.basename(os.path.dirname(path))
        else:
            return path.split("\\")[-1]

    @staticmethod
    def current_folder() -> str:
        return os.path.basename(os.getcwd())

    @staticmethod
    def create(folder_path: str):
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

    @staticmethod
    def delete(folder_path: str):
        # shutil.rmtree(folder_path)
        try:
            # Use the Windows "rmdir" command with /S to delete the folder and its contents
            subprocess.check_call(["cmd", "/c", "rmdir", "/S", "/Q", folder_path])
            print(f"Successfully deleted: {folder_path}")
        except subprocess.CalledProcessError as e:
            print(f"Error deleting folder: {folder_path}")
            print(e)

    @staticmethod
    def exists(folder_path: str) -> bool:
        return os.path.isdir(folder_path)

    @staticmethod
    def list_files(folder_path: str) -> List[str]:
        return [
            f
            for f in os.listdir(folder_path)
            if os.path.isfile(Path.join(folder_path, f))
        ]

    @staticmethod
    def list_folders(folder_path: str) -> List[str]:
        return [
            f
            for f in os.listdir(folder_path)
            if os.path.isdir(Path.join(folder_path, f))
        ]
