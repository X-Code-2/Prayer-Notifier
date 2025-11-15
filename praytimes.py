# praytimes_gui_beautiful_buttons.py
"""
واجهة جميلة لتذكير الصلاة — بدون سلايدر صوت، بأزرار ملونة.
ضع ملف الصوت الافتراضي في: sound/prayer_notifier.mp3
لبناء EXE استخدم PyInstaller مع:
--add-data "sound\prayer_notifier.mp3;sound" --collect-all win10toast
"""

import sys
import os
import threading
import time
import requests
from datetime import datetime, date, timedelta
from bs4 import BeautifulSoup
import pygame
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pystray
from PIL import Image, ImageDraw
from win10toast import ToastNotifier

# ----------------- إعدادات -----------------
PRAYER_URL = 'https://timesprayer.com/en/prayer-times-in-cairo.html'
PREALARM_MINUTES = 5
CHECK_INTERVAL_SEC = 8
DEFAULT_AUDIO = os.path.join("sound", "prayer_notifier.mp3")  # نسبي لمجلد المشروع
# -------------------------------------------

def resource_path(rel_path):
    """إرجاع المسار الصحيح سواءً كملف .py أو داخل EXE من PyInstaller."""
    if getattr(sys, 'frozen', False):
        base_path = sys._MEIPASS
    else:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, rel_path)

# المسار الفعلي لملف الصوت
AUDIO_PATH = resource_path(DEFAULT_AUDIO)

# إشعارات ويندوز
toaster = ToastNotifier()

# حالة مشتركة بين الخيط والواجهة
state = {
    "running": False,
    "next_name": None,
    "next_dt": None,
    "prev_dt": None,
    "volume": 0.85,      # قيمة افتراضية، لا يوجد سلايدر داخل الواجهة
    "audio": AUDIO_PATH,
    "lock": threading.Lock()
}

# ----------- وظائف الصوت والإشعار -----------
def init_pygame_if_needed():
    try:
        if not pygame.mixer.get_init():
            pygame.mixer.init()
    except Exception as e:
        print("تحذير: فشل تهيئة pygame:", e)

def play_sound_file(path, volume=0.85):
    """تشغيل ملف صوتي في ثريد منفصل (لا يحجب الواجهة)."""
    if not os.path.exists(path):
        print("ملف الصوت غير موجود:", path)
        return
    def _play():
        try:
            init_pygame_if_needed()
            try:
                pygame.mixer.music.stop()
            except Exception:
                pass
            pygame.mixer.music.load(path)
            pygame.mixer.music.set_volume(volume)
            pygame.mixer.music.play()
        except Exception as e:
            print("خطأ أثناء تشغيل الصوت:", e)
    threading.Thread(target=_play, daemon=True).start()

def notify(title, msg, duration=6):
    """إظهار إشعار بطريقة آمنة (داخل ثريد منفصل، threaded=False داخلياً)."""
    def _show():
        try:
            toaster.show_toast(title, msg, duration=duration, threaded=False)
        except Exception as e:
            print("فشل الإشعار:", e)
    threading.Thread(target=_show, daemon=True).start()

# ----------- جلب مواعيد الصلاة -----------
def fetch_prayer_times():
    try:
        r = requests.get(PRAYER_URL, timeout=12)
        r.raise_for_status()
    except Exception as e:
        print("خطأ جلب الأوقات:", e)
        return []
    soup = BeautifulSoup(r.content, "lxml")
    table = soup.find('table', {'class': 'ptTable'})
    if not table:
        return []
    today = date.today()
    times = []
    for row in table.find_all("tr"):
        cells = row.find_all("td")
        if len(cells) >= 2:
            name = cells[0].get_text(strip=True)
            tstr = cells[1].get_text(strip=True)
            try:
                dt_time = datetime.strptime(tstr, "%I:%M %p").time()
            except Exception:
                continue
            dt = datetime.combine(today, dt_time)
            times.append((name, dt))
    times.sort(key=lambda x: x[1])
    return times

def find_next_and_prev(schedule):
    now = datetime.now()
    prev = None
    for name, dt in schedule:
        if dt > now:
            return name, dt, prev
        prev = (name, dt)
    return None, None, prev

# ----------- أيقونة التراي -----------
tray_icon = None
def create_tray_image(size=64):
    img = Image.new("RGBA", (size, size), (0,0,0,0))
    draw = ImageDraw.Draw(img)
    # رسم أيقونة بسيطة أنيقة
    draw.ellipse((8, 14, size-8, size-8), fill=(255,215,102,255))
    draw.rectangle((size*0.62, 6, size*0.70, size*0.36), fill=(255,215,102,255))
    draw.ellipse((size*0.58, 0, size*0.66, 12), fill=(255,215,102,255))
    return img

def on_tray_show(icon, item):
    root.after(0, restore_window)

def on_tray_quit(icon, item):
    try:
        icon.stop()
    except Exception:
        pass
    os._exit(0)

