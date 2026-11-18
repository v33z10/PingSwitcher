# ⚡ PingSwitcher

![Version](https://img.shields.io/badge/version-1.11-brightgreen)
![Platform](https://img.shields.io/badge/platform-Windows-blue)
![Python](https://img.shields.io/badge/python-3.8%2B-yellow)
![License](https://img.shields.io/badge/license-MIT-blue)

**PingSwitcher** is a sleek and powerful network traffic manipulator (Lag Switch) for Windows, designed with gamers in mind. It allows you to instantly freeze incoming network packets while keeping your outgoing actions (like shots or movement) active on the server. 

Inspired by classic lag switches, this tool features a modern dark UI, global hotkeys, and fully customizable settings.

---

## ✨ Features

- **Smart UDP Buffering:** Outbound packets go through instantly, while inbound packets are buffered. This means your shots register, but enemies freeze on your screen.
- **Modern Dark UI:** Built with a clean, compact Tkinter interface featuring tabs and dark mode.
- **Global Hotkey:** Toggle the lag switch from anywhere (default: `Ctrl + Shift + C`). You can change it to any combination.
- **Custom Sounds:** Set your own `.wav` file to play when the lag switch activates or deactivates, or use the default beep.
- **Auto-Disconnect:** Set a timer (in seconds) for the lag to automatically turn off and flush the buffered packets.
- **Always on Top:** Keep the GUI visible above your game window.
- **Bilingual:** Full support for English and Russian languages.

---

## 🚀 How to Use

1. **Download:** Go to the [Releases](../../releases) tab and download the latest `PingSwitcher.exe`.
2. **Run as Administrator:** The program **requires administrator privileges** to intercept network packets using WinDivert. Windows will prompt you for this (UAC).
3. **Configure:** Go to the "Settings" tab to change your hotkey, select a custom sound, or reset to default.
4. **Activate:** Press the big green button or use your hotkey. The button will turn red. When the timer runs out or you press it again, the connection restores, and all buffered packets are sent simultaneously.

---

## ⚠️ Disclaimer & Anti-Cheat Warning

**USE AT YOUR OWN RISK.**

This tool uses **WinDivert** to intercept network traffic, which is why some antivirus software (including Windows Defender) or game anti-cheat systems (like Easy Anti-Cheat or BattlEye) may flag or block it. 

- This project was created for **educational purposes** to demonstrate network packet manipulation.
- Using lag switches in online multiplayer games usually violates the **Terms of Service** of those games and can result in permanent bans.
- The author (`v33z10`) is not responsible for any consequences, bans, or damages resulting from the use of this software.

---

## 🛠️ Build from Source

If you want to build the `.exe` yourself:

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install pydivert keyboard pyinstaller pillow
