# -*- coding: utf-8 -*-
"""
智能交通违章系统（第4套 模块二 2-6）
模拟红绿灯 + 中距离一体机识别电子标签(RFID)车牌 + 闯红灯违章登记

功能：
  1. 三色灯每隔 red_light_seconds 秒轮流切换，界面红绿灯动画同步
  2. 绿灯/黄灯状态不显示汽车
  3. 红灯状态时，若串口服务器(TCP)读到标签卡号：
       - 已登记车牌(A81237/A21456/A36888) -> 提示"车辆闯红灯"并显示车牌号，保存违章记录(可选拍照)
       - 未登记卡号              -> 显示"未登记"
     非红灯后界面恢复初始状态
  4. 数据获取方式：串口服务器 TCP 模式（网络调试工具 NetAssist TCP Client）

运行：python traffic_violation.py
打包：pyinstaller -F -w -n 智能交通违章系统 traffic_violation.py
"""
import json
import os
import queue
import socket
import threading
import time
import tkinter as tk
from tkinter import font as tkfont
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "tcp": {"host": "192.168.1.10", "port": 8000},
    "red_light_seconds": 10,
    "green_light_seconds": 10,
    "plates": ["A81237", "A21456", "A36888"],
    "camera": {"enabled": False, "snapshot_url": "http://192.168.1.100/snapshot.jpg"},
    "report_dir": "\u8fdd\u7ae0\u8bb0\u5f55",
}

COLOR_BG = "#222222"
COLOR_TEXT = "#ffffff"
COLOR_LAMP_OFF = "#3a3a3a"
COLOR_RED = "#e74c3c"
COLOR_YELLOW = "#f1c40f"
COLOR_GREEN = "#2ecc71"


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    cfg[k] = v
        except Exception:
            pass
    return cfg


class TcpReader(threading.Thread):
    """从串口服务器 TCP 读取 RFID 卡号事件，放到事件队列。"""

    def __init__(self, cfg, events):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.events = events
        self.running = True
        self.buf = b""

    def run(self):
        while self.running:
            try:
                s = socket.create_connection(
                    (self.cfg["tcp"]["host"], self.cfg["tcp"]["port"]), timeout=5
                )
                s.settimeout(2)
                while self.running:
                    try:
                        data = s.recv(1024)
                    except socket.timeout:
                        continue
                    if not data:
                        break
                    self.buf += data
                    # 按换行/回车切分帧，卡号一般以文本形式发送
                    while b"\n" in self.buf or b"\r" in self.buf:
                        line, sep, self.buf = self.buf.partition(b"\n")
                        line = line.rstrip(b"\r").strip()
                        if line:
                            self.events.put(("card", line.decode("utf-8", "ignore")))
                s.close()
            except Exception as exc:
                self.events.put(("err", str(exc)))
                time.sleep(3)


class TrafficApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("\u667a\u80fd\u4ea4\u901a\u8fdd\u7ae0\u7cfb\u7edf")
        root.geometry("520x560")
        root.configure(bg=COLOR_BG)
        self.events = queue.Queue()
        self.tcp = TcpReader(cfg, self.events)
        self.tcp.start()

        # 信号灯状态: 0 无, 1 红, 2 黄, 3 绿
        self.light = 1
        self.prev_green = None
        self.plate = ""
        self.recorded = False

        self._build_ui()
        self._light_timer()
        self._poll()

    def _build_ui(self):
        self.cv = tk.Canvas(self.root, width=180, height=420, bg=COLOR_BG, highlightthickness=0)
        self.cv.pack(pady=10)
        self.lamp_red = self.cv.create_oval(45, 20, 135, 110, fill=COLOR_LAMP_OFF, outline="#666")
        self.lamp_yellow = self.cv.create_oval(45, 160, 135, 250, fill=COLOR_LAMP_OFF, outline="#666")
        self.lamp_green = self.cv.create_oval(45, 300, 135, 390, fill=COLOR_LAMP_OFF, outline="#666")
        self.cv.create_text(90, 130, text="\u7ea2\u706f", fill=COLOR_TEXT, font=("Microsoft YaHei", 10))
        self.cv.create_text(90, 270, text="\u9ec4\u706f", fill=COLOR_TEXT, font=("Microsoft YaHei", 10))
        self.cv.create_text(90, 410, text="\u7eff\u706f", fill=COLOR_TEXT, font=("Microsoft YaHei", 10))

        self.info = tk.StringVar(value="\u7b49\u5f85\u4e2d...")
        tk.Label(self.root, textvariable=self.info, fg=COLOR_TEXT, bg=COLOR_BG,
                 font=("Microsoft YaHei", 12)).pack(pady=4)

        self.car_var = tk.StringVar(value="")
        self.car_lbl = tk.Label(self.root, textvariable=self.car_var, fg=COLOR_RED, bg=COLOR_BG,
                                font=("Microsoft YaHei", 16, "bold"))
        self.car_lbl.pack(pady=6)

        self.status = tk.StringVar(value="TCP: \u672a\u8fde\u63a5")
        tk.Label(self.root, textvariable=self.status, fg="#aaaaaa", bg=COLOR_BG,
                 font=("Microsoft YaHei", 9)).pack()

    def _light_timer(self):
        """信号灯循环: 红(10s) -> 黄(2s) -> 绿(10s) -> 黄(2s) -> 红..."""
        if self.light == 1:      # 当前红灯
            secs = self.cfg["red_light_seconds"]
            nxt = 2
        elif self.light == 3:    # 当前绿灯
            secs = self.cfg["green_light_seconds"]
            nxt = 2
        else:                    # 当前黄灯
            secs = 2
            nxt = 3 if self.prev_green else 1
            self.prev_green = None
        # 记录绿灯来源判断下个黄灯去向
        if self.light == 2 and nxt != 1:
            self.prev_green = True
        self._update_light(self.light)
        self.light = nxt
        self.root.after(int(secs * 1000), self._light_timer)

    def _update_light(self, step):
        self.cv.itemconfig(self.lamp_red, fill=COLOR_RED if step == 1 else COLOR_LAMP_OFF)
        self.cv.itemconfig(self.lamp_yellow, fill=COLOR_YELLOW if step == 2 else COLOR_LAMP_OFF)
        self.cv.itemconfig(self.lamp_green, fill=COLOR_GREEN if step == 3 else COLOR_LAMP_OFF)
        # 非红灯时清除违章展示
        if step != 1:
            self.car_var.set("")
            self.plate = ""
            self.recorded = False

    def _on_card(self, card):
        self.plate = card
        self.info.set("检测到电子标签: %s" % card)
        if self.light == 1:
            if card in self.cfg["plates"]:
                self.car_var.set("\u8f66\u8f86\u95ef\u7ea2\u706f: %s" % card)
                self.info.set("\u8f66\u8f86\u95ef\u7ea2\u706f\uff01\u5df2\u767b\u8bb0\u7535\u5b50\u6807\u7b7e")
                self._save_record(card)
            else:
                self.car_var.set("\u8f66\u724c\u201c%s\u201d \u672a\u767b\u8bb0" % card)
        else:
            self.car_var.set("\u975e\u7ea2\u706f\u72b6\u6001\uff0c\u4e0d\u663e\u793a\u8f66\u8f86")

    def _save_record(self, card):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)), self.cfg["report_dir"])
        os.makedirs(d, exist_ok=True)
        with open(os.path.join(d, "violations.txt"), "a", encoding="utf-8") as f:
            f.write("%s\t%s\n" % (now, card))
        if self.cfg["camera"]["enabled"]:
            try:
                import requests
                r = requests.get(self.cfg["camera"]["snapshot_url"], timeout=5)
                if r.status_code == 200:
                    fn = os.path.join(d, "%s_%s.jpg" % (datetime.now().strftime("%H%M%S"), card))
                    with open(fn, "wb") as f:
                        f.write(r.content)
            except Exception:
                pass

    def _poll(self):
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "card":
                    self._on_card(payload)
                elif kind == "err":
                    self.status.set("TCP: %s" % payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)


def main():
    cfg = load_config()
    root = tk.Tk()
    TrafficApp(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()