def setup_tray():
    global tray_icon
    if tray_icon is not None:
        return
    image = create_tray_image(64)
    menu = pystray.Menu(pystray.MenuItem("إظهار", on_tray_show), pystray.MenuItem("خروج", on_tray_quit))
    tray_icon = pystray.Icon("praytimes", image, "Prayer Notifier", menu)
    threading.Thread(target=tray_icon.run, daemon=True).start()

def hide_window_to_tray():
    try:
        root.withdraw()
        setup_tray()
    except Exception as e:
        print("خطأ أثناء الإخفاء إلى التراي:", e)

def restore_window():
    try:
        root.deiconify()
        root.lift()
    except Exception as e:
        print("خطأ استعادة النافذة:", e)

# ----------- العامل الخلفي -----------
def background_worker():
    triggered = set()
    while True:
        if not state["running"]:
            time.sleep(1)
            continue
        schedule = fetch_prayer_times()
        if not schedule:
            with state["lock"]:
                state["next_name"] = None
                state["next_dt"] = None
                state["prev_dt"] = None
            time.sleep(8)
            continue
        name, dt, prev = find_next_and_prev(schedule)
        with state["lock"]:
            state["next_name"] = name
            state["next_dt"] = dt
            state["prev_dt"] = prev[1] if prev else datetime.now()
        # prealarm
        if name and dt:
            key = (name, dt.date())
            alert_time = dt - timedelta(minutes=PREALARM_MINUTES)
            now = datetime.now()
            if key not in triggered and alert_time <= now <= dt + timedelta(seconds=60):
                notify("جارٍ اختبار صوت الآذان", f"{name} — سيتم تشغيل صوت الآذان الآن")
                play_sound_file(state["audio"], volume=state["volume"])
                triggered.add(key)
        time.sleep(CHECK_INTERVAL_SEC)

# ----------- إنشاء الواجهة (GUI) -----------
root = tk.Tk()
root.title("Prayer Notifier")
root.geometry("520x360")
root.resizable(False, False)

# ألوان وثيم
DARK_BG = "#0f1315"
CARD_BG = "#16191b"
ACCENT = "#2ecc71"
TEXT = "#ecf0f1"
MUTED = "#9ba5ad"

root.configure(bg=DARK_BG)

# ستايلات
style = ttk.Style(root)
style.theme_use("clam")
style.configure("Card.TFrame", background=CARD_BG, relief="flat")
style.configure("Title.TLabel", background=DARK_BG, foreground=TEXT, font=("Segoe UI", 18, "bold"))
style.configure("Muted.TLabel", background=CARD_BG, foreground=MUTED, font=("Segoe UI", 9))
style.configure("Big.TLabel", background=CARD_BG, foreground=TEXT, font=("Segoe UI", 26, "bold"))

# Header
header = ttk.Frame(root, style="Card.TFrame")
header.place(x=12, y=12, width=496, height=80)
ttk.Label(header, text="Prayer Reminder", style="Title.TLabel").place(x=16, y=12)

# حالة
status_frame = ttk.Frame(header, style="Card.TFrame")
status_frame.place(x=340, y=20, width=132, height=40)
status_dot = tk.Canvas(status_frame, width=16, height=16, bg=CARD_BG, highlightthickness=0)
status_dot.place(x=8, y=12)
status_label = ttk.Label(status_frame, text="متوقف", style="Muted.TLabel")
status_label.place(x=32, y=10)

# البطاقة الرئيسية
card = ttk.Frame(root, style="Card.TFrame")
card.place(x=12, y=104, width=496, height=160)

ttk.Label(card, text="الصلاة القادمة", style="Muted.TLabel").place(x=16, y=10)
next_name_var = tk.StringVar(value="—")
next_time_var = tk.StringVar(value="—")
name_lbl = ttk.Label(card, textvariable=next_name_var, style="Big.TLabel")
name_lbl.place(x=16, y=30)
time_lbl = ttk.Label(card, textvariable=next_time_var, style="Muted.TLabel")
time_lbl.place(x=16, y=86)

# العدّاد والـ progress
countdown_var = tk.StringVar(value="00:00:00")
countdown_lbl = ttk.Label(card, textvariable=countdown_var, style="Big.TLabel")
countdown_lbl.place(x=320, y=28)
progress = ttk.Progressbar(card, orient="horizontal", mode="determinate", length=320)
progress.place(x=16, y=120)

# ---------- قسم الأزرار (بدون سلايدر صوت) ----------
ctrl = ttk.Frame(root, style="Card.TFrame")
ctrl.place(x=12, y=276, width=496, height=72)

# تعاريف ألوان وأزرار أنيقة
style.configure("Run.TButton", foreground="#ffffff", font=("Segoe UI", 11, "bold"), padding=6)
style.map("Run.TButton", background=[("active", "#2ecc71"), ("!active", "#27ae60")])

