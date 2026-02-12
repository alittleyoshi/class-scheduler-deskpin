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


class ClassSchedulerApp:
    def __init__(self):
        self.schedule = []
        self.status = "等待开始"
        self.running = True
        self.root = None
        self.label_status = None
        self.tray_icon = None
        self._timer_thread = None

    def load_schedule(self):
        # 确保目录存在
        os.makedirs("assets/scv", exist_ok=True)
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

            # 判断为初次使用，添加目录结构
            os.makedirs("assets/sounds", exist_ok=True)

            print("⚠️ schedule.csv 不存在，已生成默认文件，请修改后重启程序。")

        self.schedule.clear()
        with open("assets/scv/schedule.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.schedule.append(
                    {
                        "period": row["period"],
                        "type": row["type"],
                        "start": row["start"],
                        "end": row["end"],
                        "sound": row["sound"],
                    }
                )

    def play_sound(self, file):
        sound_path = os.path.join("assets", "sounds", file)
        if not os.path.exists(sound_path):
            messagebox.showerror("错误", f"找不到音频文件: {file}\n请将音频文件放入 assets/sounds 目录下。")
            print(f"⚠️ 找不到音频文件: {file}\n请将音频文件放入 assets/sounds 目录下。")
            return
        mixer.init()
        mixer.music.load(sound_path)
        mixer.music.play()

    def timer_loop(self):
        last_trigger = None
        while self.running:
            now = datetime.now().strftime("%H:%M")
            in_period = False  # 是否在某一节课/休息里

            for item in self.schedule:
                # 判断当前是否在某一时间段内
                if item["start"] <= now < item["end"]:
                    in_period = True
                    self.status = item["type"]

                # 到达开始时间触发铃声
                if now == item["start"] and last_trigger != (item["period"], "start"):
                    self.play_sound(item["sound"])
                    last_trigger = (item["period"], "start")

                # 到达结束时间触发铃声
                if now == item["end"] and last_trigger != (item["period"], "end"):
                    self.play_sound(item["sound"])
                    last_trigger = (item["period"], "end")

            if not in_period:
                self.status = "空闲中"

            time.sleep(5)  # 每 5 秒检查一次

    def update_ui(self):
        if self.root is None or self.label_status is None:
            return

        self.label_status.config(text=f"状态：{self.status}\n当前时间：{datetime.now().strftime('%H:%M:%S')}")
        if self.running:
            self.root.after(1000, self.update_ui)

    def start_drag(self, event):
        self.root.x = event.x
        self.root.y = event.y

    def do_drag(self, event):
        x = self.root.winfo_x() - self.root.x + event.x
        y = self.root.winfo_y() - self.root.y + event.y
        self.root.geometry(f"+{x}+{y}")

    def reset_window(self, icon=None, item=None):
        self.root.geometry("200x60+100+100")  # 重置到初始位置

    def shutdown(self, icon=None, item=None):
        self.running = False

        if self.tray_icon is not None:
            self.tray_icon.stop()

        if self.root is not None:
            self.root.after(0, self.root.quit)

    def create_tray(self):
        image = Image.new("RGB", (64, 64), "blue")
        draw = ImageDraw.Draw(image)
        draw.rectangle([16, 16, 48, 48], fill="white")

        menu = pystray.Menu(
            pystray.MenuItem("窗口位置重置", self.reset_window),
            pystray.MenuItem("退出", self.shutdown),
        )
        self.tray_icon = pystray.Icon("bell", image, "上课铃", menu)
        threading.Thread(target=self.tray_icon.run, daemon=True).start()

    def run(self):
        self.load_schedule()

        self.root = tk.Tk()
        self.root.title("上课铃小工具")
        self.root.geometry("200x60")
        self.root.attributes("-topmost", True)

        self.root.overrideredirect(True)
        self.root.bind("<ButtonPress-1>", self.start_drag)
        self.root.bind("<B1-Motion>", self.do_drag)

        # 添加右键菜单，可以退出程序
        def show_menu(event):
            menu = tk.Menu(self.root, tearoff=0)
            menu.add_command(label="退出", command=self.shutdown)
            menu.add_command(label="播放声音", command=lambda: self.play_sound(self.schedule[1]["sound"]))
            menu.tk_popup(event.x_root, event.y_root)

        self.root.bind("<Button-3>", show_menu)

        self.label_status = tk.Label(self.root, text="状态：等待开始", font=("微软雅黑", 12))
        self.label_status.pack(pady=10)

        self._timer_thread = threading.Thread(target=self.timer_loop, daemon=True)
        self._timer_thread.start()
        self.update_ui()
        self.create_tray()

        self.root.mainloop()


def main():
    app = ClassSchedulerApp()
    app.run()


if __name__ == "__main__":
    main()
