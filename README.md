### MINICOMPUTER SETUP

1. Connect to WiFi
2. Make Windows Dark Mode
3. Darkreader, Adblocker extension
4. Install GIT
5. Install Python: 3.11.6
6. Generate SSH key
7. Git clone
8. `cd ai`
9. `p s`
10. `a`
11. `call utils\autostart.bat`
12. Remove display sleep
13. Remove automatic updates
14. Turn off app notifs
15. Disable apps in Task Manager -> Startup
16. TODO: Create autostart_chrome.bat {{url}}

@echo off
start "" chrome --kiosk "https://sleep-device.web.app"
exit

### MAIN LAPTOP TESTING SETUP

1. "C:\Users\ACER\AppData\Local\Programs\Python\Python311\python.exe" -m venv ./venv
   or
1. conda create --prefix ./venv python=3.11.6 -y
1. conda activate ./venv

- pip list --format=freeze --not-requir<Shed