style.configure("Stop.TButton", foreground="#ffffff", font=("Segoe UI", 11, "bold"), padding=6)
style.map("Stop.TButton", background=[("active", "#e74c3c"), ("!active", "#c0392b")])

style.configure("Blue.TButton", foreground="#ffffff", font=("Segoe UI", 11, "bold"), padding=6)
style.map("Blue.TButton", background=[("active", "#3498db"), ("!active", "#2980b9")])

style.configure("Gray.TButton", foreground="#ffffff", font=("Segoe UI", 11, "bold"), padding=6)
style.map("Gray.TButton", background=[("active", "#95a5a6"), ("!active", "#7f8c8d")])

# تنفيذ تشغيل/إيقاف
def on_toggle():
    state["running"] = not state["running"]
    if state["running"]:
        status_label.config(text="شغال")
        status_dot.delete("all")
        status_dot.create_oval(0,0,16,16, fill=ACCENT, outline=ACCENT)
        btn_toggle.config(text="إيقاف", style="Stop.TButton")
        notify("جارٍ اختبار صوت الآذان", "تشغيل اختبار صوت الآذان الآن")
        play_sound_file(state["audio"], volume=state["volume"])
    else:
        status_label.config(text="متوقف")
        status_dot.delete("all")
        status_dot.create_oval(0,0,16,16, fill="#e74c3c", outline="#e74c3c")
        btn_toggle.config(text="تشغيل", style="Run.TButton")
        next_name_var.set("—")
        next_time_var.set("—")
        countdown_var.set("00:00:00")
        progress['value'] = 0

btn_toggle = ttk.Button(ctrl, text="تشغيل", style="Run.TButton", command=on_toggle)
btn_toggle.place(x=14, y=10, width=130, height=40)

# زر اختبار الصوت (أزرق)
def manual_test():
    notify("اختبار الآذان", "تشغيل صوت الآذان للاختبار")
    play_sound_file(state["audio"], volume=state["volume"])

btn_test = ttk.Button(ctrl, text="اختبار الصوت", style="Blue.TButton", command=manual_test)
btn_test.place(x=160, y=10, width=130, height=40)

# اختيار ملف الصوت
def choose_audio():
    file = filedialog.askopenfilename(title="اختر ملف الآذان", filetypes=[("Audio", "*.mp3 *.wav")])
    if file:
        with state["lock"]:
            state["audio"] = file
        notify("تم اختيار ملف جديد", os.path.basename(file))
        # نظهر اسم الملف كتعليق صغير
        root.after(0, lambda: time_lbl.config(text=f"ملف: {os.path.basename(file)}"))

btn_choose = ttk.Button(ctrl, text="اختيار ملف", style="Gray.TButton", command=choose_audio)
btn_choose.place(x=306, y=10, width=80, height=40)

# زر خروج أحمر
def exit_app():
    if messagebox.askyesno("تأكيد", "هل تريد الخروج؟"):
        try:
            if tray_icon:
                tray_icon.stop()
        except Exception:
            pass
        root.destroy()
        os._exit(0)

btn_exit = ttk.Button(ctrl, text="خروج", style="Stop.TButton", command=exit_app)
btn_exit.place(x=396, y=10, width=80, height=40)

# عند التصغير اخفاء إلى التراي
def on_minimize(event):
    if root.state() == "iconic":
        hide_window_to_tray()

root.bind("<Unmap>", on_minimize)
root.protocol("WM_DELETE_WINDOW", lambda: exit_app())

# ---------- تحديث الواجهة بطريقة آمنة ----------
def update_ui():
    with state["lock"]:
        nname = state.get("next_name")
        ndt = state.get("next_dt")
        pdt = state.get("prev_dt")
    if nname and ndt:
        next_name_var.set(nname)
        next_time_var.set(ndt.strftime("%I:%M %p"))
        now = datetime.now()
        remaining = ndt - now
        if remaining.total_seconds() < 0:
            remaining = timedelta(0)
        h, rem = divmod(int(remaining.total_seconds()), 3600)
        m, s = divmod(rem, 60)
        countdown_var.set(f"{h:02d}:{m:02d}:{s:02d}")
        # شريط التقدم
        try:
            start = pdt if pdt else now
            total = (ndt - start).total_seconds()
            passed = (now - start).total_seconds()
            frac = max(0.0, min(1.0, passed / total)) if total > 0 else 0.0
            progress['value'] = frac * 100
        except Exception:
            progress['value'] = 0
    else:
        next_name_var.set("—")
        next_time_var.set("—")
        countdown_var.set("00:00:00")
        progress['value'] = 0
    root.after(1000, update_ui)

# تشغيل الخيط الخلفي وتحديث الواجهة
threading.Thread(target=background_worker, daemon=True).start()
update_ui()

# الدوت الابتدائي
status_dot.create_oval(0,0,16,16, fill="#e74c3c", outline="#e74c3c")

# شغّل النافذة
try:
    root.mainloop()
except KeyboardInterrupt:
    pass
