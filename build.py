import subprocess

from automation.file_helper import FileHelper

TITLE = "Slash And Burn"


def main():
    subprocess.run(
        # --noconsole
        rf'pyinstaller --noconsole -F -w --add-data ".env;." --add-data="assets\\*.png;assets" --add-data="*.pt;." --add-data="credentials.json;." --icon=assets\\pyinstaller.ico app.py',
        shell=True,
    )
    FileHelper.move("dist/app.exe", f"{TITLE}.exe")


if __name__ == "__main__":
    main()
