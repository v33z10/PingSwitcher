import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import threading
import winsound
import keyboard
import pydivert
import ctypes
import sys
import socket
import os
import webbrowser
import json

# ---------- Настройки (сохранение в JSON) ----------
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "hotkey": "ctrl+shift+c",
    "custom_sound": ""
}

def load_settings():
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                return {**DEFAULT_SETTINGS, **data}
        except Exception:
            pass
    return DEFAULT_SETTINGS.copy()

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception:
        pass

# ---------- Локализация ----------
TRANSLATIONS = {
    "en": {
        "title": "PingSwitcher v1.11 by: v33z10",
        "connected": "Connected",
        "lagging": "Lagging...",
        "auto_reconnect": "Auto-reconnect after",
        "seconds": "seconds",
        "always_on_top": "Always on top",
        "sound": "Sound",
        "status_ready": "Ready",
        "status_lagging": "Traffic blocked...",
        "status_restored": "Connection restored",
        "lang_label": "Language:",
        "time_left": "Time left: {}s",
        "no_limit": "No limit",
        "tab_main": "Main",
        "tab_settings": "Settings",
        "hotkey_label": "Hotkey:",
        "btn_apply_hk": "Apply",
        "sound_label": "Custom Sound (WAV):",
        "sound_select": "Select .wav",
        "sound_default": "Default Beep",
        "hotkey_error": "Invalid hotkey format!",
        "hotkey_success": "Hotkey updated!"
    },
    "ru": {
        "title": "PingSwitcher v1.11 by: v33z10",
        "connected": "Connected",
        "lagging": "Lagging...",
        "auto_reconnect": "Авто-переподключение через",
        "seconds": "сек",
        "always_on_top": "Поверх всех окон",
        "sound": "Звук",
        "status_ready": "Готов к работе",
        "status_lagging": "Трафик заблокирован...",
        "status_restored": "Соединение восстановлено",
        "lang_label": "Язык:",
        "time_left": "Осталось: {}с",
        "no_limit": "Без ограничений",
        "tab_main": "Главная",
        "tab_settings": "Настройки",
        "hotkey_label": "Горячая клавиша:",
        "btn_apply_hk": "Применить",
        "sound_label": "Свой звук (WAV):",
        "sound_select": "Выбрать .wav",
        "sound_default": "Стандартный",
        "hotkey_error": "Неверный формат клавиши!",
        "hotkey_success": "Клавиша обновлена!"
    }
}

# ---------- Проверка прав администратора ----------
def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def request_admin():
    if not is_admin():
        executable = sys.executable
        if executable.endswith("python.exe"):
            executable = executable.replace("python.exe", "pythonw.exe")
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", executable, f'"{os.path.abspath(sys.argv[0])}"', None, 0
        )
        sys.exit(0)

