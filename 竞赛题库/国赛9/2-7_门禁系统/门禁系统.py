# -*- coding: utf-8 -*-
"""套9 2-7 客厅环境系统升级（门禁+电动推杆） - Python 3.6 兼容
任务要求：
- 电动推杆伸出=关门，缩回=开门
- 行程开关反馈关门状态
- UHF桌面发卡器读取RFID标签：
  - RFID1 -> 开门，电动推杆缩回，显示开门背景图，LED显示"欢迎光临"
  - RFID2 -> 关门，电动推杆伸出，显示关门背景图，LED显示"您走好"
  - RFID3 -> 关门背景图，LED显示"未注册"
- 接近开关和行程开关辅助电动推杆切换
"""
import os
import sys
import time
import random
import threading

try:
    import requests
except ImportError:
    requests = None

try:
    import tkinter as tk
    from PIL import Image, ImageTk
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

CLOUD_BASE = "http://api.nlecloud.com"
CLOUD_USER = "13329262958"
CLOUD_PASS = "qwe123456789"


class CloudClient:
    def __init__(self):
        self.token = ""
    def login(self):
        if not requests: return False
        try:
            r = requests.post("%s/Users/Login" % CLOUD_BASE,
                json={"Account": CLOUD_USER, "Password": CLOUD_PASS, "IsRememberMe": True}, timeout=5)
            data = r.json()
            if data["Status"] == 0:
                self.token = data["ResultObj"]["AccessToken"]
                return True
        except: pass
        return False
    def send_command(self, device_id, api_tag, value):
        if not self.token or not requests: return
        try:
            requests.post("%s/Cmds" % CLOUD_BASE,
                headers={"AccessToken": self.token},
                params={"deviceId": device_id, "apiTag": api_tag},
                json=value, timeout=5)
        except: pass
    def get_sensor_data(self, device_id, api_tag):
        if not self.token or not requests: return None
        try:
            r = requests.get("%s/Devices/%s/Datas" % (CLOUD_BASE, device_id),
                headers={"AccessToken": self.token},
                params={"ApiTags": api_tag}, timeout=5)
            data = r.json()
            if data["Status"] == 0 and data["ResultObj"]:
                for item in data["ResultObj"].get("PageSet", []):
                    if item.get("ApiTag", "").lower() == api_tag.lower():
                        return item.get("Value", "")
        except: pass
        return None


class DoorSystem:
    """门禁电动推杆系统"""
    # RFID注册表
    REGISTERED = {
        "RFID001": "张三",
        "RFID002": "李四",
    }

    def __init__(self):
        self.cloud = CloudClient()
        self.door_open = False  # True=开门状态
        self.running = False
        self.root = None
        self.led_text = ""

    def set_door(self, open_door):
        """控制电动推杆"""
        self.door_open = open_door
        # 电动推杆: putt=前进(关门), back=后退(开门)
        self.cloud.send_command(1, "m_pushrod_putt", {"value": "0" if open_door else "1"})
        self.cloud.send_command(1, "m_pushrod_back", {"value": "1" if open_door else "0"})

    def on_card_read(self, rfid):
        """处理RFID读卡"""
        if rfid == "RFID001":
            self.set_door(True)  # 开门
            self.led_text = "欢迎光临"
        elif rfid == "RFID002":
            self.set_door(False)  # 关门
            self.led_text = "您走好"
        else:
            self.set_door(False)
            self.led_text = "未注册"

        if self.root and hasattr(self, 'status_label'):
            self.update_gui()

    def update_gui(self):
        state = "开门" if self.door_open else "关门"
        color = "green" if self.door_open else "red"
        self.status_label.config(text="当前状态: %s" % state, fg=color)
        self.led_display.config(text=self.led_text)
        bg = "#90EE90" if self.door_open else "#D3D3D3"
        self.door_canvas.config(bg=bg)

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("客厅环境系统 - 门禁")
        self.root.geometry("500x400")

        tk.Label(self.root, text="客厅环境系统升级", font=("微软雅黑", 14, "bold")).pack(pady=5)

        # 门状态
        self.door_canvas = tk.Canvas(self.root, width=200, height=120, bg="#D3D3D3")
        self.door_canvas.pack(pady=5)
        self.door_canvas.create_text(100, 60, text="门", font=("微软雅黑", 16))

        self.status_label = tk.Label(self.root, text="当前状态: 关门", font=("微软雅黑", 12))
        self.status_label.pack(pady=5)

        # LED显示屏
        led_frame = tk.Frame(self.root, bg="black", bd=2, relief=tk.SUNKEN)
        led_frame.pack(pady=10, padx=30, fill=tk.X)
        self.led_display = tk.Label(led_frame, text="", font=("Consolas", 16),
                                    bg="black", fg="#00ff00")
        self.led_display.pack(pady=8)

        # 模拟读卡按钮
        card_frame = tk.Frame(self.root)
        card_frame.pack(pady=10)
        tk.Label(card_frame, text="模拟读卡:", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        tk.Button(card_frame, text="RFID1(张三)", command=lambda: self.on_card_read("RFID001"),
                  font=("微软雅黑", 9), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=3)
        tk.Button(card_frame, text="RFID2(李四)", command=lambda: self.on_card_read("RFID002"),
                  font=("微软雅黑", 9), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=3)
        tk.Button(card_frame, text="RFID3(未注册)", command=lambda: self.on_card_read("RFID999"),
                  font=("微软雅黑", 9), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=3)

        # 手动控制
        ctrl_frame = tk.Frame(self.root)
        ctrl_frame.pack(pady=5)
        tk.Button(ctrl_frame, text="手动开门", command=lambda: self.set_door(True),
                  font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl_frame, text="手动关门", command=lambda: self.set_door(False),
                  font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)

    def monitor_loop(self):
        while self.running:
            # 从云平台读取RFID
            val = self.cloud.get_sensor_data(1, "m_rfid")
            if val:
                self.on_card_read(val)
            time.sleep(1)

    def start_monitor(self):
        if not self.running:
            self.running = True
            self.cloud.login()
            t = threading.Thread(target=self.monitor_loop, daemon=True)
            t.start()

    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            print("门禁系统（命令行模式）")
            print("RFID1=开门+欢迎  RFID2=关门+您走好  RFID3=未注册")
            self.cloud.login()
            while True:
                try:
                    cmd = input("输入RFID号: ").strip()
                    if cmd:
                        self.on_card_read(cmd)
                except (KeyboardInterrupt, EOFError):
                    break


if __name__ == "__main__":
    app = DoorSystem()
    app.run()
