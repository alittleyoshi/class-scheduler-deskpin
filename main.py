import tkinter as tk
import threading
import time
import csv
import os
from pygame import mixer
import pystray
from PIL import Image, ImageDraw
from datetime import datetime
from tkinter import messagebox

schedule = []
status = "等待开始"
running = True


def load_schedule():
    global schedule
    if not os.path.exists("assets/scv/schedule.csv"):
        # 默认文件
        with open("assets/scv/schedule.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["period", "type", "start", "end", "sound"])
            writer.writerow([1, "work", "08:00", "08:40", "class_start.mp3"])
            writer.writerow([2, "break", "08:40", "08:50", "class_end.mp3"])
        # 弹窗提示
        messagebox.showwarning(
            "提示",
            "已生成默认 schedule.csv，请修改后重启程序。"
        )
        print(f"⚠️ schedule.csv 不存在，已生成默认文件，请修改后重启程序。")

    schedule.clear()
    with open("assets/scv/schedule.csv", "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            schedule.append({
                "period": row["period"],
                "type": row["type"],
                "start": row["start"],
                "end": row["end"],
                "sound": row["sound"]
            })


def play_sound(file):
    sound_path = os.path.join("assets", "sounds", file)
    if not os.path.exists(sound_path):
        messagebox.showerror("错误", f"找不到音频文件: {sound_path}")
        print(f"⚠️ 找不到音频文件: {sound_path}")
        return
    mixer.init()
    mixer.music.load(sound_path)
    mixer.music.play()


def timer_loop():
    global status
    last_trigger = None
    while True:
        if running:
            now = datetime.now().strftime("%H:%M")
            in_period = False  # 是否在某一节课/休息里

            for item in schedule:
                # 判断当前是否在某一时间段内
                if item["start"] <= now < item["end"]:
                    in_period = True
                    status = item["type"]

                # 到达开始时间触发铃声
                if now == item["start"] and last_trigger != (item["period"], "start"):
                    play_sound(item["sound"])
                    last_trigger = (item["period"], "start")

                # 到达结束时间触发铃声
                if now == item["end"] and last_trigger != (item["period"], "end"):
                    play_sound(item["sound"])
                    last_trigger = (item["period"], "end")

            if not in_period:
                status = "空闲中"

        time.sleep(5)  # 每 5 秒检查一次


def update_ui():
    label_status.config(text=f"状态：{status}\n当前时间：{datetime.now().strftime('%H:%M:%S')}")
    root.after(1000, update_ui)


def quit_app(icon, item):
    icon.stop()
    root.quit()
    
def reset_window(icon, item):
        root.geometry("200x60+100+100")  # 重置到初始位置

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

    # 添加右键菜单，可以退出程序
    def show_menu(event):
        menu = tk.Menu(root, tearoff=0)
        menu.add_command(label="退出", command=root.quit)
        menu.add_command(label="播放声音", command=lambda: play_sound(schedule[1]["sound"]))
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