# ---------- Поток PingSwitcher ----------
class LagSwitchBlocker(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.active = False
        self.inbound_buffer = []
        self.w = None
        self._stop_event = threading.Event()
        self.lock = threading.Lock()

    def run(self):
        try:
            self.w = pydivert.WinDivert("udp")
            self.w.open()
            
            while not self._stop_event.is_set():
                try:
                    packet = self.w.recv()
                except Exception:
                    break

                with self.lock:
                    is_active = self.active

                if is_active:
                    if packet.is_outbound:
                        self.w.send(packet)
                    else:
                        self.inbound_buffer.append(packet)
                        if len(self.inbound_buffer) > 15000:
                            self.inbound_buffer.pop(0)
                else:
                    self.w.send(packet)
                    if self.inbound_buffer:
                        buffer_copy = self.inbound_buffer[:]
                        self.inbound_buffer.clear()
                        for p in buffer_copy:
                            try: self.w.send(p)
                            except: pass
        except Exception as e:
            print(f"[PingSwitcher] Ошибка: {e}")
        finally:
            if self.w:
                try: self.w.close()
                except: pass

    def wakeup(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.sendto(b'wakeup', ('8.8.8.8', 53))
            s.close()
        except: pass

    def stop(self):
        with self.lock:
            self.active = False
        self.wakeup()

    def terminate(self):
        self._stop_event.set()
        self.wakeup()

# ---------- GUI ----------
class PingSwitcherApp:
    def __init__(self, root):
        self.root = root
        # Увеличили высоту до 320, чтобы влезли все элементы и отступы
        self.root.geometry("480x320")
        self.root.resizable(False, False)
        self.root.configure(bg="#1e1e1e")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        try:
            self.root.iconbitmap(resource_path("icon.ico"))
        except Exception:
            pass

        self.settings = load_settings()
        self.current_hotkey = self.settings.get("hotkey", "ctrl+shift+c")
        
        self.auto_stop_timer = None
        self.countdown_timer = None
        self.time_left = 0

        self.lang_var = tk.StringVar(value="en")
        self.auto_reconnect_var = tk.BooleanVar(value=True)
        self.auto_seconds_var = tk.IntVar(value=10)
        self.sound_var = tk.BooleanVar(value=True)
        self.topmost_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar()
        self.countdown_var = tk.StringVar()

        self.blocker = LagSwitchBlocker()
        self.blocker.start()

        self._setup_styles()
        self._build_ui()
        self._update_language()
        self.apply_hotkey(silent=True)
        self._apply_topmost()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e1e1e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d2d", foreground="#aaaaaa", padding=[15, 5], font=("Segoe UI", 9))
        style.map("TNotebook.Tab", background=[("selected", "#1e1e1e")], foreground=[("selected", "#ffffff")])
        style.configure("TFrame", background="#1e1e1e")

    def _build_ui(self):
        # Нижняя кликабельная ссылка
        self.link_label = tk.Label(
            self.root, text="https://pingswitcher.gt.tc/",
            bg="#2d2d2d", fg="#4a90e2", font=("Segoe UI", 9, "underline"),
            cursor="hand2"
        )
        self.link_label.pack(fill="x", side="bottom")
        self.link_label.bind("<Button-1>", lambda e: webbrowser.open("https://pingswitcher.gt.tc/"))

        # Верхняя панель заголовка
        self.title_frame = tk.Frame(self.root, bg="#2d2d2d")
        self.title_frame.pack(fill="x", side="top")
        self.title_label = tk.Label(
            self.title_frame, text="PingSwitcher v1.11 by: v33z10",
            bg="#2d2d2d", fg="#cccccc", font=("Segoe UI", 10)
        )
        self.title_label.pack(pady=4)

        # --- ВКЛАДКИ ---
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(5, 5))

        # ================= Вкладка 1: Главная =================
        self.tab_main = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_main, text="Main")

        # СТАТУС (жестко прибит к низу вкладки с отступом 15px)
        self.status_label = tk.Label(
            self.tab_main, textvariable=self.status_var,
            bg="#1e1e1e", fg="#888888", font=("Segoe UI", 9)
        )
        self.status_label.pack(side="bottom", pady=5)

        # Большая кнопка
        self.toggle_btn = tk.Button(
            self.tab_main, text="Connected",
            bg="#7cb342", fg="white", font=("Segoe UI", 12, "bold"),
            activebackground="#8bc34a", activeforeground="white",
            relief="flat", bd=0, width=20, height=3, cursor="hand2",
            command=self.toggle_lag
        )
        self.toggle_btn.pack(pady=(15, 5), side="top")

        # Обратный отсчет
        self.countdown_label = tk.Label(
            self.tab_main, textvariable=self.countdown_var,
            bg="#1e1e1e", fg="#ff9800", font=("Segoe UI", 9, "bold")
        )
        self.countdown_label.pack(pady=2, side="top")

        # Флажок Auto-reconnect
        self.frame_auto = tk.Frame(self.tab_main, bg="#1e1e1e")
        self.frame_auto.pack(pady=10, side="top")

        self.auto_cb = tk.Checkbutton(
            self.frame_auto, text="Auto-reconnect", variable=self.auto_reconnect_var,
            bg="#1e1e1e", fg="white", selectcolor="#1e1e1e",
            activebackground="#1e1e1e", activeforeground="white",
            font=("Segoe UI", 10)
        )
        self.auto_cb.pack(side="left")

        self.auto_spin = tk.Spinbox(
            self.frame_auto, from_=3, to=120, textvariable=self.auto_seconds_var,
            width=4, font=("Segoe UI", 10), justify="center"
        )
        self.auto_spin.pack(side="left", padx=5)

        self.secs_label = tk.Label(self.frame_auto, text="sec", bg="#1e1e1e", fg="white", font=("Segoe UI", 10))
        self.secs_label.pack(side="left")

        # ================= Вкладка 2: Настройки =================
        self.tab_settings = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_settings, text="Settings")

        # Контейнер для общих настроек
        self.general_frame = tk.Frame(self.tab_settings, bg="#1e1e1e")
        self.general_frame.pack(fill="x", padx=20, pady=(10, 5))

        # Язык
        self.lang_frame_settings = tk.Frame(self.general_frame, bg="#1e1e1e")
        self.lang_frame_settings.pack(fill="x", pady=2)
        
        self.lang_label = tk.Label(self.lang_frame_settings, text="Language:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10))
        self.lang_label.pack(side="left")
        
        self.lang_combo = ttk.Combobox(self.lang_frame_settings, textvariable=self.lang_var, values=["en", "ru"], width=4, state="readonly")
        self.lang_combo.pack(side="right")
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._update_language())

        # Always on top
        self.topmost_cb = tk.Checkbutton(
            self.general_frame, text="Always on top", variable=self.topmost_var,
            bg="#1e1e1e", fg="white", selectcolor="#1e1e1e",
            activebackground="#1e1e1e", activeforeground="white",
            font=("Segoe UI", 10), command=self._apply_topmost
        )
        self.topmost_cb.pack(anchor="w", pady=2)

        # Sound
        self.sound_cb = tk.Checkbutton(
            self.general_frame, text="Sound", variable=self.sound_var,
            bg="#1e1e1e", fg="white", selectcolor="#1e1e1e",
            activebackground="#1e1e1e", activeforeground="white",
            font=("Segoe UI", 10)
        )
        self.sound_cb.pack(anchor="w", pady=2)

        # Разделитель
        tk.Frame(self.tab_settings, bg="#333", height=1).pack(fill="x", padx=20, pady=5)

        # Горячая клавиша
        self.hk_frame = tk.Frame(self.tab_settings, bg="#1e1e1e")
        self.hk_frame.pack(pady=5, fill="x", padx=20)
        
        self.hk_label = tk.Label(self.hk_frame, text="Hotkey:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10))
        self.hk_label.pack(side="left")
        
        self.hk_entry = tk.Entry(self.hk_frame, width=15, font=("Segoe UI", 10), justify="center")
        self.hk_entry.insert(0, self.current_hotkey)
        self.hk_entry.pack(side="left", padx=10)

        self.hk_btn = tk.Button(self.hk_frame, text="Apply", bg="#3d3d3d", fg="white", 
                                relief="flat", command=self.apply_hotkey)
        self.hk_btn.pack(side="left")

        # Разделитель
        tk.Frame(self.tab_settings, bg="#333", height=1).pack(fill="x", padx=20, pady=5)

        # Звук
        self.snd_label = tk.Label(self.tab_settings, text="Custom Sound (WAV):", bg="#1e1e1e", fg="white", font=("Segoe UI", 10))
        self.snd_label.pack(pady=(5, 5))

        self.snd_frame = tk.Frame(self.tab_settings, bg="#1e1e1e")
        self.snd_frame.pack(fill="x", padx=20)

        self.snd_btn = tk.Button(self.snd_frame, text="Select .wav", bg="#3d3d3d", fg="white", 
                                 relief="flat", command=self._select_sound)
        self.snd_btn.pack(side="left", expand=True, fill="x", padx=(0, 5))

        self.reset_snd_btn = tk.Button(self.snd_frame, text="Default Beep", bg="#3d3d3d", fg="white", 
                                       relief="flat", command=self._reset_sound)
        self.reset_snd_btn.pack(side="right", expand=True, fill="x", padx=(5, 0))

        self.snd_path_label = tk.Label(self.tab_settings, text=self._get_sound_name(), bg="#1e1e1e", fg="#888888", font=("Segoe UI", 8))
        self.snd_path_label.pack(pady=5)

    # --- Логика настроек ---
    def _get_sound_name(self):
        path = self.settings.get("custom_sound", "")
        if path and os.path.exists(path):
            return os.path.basename(path)
        return "Default (Beep)" if self.lang_var.get() == "en" else "Стандартный (Beep)"

    def _select_sound(self):
        file_path = filedialog.askopenfilename(
            title="Select Sound", 
            filetypes=[("WAV files", "*.wav")]
        )
        if file_path:
            self.settings["custom_sound"] = file_path
            save_settings(self.settings)
            self.snd_path_label.config(text=os.path.basename(file_path))

    def _reset_sound(self):
        self.settings["custom_sound"] = ""
        save_settings(self.settings)
        self.snd_path_label.config(text=self._get_sound_name())

    def apply_hotkey(self, silent=False):
        new_hotkey = self.hk_entry.get().strip().lower()
        if not new_hotkey:
            return
            
        try:
            keyboard.remove_hotkey(self.current_hotkey)
        except:
            pass

        try:
            keyboard.add_hotkey(new_hotkey, lambda: None)
            keyboard.remove_hotkey(new_hotkey)
            
            self.current_hotkey = new_hotkey
            self.settings["hotkey"] = new_hotkey
            save_settings(self.settings)
            
            keyboard.add_hotkey(self.current_hotkey, self._toggle_from_hotkey)
            self._update_language()
            
            if not silent:
                messagebox.showinfo("Success", TRANSLATIONS[self.lang_var.get()]["hotkey_success"])
        except Exception:
            if not silent:
                messagebox.showerror("Error", TRANSLATIONS[self.lang_var.get()]["hotkey_error"])
            self.hk_entry.delete(0, tk.END)
            self.hk_entry.insert(0, self.current_hotkey)

    def _update_language(self):
        lang = self.lang_var.get()
        t = TRANSLATIONS[lang]

        self.root.title(t["title"])
        
        hk_text = self.current_hotkey.upper().replace("+", " + ")
        if self.blocker.active:
            self.toggle_btn.config(text=f"{t['lagging']}\n{hk_text}")
        else:
            self.toggle_btn.config(text=f"{t['connected']}\n{hk_text}")

        self.auto_cb.config(text=t["auto_reconnect"])
        self.secs_label.config(text=t["seconds"])
        self.topmost_cb.config(text=t["always_on_top"])
        self.sound_cb.config(text=t["sound"])
        
        # Вкладки
        self.notebook.tab(0, text=t["tab_main"])
        self.notebook.tab(1, text=t["tab_settings"])
        
        # Настройки
        self.lang_label.config(text=t["lang_label"])
        self.hk_label.config(text=t["hotkey_label"])
        self.hk_btn.config(text=t["btn_apply_hk"])
        self.snd_label.config(text=t["sound_label"])
        self.snd_btn.config(text=t["sound_select"])
        self.reset_snd_btn.config(text=t["sound_default"])
        self.snd_path_label.config(text=self._get_sound_name())

        if self.blocker.active:
            self.status_var.set(t["status_lagging"])
        else:
            self.status_var.set(t["status_ready"])

        if self.countdown_timer and self.time_left > 0:
            self.countdown_var.set(t["time_left"].format(self.time_left))
        elif not self.auto_reconnect_var.get():
            self.countdown_var.set(t["no_limit"])
        else:
            self.countdown_var.set("")

    def _apply_topmost(self):
        self.root.attributes("-topmost", self.topmost_var.get())

    def _toggle_from_hotkey(self):
        self.root.after(0, self.toggle_lag)

    def _play_sound(self, start=True):
        if not self.sound_var.get():
            return
            
        custom_path = self.settings.get("custom_sound", "")
        if custom_path and os.path.exists(custom_path):
            try:
                winsound.PlaySound(custom_path, winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except:
                pass
                
        try:
            winsound.Beep(1200 if start else 400, 150)
        except: 
            pass

    def toggle_lag(self):
        if self.blocker.active:
            self.stop_lag()
        else:
            self.start_lag()

    def start_lag(self):
        if self.blocker.active:
            return

        self._play_sound(start=True)
        t = TRANSLATIONS[self.lang_var.get()]
        self.status_var.set(t["status_lagging"])
        
        hk_text = self.current_hotkey.upper().replace("+", " + ")
        self.toggle_btn.config(text=f"{t['lagging']}\n{hk_text}", bg="#e53935")
        
        with self.blocker.lock:
            self.blocker.active = True

        if self.auto_reconnect_var.get():
            self.time_left = self.auto_seconds_var.get()
            self._update_countdown()
        else:
            self.countdown_var.set(t["no_limit"])

    def stop_lag(self):
        if self.auto_stop_timer:
            self.root.after_cancel(self.auto_stop_timer)
            self.auto_stop_timer = None
        
        if self.countdown_timer:
            self.root.after_cancel(self.countdown_timer)
            self.countdown_timer = None
            
        self.time_left = 0
        self.countdown_var.set("")

        if self.blocker.active:
            self.blocker.stop()
            self._reset_ui()

    def _update_countdown(self):
        if self.time_left > 0:
            t = TRANSLATIONS[self.lang_var.get()]
            self.countdown_var.set(t["time_left"].format(self.time_left))
            self.time_left -= 1
            self.countdown_timer = self.root.after(1000, self._update_countdown)
        else:
            self.stop_lag()

    def _reset_ui(self):
        t = TRANSLATIONS[self.lang_var.get()]
        self.status_var.set(t["status_restored"])
        
        hk_text = self.current_hotkey.upper().replace("+", " + ")
        self.toggle_btn.config(text=f"{t['connected']}\n{hk_text}", bg="#7cb342")
        
        self.countdown_var.set("")
        self._play_sound(start=False)

    def on_close(self):
        try:
            keyboard.remove_hotkey(self.current_hotkey)
        except:
            pass
        self.blocker.terminate()
        self.root.destroy()

if __name__ == "__main__":
    if not is_admin():
        request_admin()

    root = tk.Tk()
    app = PingSwitcherApp(root)
    root.mainloop()
