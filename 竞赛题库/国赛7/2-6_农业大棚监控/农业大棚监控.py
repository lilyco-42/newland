# -*- coding: utf-8 -*-
"""智能农业大棚监控系统 - Python 3.6 兼容版"""
import tkinter as tk
from tkinter import ttk, messagebox
import time
import datetime
import json
import threading
import random

try:
    import urllib.request
except ImportError:
    pass

API_URL = "http://api.nlecloud.com"
API_TOKEN = "your_token_here"

# 大棚区域
ZONES = ["A区-番茄", "B区-黄瓜", "C区-辣椒", "D区-草莓", "E区-生菜", "F区-育苗"]


class GreenhouseZone:
    def __init__(self, name, zone_id):
        self.name = name
        self.zone_id = zone_id
        self.air_temp = 25.0 + random.random() * 5
        self.air_humid = 65.0 + random.random() * 20
        self.soil_temp = 20.0 + random.random() * 5
        self.soil_humid = 40.0 + random.random() * 20
        self.light = 5000 + random.random() * 5000
        self.co2 = 350 + random.random() * 200
        self.vent_on = False
        self.light_on = True
        self.irr_on = False

    def update_data(self):
        self.air_temp += random.uniform(-0.5, 0.5)
        self.air_temp = max(15.0, min(40.0, self.air_temp))
        self.air_humid += random.uniform(-2, 2)
        self.air_humid = max(30.0, min(95.0, self.air_humid))
        self.soil_temp += random.uniform(-0.3, 0.3)
        self.soil_temp = max(10.0, min(35.0, self.soil_temp))
        self.soil_humid += random.uniform(-1, 1)
        self.soil_humid = max(20.0, min(80.0, self.soil_humid))
        self.light += random.randint(-200, 200)
        self.light = max(0, min(12000, self.light))
        self.co2 += random.randint(-10, 10)
        self.co2 = max(200, min(800, self.co2))


class AgriMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能农业大棚监控系统")
        self.root.geometry("1050x700")
        self.root.configure(bg="#0a1628")

        self.zones = []
        for i, name in enumerate(ZONES):
            self.zones.append(GreenhouseZone(name, i))

        self.zone_labels = []
        self._build_ui()
        self._update_clock()
        self._start_data_loop()

    def _build_ui(self):
        # 顶部
        header = tk.Frame(self.root, bg="#1b4332", height=50)
        header.pack(fill="x")
        tk.Label(header, text="智能农业大棚监控系统", font=("微软雅黑", 20, "bold"),
                 fg="#52b788", bg="#1b4332").pack(side="left", padx=20)
        self.clock_label = tk.Label(header, text="", font=("微软雅黑", 12), fg="#aaa", bg="#1b4332")
        self.clock_label.pack(side="right", padx=20)

        main = tk.Frame(self.root, bg="#0a1628")
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧 - 传感器与区域
        left = tk.Frame(main, bg="#0a1628")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 传感器概览
        tk.Label(left, text="环境传感器", font=("微软雅黑", 13, "bold"),
                 fg="#52b788", bg="#0a1628").pack(anchor="w", pady=(0, 5))
        sensor_frame = tk.Frame(left, bg="#0a1628")
        sensor_frame.pack(fill="x", pady=(0, 10))
        sensor_names = ["空气温度", "空气湿度", "土壤湿度", "光照强度", "CO2浓度", "土壤pH"]
        sensor_colors = ["#ff6b6b", "#4ecdc4", "#a29bfe", "#ffeaa7", "#74b9ff", "#00cec9"]
        self.sensor_labels = []
        for i in range(6):
            frame = tk.Frame(sensor_frame, bg="#112240", padx=8, pady=5)
            frame.pack(side="left", fill="x", expand=True, padx=3)
            tk.Label(frame, text=sensor_names[i], font=("微软雅黑", 9), fg="#8b949e", bg="#112240").pack()
            lbl = tk.Label(frame, text="--", font=("微软雅黑", 14, "bold"),
                           fg=sensor_colors[i], bg="#112240")
            lbl.pack()
            self.sensor_labels.append(lbl)

        # 大棚区域
        tk.Label(left, text="大棚区域", font=("微软雅黑", 13, "bold"),
                 fg="#52b788", bg="#0a1628").pack(anchor="w", pady=(0, 5))
        zone_grid = tk.Frame(left, bg="#0a1628")
        zone_grid.pack(fill="both", expand=True)
        self.zone_labels = []
        for i in range(len(ZONES)):
            row = i // 3
            col = i % 3
            frame = tk.Frame(zone_grid, bg="#112240", padx=8, pady=8, bd=1, relief="solid")
            frame.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
            name_lbl = tk.Label(frame, text=ZONES[i], font=("微软雅黑", 10, "bold"),
                                fg="#52b788", bg="#112240")
            name_lbl.pack(anchor="w")
            temp_lbl = tk.Label(frame, text="温度: --°C", font=("微软雅黑", 10), fg="#ff6b6b", bg="#112240")
            temp_lbl.pack(anchor="w")
            humid_lbl = tk.Label(frame, text="湿度: --%", font=("微软雅黑", 10), fg="#4ecdc4", bg="#112240")
            humid_lbl.pack(anchor="w")
            soil_lbl = tk.Label(frame, text="土壤: --%", font=("微软雅黑", 10), fg="#a29bfe", bg="#112240")
            soil_lbl.pack(anchor="w")
            self.zone_labels.append((frame, temp_lbl, humid_lbl, soil_lbl))
            for c in range(3):
                zone_grid.columnconfigure(c, weight=1)

        # 右侧 - 控制与日志
        right = tk.Frame(main, bg="#0a1628", width=300)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # 设备控制
        tk.Label(right, text="设备控制", font=("微软雅黑", 13, "bold"),
                 fg="#52b788", bg="#0a1628").pack(anchor="w", pady=(0, 5))
        self.controls = [
            ("通风系统", False), ("补光灯", True), ("加热器", False),
            ("遮阳帘", False), ("喷灌系统", True), ("CO2发生器", False)
        ]
        self.ctrl_buttons = []
        for i, (name, on) in enumerate(self.controls):
            frame = tk.Frame(right, bg="#112240", padx=8, pady=5)
            frame.pack(fill="x", padx=5, pady=2)
            tk.Label(frame, text=name, font=("微软雅黑", 10), fg="#e0e0e0", bg="#112240").pack(side="left")
            btn_color = "#238636" if on else "#da3633"
            btn_text = "开启" if on else "关闭"
            btn = tk.Button(frame, text=btn_text, font=("微软雅黑", 9), bg=btn_color, fg="white",
                            width=6, command=lambda idx=i: self._toggle_control(idx))
            btn.pack(side="right")
            self.ctrl_buttons.append((btn, name, on))

        ttk.Separator(right).pack(fill="x", padx=10, pady=8)

        # 灌溉控制
        tk.Label(right, text="灌溉控制", font=("微软雅黑", 13, "bold"),
                 fg="#52b788", bg="#0a1628").pack(anchor="w", pady=(0, 5))
        self.irrigations = [(z, False) for z in ZONES]
        self.irr_buttons = []
        for i, (name, on) in enumerate(self.irrigations):
            frame = tk.Frame(right, bg="#112240", padx=8, pady=4)
            frame.pack(fill="x", padx=5, pady=2)
            tk.Label(frame, text=name, font=("微软雅黑", 9), fg="#8b949e", bg="#112240").pack(side="left")
            btn = tk.Button(frame, text="启动", font=("微软雅黑", 8), bg="#238636", fg="white",
                            width=5, command=lambda idx=i: self._toggle_irr(idx))
            btn.pack(side="right")
            self.irr_buttons.append((btn, name, on))

        ttk.Separator(right).pack(fill="x", padx=10, pady=8)

        # 日志
        tk.Label(right, text="系统日志", font=("微软雅黑", 12, "bold"),
                 fg="#52b788", bg="#0a1628").pack(anchor="w", pady=(0, 5))
        self.log_text = tk.Text(right, height=8, font=("微软雅黑", 9), bg="#112240", fg="#e0e0e6",
                                state="disabled", relief="flat")
        self.log_text.pack(fill="both", expand=True, padx=5)

    def _update_data(self):
        for zone in self.zones:
            zone.update_data()

        # 更新传感器概览 (第一个区域的平均值)
        avg_temp = sum(z.air_temp for z in self.zones) / len(self.zones)
        avg_humid = sum(z.air_humid for z in self.zones) / len(self.zones)
        avg_soil = sum(z.soil_humid for z in self.zones) / len(self.zones)
        avg_light = sum(z.light for z in self.zones) / len(self.zones)
        avg_co2 = sum(z.co2 for z in self.zones) / len(self.zones)

        self.sensor_labels[0].configure(text="%.1f°C" % avg_temp)
        self.sensor_labels[1].configure(text="%.1f%%" % avg_humid)
        self.sensor_labels[2].configure(text="%.1f%%" % avg_soil)
        self.sensor_labels[3].configure(text="%.0f lux" % avg_light)
        self.sensor_labels[4].configure(text="%.0f ppm" % avg_co2)
        self.sensor_labels[5].configure(text="%.1f" % 6.8)

        # 更新区域
        for i, zone in enumerate(self.zones):
            if i < len(self.zone_labels):
                _, temp_lbl, humid_lbl, soil_lbl = self.zone_labels[i]
                temp_lbl.configure(text="温度: %.1f°C" % zone.air_temp)
                humid_lbl.configure(text="湿度: %.1f%%" % zone.air_humid)
                soil_lbl.configure(text="土壤: %.1f%%" % zone.soil_humid)

    def _toggle_control(self, idx):
        btn, name, on = self.ctrl_buttons[idx]
        new_on = not on
        self.ctrl_buttons[idx] = (btn, name, new_on)
        if new_on:
            btn.configure(text="关闭", bg="#da3633")
            self._log("开启 %s" % name)
        else:
            btn.configure(text="开启", bg="#238636")
            self._log("关闭 %s" % name)
        self._send_control(name, "on" if new_on else "off")

    def _toggle_irr(self, idx):
        btn, name, on = self.irr_buttons[idx]
        new_on = not on
        self.irr_buttons[idx] = (btn, name, new_on)
        if new_on:
            btn.configure(text="停止", bg="#da3633")
            self._log("启动灌溉: %s" % name)
        else:
            btn.configure(text="启动", bg="#238636")
            self._log("停止灌溉: %s" % name)

    def _log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = "[%s] %s" % (ts, msg)
        self.log_text.configure(state="normal")
        self.log_text.insert("1.0", line + "\n")
        self.log_text.configure(state="disabled")

    def _upload_data(self):
        def _do():
            try:
                for zone in self.zones:
                    data = json.dumps({
                        "zone_id": zone.zone_id,
                        "air_temp": round(zone.air_temp, 1),
                        "air_humid": round(zone.air_humid, 1),
                        "soil_temp": round(zone.soil_temp, 1),
                        "soil_humid": round(zone.soil_humid, 1),
                        "light": round(zone.light, 0),
                        "co2": round(zone.co2, 0),
                        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        "%s/v4/datas" % API_URL, data=data,
                        headers={"Content-Type": "application/json",
                                 "Authorization": "Bearer %s" % API_TOKEN}
                    )
                    urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _send_control(self, device, action):
        def _do():
            try:
                data = json.dumps({
                    "device": device, "action": action,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }).encode("utf-8")
                req = urllib.request.Request(
                    "%s/v4/datas" % API_URL, data=data,
                    headers={"Content-Type": "application/json",
                             "Authorization": "Bearer %s" % API_TOKEN}
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _start_data_loop(self):
        def _loop():
            while True:
                self.root.after(0, self._update_data)
                self.root.after(0, self._upload_data)
                time.sleep(3)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def _update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.configure(text=now)
        self.root.after(1000, self._update_clock)


if __name__ == "__main__":
    root = tk.Tk()
    app = AgriMonitorApp(root)
    root.mainloop()