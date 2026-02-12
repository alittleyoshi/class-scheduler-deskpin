import csv
import os
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

import pystray
from PIL import Image, ImageDraw
from pygame import mixer

schedule = []
status = "等待开始"
running = True
CHECK_OVERLAP = True
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SCHEDULE_PATH = os.path.join(BASE_DIR, "schedule.csv")
LEGACY_SCHEDULE_PATH = os.path.join(BASE_DIR, "assets", "scv", "schedule.csv")


def parse_minutes(value):
    parsed_time = datetime.strptime(value, "%H:%M").time()
    return parsed_time.hour * 60 + parsed_time.minute


def get_schedule_path():
    if os.path.exists(SCHEDULE_PATH):
        return SCHEDULE_PATH
    if os.path.exists(LEGACY_SCHEDULE_PATH):
        return LEGACY_SCHEDULE_PATH
    return SCHEDULE_PATH


def ensure_default_schedule(path):
    if os.path.exists(path):
        return

    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["period", "type", "start", "end", "sound"])
        writer.writerow([1, "work", "08:00", "08:40", "class_start.mp3"])
        writer.writerow([2, "break", "08:40", "08:50", "class_end.mp3"])

    messagebox.showwarning("提示", "已生成默认 schedule.csv，请修改后重启程序。")
    print(f"⚠️ schedule.csv 不存在，已生成默认文件：{path}")


def load_schedule():
    global schedule

    schedule_path = get_schedule_path()
    ensure_default_schedule(schedule_path)

    schedule.clear()
    errors = []

    with open(schedule_path, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            line_no = reader.line_num
            required_fields = ["period", "type", "start", "end", "sound"]
            missing_fields = [field for field in required_fields if not (row.get(field) or "").strip()]
            if missing_fields:
                errors.append(f"第 {line_no} 行配置错误：缺少必填字段 {', '.join(missing_fields)}")
                continue

            period_raw = row["period"].strip()
            start_raw = row["start"].strip()
            end_raw = row["end"].strip()

            try:
                period = int(period_raw)
            except ValueError:
                errors.append(f"第 {line_no} 行配置错误：period 必须是可排序数字，当前值为 '{period_raw}'")
                continue

            try:
                start_minutes = parse_minutes(start_raw)
            except ValueError:
                errors.append(f"第 {line_no} 行配置错误：start 时间格式错误，必须为 HH:MM，当前值为 '{start_raw}'")
                continue

            try:
                end_minutes = parse_minutes(end_raw)
            except ValueError:
                errors.append(f"第 {line_no} 行配置错误：end 时间格式错误，必须为 HH:MM，当前值为 '{end_raw}'")
                continue

            if start_minutes >= end_minutes:
                errors.append(f"第 {line_no} 行配置错误：start 必须早于 end，当前值为 {start_raw}-{end_raw}")
                continue

            schedule.append(
                {
                    "line": line_no,
                    "period": period,
                    "type": row["type"].strip(),
                    "start": start_raw,
                    "end": end_raw,
                    "start_minutes": start_minutes,
                    "end_minutes": end_minutes,
                    "sound": row["sound"].strip(),
                }
            )

    schedule.sort(key=lambda item: item["period"])

    if CHECK_OVERLAP:
        valid_schedule = []
        for item in schedule:
            overlap_item = next(
                (
                    prev
                    for prev in valid_schedule
                    if not (
                        item["start_minutes"] >= prev["end_minutes"]
                        or item["end_minutes"] <= prev["start_minutes"]
                    )
                ),
                None,
            )
            if overlap_item:
                errors.append(
                    f"第 {item['line']} 行配置错误：时间段与第 {overlap_item['line']} 行重叠 "
                    f"({item['start']}-{item['end']} 与 {overlap_item['start']}-{overlap_item['end']})"
                )
                continue
            valid_schedule.append(item)
        schedule = valid_schedule

    if errors:
        error_text = "\n".join(errors)
        print(error_text)
        messagebox.showwarning("课表配置错误", error_text)

    if not schedule:
        print("⚠️ 未加载到有效课表，请检查 schedule.csv 配置。")


def resolve_sound_path(file_name):
    candidates = [
        os.path.join(BASE_DIR, file_name),
        os.path.join(BASE_DIR, "assets", "sounds", file_name),
    ]
    for path in candidates:
        if os.path.exists(path):
            return path
    return None


def play_sound(file):
    sound_path = resolve_sound_path(file)
    if not sound_path:
        messagebox.showerror(
            "错误",
            f"找不到音频文件: {file}\n请将音频文件放在程序目录或 assets/sounds 目录下。",
        )
        print(f"⚠️ 找不到音频文件: {file}\n请将音频文件放在程序目录或 assets/sounds 目录下。")
        return
    mixer.init()
    mixer.music.load(sound_path)
    mixer.music.play()


def timer_loop():
    global status
    last_trigger = None
    while True:
        if running:
            now = datetime.now()
            now_minutes = now.hour * 60 + now.minute
            in_period = False

            for item in schedule:
                if item["start_minutes"] <= now_minutes < item["end_minutes"]:
                    in_period = True
                    status = item["type"]

                if now_minutes == item["start_minutes"] and last_trigger != (item["period"], "start"):
                    play_sound(item["sound"])
                    last_trigger = (item["period"], "start")

                if now_minutes == item["end_minutes"] and last_trigger != (item["period"], "end"):
                    play_sound(item["sound"])
                    last_trigger = (item["period"], "end")

            if not in_period:
                status = "空闲中"

        time.sleep(5)


def update_ui():
    label_status.config(text=f"状态：{status}\n当前时间：{datetime.now().strftime('%H:%M:%S')}")
    root.after(1000, update_ui)


def quit_app(icon, item):
    icon.stop()
    root.quit()


def reset_window(icon, item):
    root.geometry("200x60+100+100")


def create_tray():
    image = Image.new("RGB", (64, 64), "blue")
    draw = ImageDraw.Draw(image)
    draw.rectangle([16, 16, 48, 48], fill="white")

    menu = pystray.Menu(
        pystray.MenuItem("窗口位置重置", reset_window),
        pystray.MenuItem("退出", quit_app),
    )
    icon = pystray.Icon("bell", image, "上课铃", menu)
    threading.Thread(target=icon.run, daemon=True).start()


def start_drag(event):
    root.x = event.x
    root.y = event.y


def do_drag(event):
    x = root.winfo_x() - root.x + event.x
    y = root.winfo_y() - root.y + event.y
    root.geometry(f"+{x}+{y}")


def main():
    global root, label_status
    load_schedule()

    root = tk.Tk()
    root.title("上课铃小工具")
    root.geometry("200x60")
    root.attributes("-topmost", True)

    root.overrideredirect(True)
    root.bind("<ButtonPress-1>", start_drag)
    root.bind("<B1-Motion>", do_drag)

    def show_menu(event):
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="退出", command=root.quit)
        menu.add_command(label="播放声音", command=lambda: play_sound(schedule[0]["sound"]) if schedule else None)
        menu.tk_popup(event.x_root, event.y_root)

    root.bind("<Button-3>", show_menu)

    label_status = tk.Label(root, text="状态：等待开始", font=("微软雅黑", 12))
    label_status.pack(pady=10)

    threading.Thread(target=timer_loop, daemon=True).start()
    update_ui()
    create_tray()

    root.mainloop()


if __name__ == "__main__":
    main()
