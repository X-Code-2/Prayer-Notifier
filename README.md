# Prayer Notifier (GUI)

A lightweight desktop application that fetches real prayer times online and reminds you before each prayer with a clear notification and customizable adhan audio.  
The program comes with a modern GUI, beautiful colored buttons, countdown timers, progress bars, tray-icon minimization, and smooth background operation.

This tool was converted into an executable (`.exe`) using PyInstaller so it can run on Windows without requiring Python to be installed. You can publish the EXE along with the source code safely.

---

## ✨ Features

### ✔ Real-time Prayer Times
The app automatically fetches prayer times from **TimesPrayer.com** and updates continuously.

### ✔ Pre-prayer Notification
Five minutes before the next prayer, the app sends:
- A Windows toast notification  
- A preview of the adhan sound

### ✔ Beautiful Modern GUI
The interface includes:
- Dark theme with clean cards  
- Big prayer countdown timer  
- Progress bar showing how close the next prayer is  
- Status indicator (Running / Stopped)

### ✔ Custom Adhan Sound
You can choose your own audio file (`.mp3` or `.wav`) to play as the reminder.

### ✔ System Tray Support
Minimizing the window hides the app into the Windows system tray, where you can:
- Restore the app  
- Quit directly  

### ✔ Background Worker
A dedicated background thread constantly checks upcoming prayer times without freezing the interface.

---

## 📦 EXE Build Instructions

If you want to generate the `.exe` version, use **PyInstaller** with these options:

```bash
pyinstaller --noconsole --onefile --add-data "sound/prayer_notifier.mp3;sound" --collect-all win10toast praytimes.py
```
# 📁 File Overview
- praytimes.py

- Main application file that includes:

- Fetching prayer times

- GUI creation with Tkinter

- Windows tray integration

- Background threading

- Audio playback via Pygame

- Toast notifications

- The code is fully self-contained and safe to ship inside a repository.

# 🛠 Requirements (for source users)

- If running from source instead of EXE, install:

```bash
pip install requests bs4 lxml pygame pystray pillow win10toast
```
# 📷 Screenshot

<img width="652" height="490" alt="image" src="https://github.com/user-attachments/assets/a3373cb3-c04e-446e-9a92-ed12752475ae" />

# 📜 License

Feel free to modify and use the project. Attribution is appreciated but not required.

# 🙏 About

A simple, elegant reminder tool made to help you stay aware of prayer times without distraction.
