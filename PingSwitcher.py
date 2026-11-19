import tkinter as tk
from tkinter import messagebox, ttk, filedialog
import threading
import winsound
import keyboard
import pydivert
import ctypes
import ctypes.wintypes
import sys
import socket
import os
import webbrowser
import json
import pygame
import subprocess

# ---------- Инициализация Аудио ----------
try:
    pygame.mixer.init()
except Exception as e:
    print(f"Audio init error: {e}")

# ---------- Настройки (сохранение в JSON) ----------
SETTINGS_FILE = "settings.json"
DEFAULT_SETTINGS = {
    "hotkey": "ctrl+shift+c",
    "on_sound": "",
    "off_sound": "",
    "play_on": True,
    "play_off": True
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

# ---------- Темная тема окна Windows ----------
def set_dark_title_bar(window):
    try:
        window.update()
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        set_window_attribute = ctypes.windll.dwmapi.DwmSetWindowAttribute
        get_parent = ctypes.windll.user32.GetParent
        hwnd = get_parent(window.winfo_id())
        value = ctypes.c_int(2)
        set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ctypes.byref(value), ctypes.sizeof(value))
    except Exception:
        pass

# ---------- Локализация ----------
TRANSLATIONS = {
    "en": {
        "title": "PingSwitcher v1.12 by: v33z10",
        "start_btn": "Start",
        "stop_btn": "Stop",
        "auto_reconnect": "Auto-reconnect after",
        "seconds": "seconds",
        "always_on_top": "Always on top",
        "status_ready": "Ready",
        "status_lagging": "Traffic blocked...",
        "status_restored": "Connection restored",
        "lang_label": "Language:",
        "time_left": "Time left: {}s",
        "no_limit": "No limit",
        "tab_main": "Main",
        "tab_settings": "Settings",
        "hotkey_label": "Start Hotkey:",
        "btn_apply_hk": "Apply",
        "hotkey_error": "Invalid hotkey format!",
        "hotkey_success": "Hotkey updated!",
        "sound_on": "Enable ON sound",
        "sound_off": "Enable OFF sound",
        "sound_on_file": "Sound on Start:",
        "sound_off_file": "Sound on Stop:",
        "select_file": "Select Audio",
        "err_filter": "WinDivert Error",
        "fix_btn": "🛠 Fix Program (WinDivert)",
        "fix_title": "Fix Applied",
        "fix_success": "WinDivert services have been stopped and cleared.\nPlease restart your PC or try starting again."
    },
    "ru": {
        "title": "PingSwitcher v1.12 by: v33z10",
        "start_btn": "Запустить",
        "stop_btn": "Остановить",
        "auto_reconnect": "Авто-переподключение через",
        "seconds": "сек",
        "always_on_top": "Поверх всех окон",
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
        "hotkey_error": "Неверный формат клавиши!",
        "hotkey_success": "Клавиша обновлена!",
        "sound_on": "Включить звук при старте",
        "sound_off": "Включить звук при стопе",
        "sound_on_file": "Звук запуска:",
        "sound_off_file": "Звук остановки:",
        "select_file": "Выбрать аудио",
        "err_filter": "Ошибка WinDivert",
        "fix_btn": "🛠 Исправить программу",
        "fix_title": "Исправление применено",
        "fix_success": "Службы WinDivert остановлены и очищены.\nПожалуйста, перезагрузите ПК или попробуйте запустить снова."
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
    def __init__(self, w):
        super().__init__(daemon=True)
        self.w = w
        self.inbound_buffer = []
        self._stop_event = threading.Event()
        self.active = True

    def run(self):
        try:
            while not self._stop_event.is_set():
                try:
                    packet = self.w.recv()
                except Exception:
                    break

                if packet.is_outbound:
                    # Исходящие (ваши выстрелы) уходят моментально
                    self.w.send(packet)
                else:
                    # Входящие (урон, смерть) задерживаются в буфере
                    self.inbound_buffer.append(packet)
                    if len(self.inbound_buffer) > 15000:
                        self.inbound_buffer.pop(0)
        except Exception as e:
            print(f"[PingSwitcher] Ошибка WinDivert: {e}")
        finally:
            self.active = False
            # При остановке выплевываем весь накопленный буфер
            if self.inbound_buffer:
                for p in self.inbound_buffer:
                    try: self.w.send(p)
                    except: pass
                self.inbound_buffer.clear()
            try: self.w.close()
            except: pass

    def stop(self):
        self._stop_event.set()
        try:
            self.w.close()
        except: pass

# ---------- Класс для прокручиваемого фрейма ----------
class ScrollableFrame(ttk.Frame):
    def __init__(self, container, *args, **kwargs):
        super().__init__(container, *args, **kwargs)
        self.canvas = tk.Canvas(self, bg="#1e1e1e", highlightthickness=0)
        scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.scrollable_frame = tk.Frame(self.canvas, bg="#1e1e1e")

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        self.canvas.bind("<Configure>", lambda e: self.canvas.itemconfig(self.canvas_window, width=e.width))

        self.canvas.configure(yscrollcommand=scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")

# ---------- GUI ----------
class PingSwitcherApp:
    def __init__(self, root):
        self.root = root
        self.root.geometry("480x380")
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
        self.blocker = None
        self.is_running = False

        self.lang_var = tk.StringVar(value="en")
        self.auto_reconnect_var = tk.BooleanVar(value=True)
        self.auto_seconds_var = tk.IntVar(value=10)
        self.topmost_var = tk.BooleanVar(value=False)
        self.status_var = tk.StringVar()
        self.countdown_var = tk.StringVar()
        
        self.play_on_var = tk.BooleanVar(value=self.settings.get("play_on", True))
        self.play_off_var = tk.BooleanVar(value=self.settings.get("play_off", True))

        self._setup_styles()
        self._build_ui()
        self._update_language()
        self.apply_hotkey(silent=True)
        self._apply_topmost()
        
        set_dark_title_bar(self.root)

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#1e1e1e", borderwidth=0)
        style.configure("TNotebook.Tab", background="#2d2d2d", foreground="#aaaaaa", padding=[15, 5], font=("Segoe UI", 9))
        style.map("TNotebook.Tab", background=[("selected", "#1e1e1e")], foreground=[("selected", "#ffffff")])
        style.configure("TFrame", background="#1e1e1e")
        style.configure("TScrollbar", background="#2d2d2d", troughcolor="#1e1e1e", borderwidth=0)

    def _build_ui(self):
        self.link_label = tk.Label(
            self.root, text="https://pingswitcher.gt.tc/",
            bg="#2d2d2d", fg="#4a90e2", font=("Segoe UI", 9, "underline"),
            cursor="hand2"
        )
        self.link_label.pack(fill="x", side="bottom")
        self.link_label.bind("<Button-1>", lambda e: webbrowser.open("https://pingswitcher.gt.tc/"))

        self.title_frame = tk.Frame(self.root, bg="#2d2d2d")
        self.title_frame.pack(fill="x", side="top")
        self.title_label = tk.Label(
            self.title_frame, text="PingSwitcher v1.12 by: v33z10",
            bg="#2d2d2d", fg="#cccccc", font=("Segoe UI", 10)
        )
        self.title_label.pack(pady=4)

        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=10, pady=(5, 5))

        # ================= Вкладка 1: Главная =================
        self.tab_main = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_main, text="Main")

        self.status_label = tk.Label(
            self.tab_main, textvariable=self.status_var,
            bg="#1e1e1e", fg="#888888", font=("Segoe UI", 9)
        )
        self.status_label.pack(side="bottom", pady=5)

        # Кнопка Старт/Стоп (Canvas)
        self.btn_canvas = tk.Canvas(self.tab_main, width=280, height=80, bg="#1e1e1e", highlightthickness=0)
        self.btn_canvas.pack(pady=(20, 5))
        
        self.btn_rect = self._create_rounded_rect(5, 5, 275, 75, radius=20, fill="#7cb342")
        self.btn_text_top = self.btn_canvas.create_text(140, 30, text="Start", fill="white", font=("Segoe UI", 14, "bold"))
        self.btn_text_bot = self.btn_canvas.create_text(140, 55, text="CTRL + SHIFT + C", fill="white", font=("Segoe UI", 9))
        
        self.btn_canvas.tag_bind(self.btn_rect, "<Button-1>", self._on_btn_click)
        self.btn_canvas.tag_bind(self.btn_text_top, "<Button-1>", self._on_btn_click)
        self.btn_canvas.tag_bind(self.btn_text_bot, "<Button-1>", self._on_btn_click)

        self.countdown_label = tk.Label(
            self.tab_main, textvariable=self.countdown_var,
            bg="#1e1e1e", fg="#ff9800", font=("Segoe UI", 9, "bold")
        )
        self.countdown_label.pack(pady=5)

        self.frame_auto = tk.Frame(self.tab_main, bg="#1e1e1e")
        self.frame_auto.pack(pady=10)

        self.auto_cb = tk.Checkbutton(
            self.frame_auto, text="Auto-reconnect", variable=self.auto_reconnect_var,
            bg="#1e1e1e", fg="white", selectcolor="#1e1e1e",
            activebackground="#1e1e1e", activeforeground="white", font=("Segoe UI", 10)
        )
        self.auto_cb.pack(side="left", padx=3)

        self.auto_spin = tk.Spinbox(
            self.frame_auto, from_=3, to=120, textvariable=self.auto_seconds_var,
            width=4, font=("Segoe UI", 10), justify="center"
        )
        self.auto_spin.pack(side="left", padx=3)

        self.secs_label = tk.Label(self.frame_auto, text="sec", bg="#1e1e1e", fg="white", font=("Segoe UI", 10))
        self.secs_label.pack(side="left", padx=3)

        # ================= Вкладка 2: Настройки =================
        self.tab_settings = ttk.Frame(self.notebook, style="TFrame")
        self.notebook.add(self.tab_settings, text="Settings")
        
        self.scroll_frame = ScrollableFrame(self.tab_settings)
        self.scroll_frame.pack(fill="both", expand=True)
        self.content_frame = self.scroll_frame.scrollable_frame

        # --- Язык ---
        self.lang_frame = tk.Frame(self.content_frame, bg="#1e1e1e")
        self.lang_frame.pack(fill="x", padx=10, pady=(10, 5))
        self.lang_label = tk.Label(self.lang_frame, text="Language:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10))
        self.lang_label.pack(side="left")
        self.lang_combo = ttk.Combobox(self.lang_frame, textvariable=self.lang_var, values=["en", "ru"], width=5, state="readonly")
        self.lang_combo.pack(side="right", padx=10)
        self.lang_combo.bind("<<ComboboxSelected>>", lambda e: self._update_language())

        # --- Горячая клавиша ---
        self.hk_frame = tk.Frame(self.content_frame, bg="#1e1e1e")
        self.hk_frame.pack(fill="x", padx=10, pady=5)
        
        self.hk_label = tk.Label(self.hk_frame, text="Hotkey:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10))
        self.hk_label.pack(side="left")
        self.hk_entry = tk.Entry(self.hk_frame, width=15, font=("Segoe UI", 10), justify="center", bg="#2d2d2d", fg="white", relief="flat")
        self.hk_entry.insert(0, self.current_hotkey)
        self.hk_entry.pack(side="left", padx=10)

        self.hk_btn = tk.Button(self.hk_frame, text="Apply", bg="#3d3d3d", fg="white", relief="flat", command=self.apply_hotkey)
        self.hk_btn.pack(side="right")

        # --- Общие настройки ---
        self.topmost_cb = tk.Checkbutton(
            self.content_frame, text="Always on top", variable=self.topmost_var,
            bg="#1e1e1e", fg="white", selectcolor="#1e1e1e",
            activebackground="#1e1e1e", activeforeground="white",
            font=("Segoe UI", 10), command=self._apply_topmost
        )
        self.topmost_cb.pack(anchor="w", padx=10, pady=5)

        tk.Frame(self.content_frame, bg="#333", height=1).pack(fill="x", padx=10, pady=5)

        # --- Улучшенные настройки звука ---
        self.snd_title = tk.Label(self.content_frame, text="Sound settings:", bg="#1e1e1e", fg="white", font=("Segoe UI", 10, "bold"))
        self.snd_title.pack(anchor="w", padx=10, pady=(5, 2))

        self.on_cb = tk.Checkbutton(self.content_frame, text="Enable ON sound", variable=self.play_on_var, 
                                    bg="#1e1e1e", fg="white", selectcolor="#1e1e1e", activebackground="#1e1e1e",
                                    activeforeground="white", font=("Segoe UI", 9), command=self._save_sound_settings)
        self.on_cb.pack(anchor="w", padx=10)

        self.on_file_frame = tk.Frame(self.content_frame, bg="#1e1e1e")
        self.on_file_frame.pack(fill="x", padx=20, pady=2)
        self.on_label = tk.Label(self.on_file_frame, text="Sound on Start:", bg="#1e1e1e", fg="#aaaaaa", font=("Segoe UI", 9))
        self.on_label.pack(side="left")
        self.on_btn = tk.Button(self.on_file_frame, text="Select Audio", bg="#3d3d3d", fg="white", relief="flat", width=12, command=lambda: self._select_sound("on"))
        self.on_btn.pack(side="right")

        self.off_cb = tk.Checkbutton(self.content_frame, text="Enable OFF sound", variable=self.play_off_var, 
                                     bg="#1e1e1e", fg="white", selectcolor="#1e1e1e", activebackground="#1e1e1e",
                                     activeforeground="white", font=("Segoe UI", 9), command=self._save_sound_settings)
        self.off_cb.pack(anchor="w", padx=10, pady=(5, 0))

        self.off_file_frame = tk.Frame(self.content_frame, bg="#1e1e1e")
        self.off_file_frame.pack(fill="x", padx=20, pady=2)
        self.off_label = tk.Label(self.off_file_frame, text="Sound on Stop:", bg="#1e1e1e", fg="#aaaaaa", font=("Segoe UI", 9))
        self.off_label.pack(side="left")
        self.off_btn = tk.Button(self.off_file_frame, text="Select Audio", bg="#3d3d3d", fg="white", relief="flat", width=12, command=lambda: self._select_sound("off"))
        self.off_btn.pack(side="right")
        
        self.snd_path_label = tk.Label(self.content_frame, text="", bg="#1e1e1e", fg="#888888", font=("Segoe UI", 8), wraplength=380)
        self.snd_path_label.pack(pady=5)

        # --- Кнопка исправления (Fix) ---
        tk.Frame(self.content_frame, bg="#333", height=1).pack(fill="x", padx=10, pady=10)
        self.fix_btn = tk.Button(
            self.content_frame, text="🛠 Fix Program (WinDivert)",
            bg="#d32f2f", fg="white", font=("Segoe UI", 10, "bold"),
            activebackground="#b71c1c", activeforeground="white",
            relief="flat", cursor="hand2", command=self.fix_program
        )
        self.fix_btn.pack(pady=10, ipadx=20, ipady=5)

    # --- Вспомогательные методы ---
    def _create_rounded_rect(self, x1, y1, x2, y2, radius=25, **kwargs):
        points = [x1+radius, y1, x1+radius, y1,
                  x2-radius, y1, x2-radius, y1,
                  x2, y1, x2, y1+radius,
                  x2, y1+radius, x2, y2-radius,
                  x2, y2-radius, x2, y2,
                  x2-radius, y2, x2-radius, y2,
                  x1+radius, y2, x1+radius, y2,
                  x1, y2, x1, y2-radius,
                  x1, y2-radius, x1, y1+radius,
                  x1, y1+radius, x1, y1]
        return self.btn_canvas.create_polygon(points, **kwargs, smooth=True)

    def _on_btn_click(self, event):
        self.toggle_lag()

    def fix_program(self):
        t = TRANSLATIONS[self.lang_var.get()]
        try:
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startupinfo.wShowWindow = subprocess.SW_HIDE
            
            cmds = [
                "sc stop WinDivert",
                "sc delete WinDivert",
                "sc stop windivert64",
                "sc delete windivert64"
            ]
            for cmd in cmds:
                subprocess.run(cmd, shell=True, startupinfo=startupinfo, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            messagebox.showinfo(t["fix_title"], t["fix_success"])
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def _save_sound_settings(self):
        self.settings["play_on"] = self.play_on_var.get()
        self.settings["play_off"] = self.play_off_var.get()
        save_settings(self.settings)

    def _select_sound(self, sound_type):
        file_path = filedialog.askopenfilename(
            title="Select Audio", 
            filetypes=[("Audio Files", "*.wav *.mp3 *.ogg *.flac"), ("All Files", "*.*")]
        )
        if file_path:
            self.settings[f"{sound_type}_sound"] = file_path
            save_settings(self.settings)
            self._update_sound_label()

    def _update_sound_label(self):
        on_path = self.settings.get("on_sound", "")
        off_path = self.settings.get("off_sound", "")
        text = ""
        if on_path: text += f"ON: {os.path.basename(on_path)}  "
        if off_path: text += f"OFF: {os.path.basename(off_path)}"
        if not text: text = "Default Beep"
        self.snd_path_label.config(text=text)

    def apply_hotkey(self, silent=False):
        new_hotkey = self.hk_entry.get().strip().lower()
        if not new_hotkey: return
            
        try:
            keyboard.remove_hotkey(self.current_hotkey)
        except: pass

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
        if self.is_running:
            self.btn_canvas.itemconfig(self.btn_text_top, text=t["stop_btn"])
            self.status_var.set(t["status_lagging"])
        else:
            self.btn_canvas.itemconfig(self.btn_text_top, text=t["start_btn"])
            self.status_var.set(t["status_ready"])
            
        self.btn_canvas.itemconfig(self.btn_text_bot, text=hk_text)

        self.auto_cb.config(text=t["auto_reconnect"])
        self.secs_label.config(text=t["seconds"])
        self.topmost_cb.config(text=t["always_on_top"])
        
        self.notebook.tab(0, text=t["tab_main"])
        self.notebook.tab(1, text=t["tab_settings"])
        
        self.lang_label.config(text=t["lang_label"])
        self.hk_label.config(text=t["hotkey_label"])
        self.hk_btn.config(text=t["btn_apply_hk"])
        
        self.on_cb.config(text=t["sound_on"])
        self.off_cb.config(text=t["sound_off"])
        self.on_label.config(text=t["sound_on_file"])
        self.off_label.config(text=t["sound_off_file"])
        self.on_btn.config(text=t["select_file"])
        self.off_btn.config(text=t["select_file"])
        self.fix_btn.config(text=t["fix_btn"])
        self._update_sound_label()

        if self.is_running and self.countdown_timer and self.time_left > 0:
            self.countdown_var.set(t["time_left"].format(self.time_left))
        elif not self.is_running and not self.auto_reconnect_var.get():
            self.countdown_var.set(t["no_limit"])
        else:
            self.countdown_var.set("")

    def _apply_topmost(self):
        self.root.attributes("-topmost", self.topmost_var.get())

    def _toggle_from_hotkey(self):
        self.root.after(0, self.toggle_lag)

    def _play_sound(self, sound_type):
        play_var = self.play_on_var if sound_type == "on" else self.play_off_var
        if not play_var.get(): return
            
        path = self.settings.get(f"{sound_type}_sound", "")
        if path and os.path.exists(path):
            try:
                pygame.mixer.music.load(path)
                pygame.mixer.music.play()
                return
            except Exception as e:
                print(f"Audio error: {e}")
                
        try:
            winsound.MessageBeep(winsound.MB_ICONASTERISK if sound_type == "on" else winsound.MB_ICONHAND)
        except: 
            pass

    def toggle_lag(self):
        if self.is_running:
            self.stop_lag()
        else:
            self.start_lag()

    def start_lag(self):
        if self.is_running: return

        if self.blocker:
            self.blocker.stop()
            self.blocker = None

        filter_str = "udp"

        try:
            w = pydivert.WinDivert(filter_str)
            w.open()
        except Exception as e:
            self.is_running = False
            t = TRANSLATIONS[self.lang_var.get()]
            msg = f"Failed to start blocking.\nError: {e}\n\n"
            msg += "Try clicking the '🛠 Fix Program' button in the Settings tab." if self.lang_var.get() == "en" else "Попробуйте нажать кнопку '🛠 Исправить программу' во вкладке Настройки."
            messagebox.showerror(t["err_filter"], msg)
            return

        self.is_running = True
        self.blocker = LagSwitchBlocker(w)
        self.blocker.start()
        
        self._play_sound("on")
        t = TRANSLATIONS[self.lang_var.get()]
        self.status_var.set(t["status_lagging"])
        
        hk_text = self.current_hotkey.upper().replace("+", " + ")
        self.btn_canvas.itemconfig(self.btn_text_top, text=t["stop_btn"])
        self.btn_canvas.itemconfig(self.btn_rect, fill="#e53935")

        if self.auto_reconnect_var.get():
            self.time_left = self.auto_seconds_var.get()
            self._update_countdown()
        else:
            self.countdown_var.set(t["no_limit"])

    def stop_lag(self):
        if not self.is_running:
            return
            
        self.is_running = False

        if self.auto_stop_timer:
            self.root.after_cancel(self.auto_stop_timer)
            self.auto_stop_timer = None
        
        if self.countdown_timer:
            self.root.after_cancel(self.countdown_timer)
            self.countdown_timer = None
            
        self.time_left = 0
        self.countdown_var.set("")

        if self.blocker:
            self.blocker.stop()
            self.blocker = None
            
        self._reset_ui()

    def _update_countdown(self):
        if self.time_left > 0 and self.is_running:
            t = TRANSLATIONS[self.lang_var.get()]
            self.countdown_var.set(t["time_left"].format(self.time_left))
            self.time_left -= 1
            self.countdown_timer = self.root.after(1000, self._update_countdown)
        elif self.is_running:
            self.stop_lag()

    def _reset_ui(self):
        t = TRANSLATIONS[self.lang_var.get()]
        self.status_var.set(t["status_restored"])
        
        hk_text = self.current_hotkey.upper().replace("+", " + ")
        self.btn_canvas.itemconfig(self.btn_text_top, text=t["start_btn"])
        self.btn_canvas.itemconfig(self.btn_rect, fill="#7cb342")
        
        self.countdown_var.set("")
        self._play_sound("off")

    def on_close(self):
        try:
            keyboard.remove_hotkey(self.current_hotkey)
        except:
            pass
        if self.blocker:
            self.blocker.stop()
        self.root.destroy()

if __name__ == "__main__":
    if not is_admin():
        request_admin()

    root = tk.Tk()
    app = PingSwitcherApp(root)
    root.mainloop()
