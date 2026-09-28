# -*- coding: utf-8 -*-
"""套9 2-6 气象系统 - Python 3.6 兼容
任务要求：
- 5个传感器：温度、湿度、光照、CO2、噪音
- 10秒采集一次，显示在LED屏幕
- LED显示格式：温度 xx，湿度 xx，光照 xx，CO2 xx，噪音 xx
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
    def get_sensor_data(self, device_id, api_tags):
        if not self.token or not requests: return {}
        try:
            r = requests.get("%s/Devices/%s/Datas" % (CLOUD_BASE, device_id),
                headers={"AccessToken": self.token},
                params={"ApiTags": api_tags}, timeout=5)
            data = r.json()
            result = {}
            if data["Status"] == 0 and data["ResultObj"]:
                for item in data["ResultObj"].get("PageSet", []):
                    tag = item.get("ApiTag", "")
                    val = item.get("Value", "")
                    if tag and val:
                        result[tag] = val
            return result
        except: pass
        return {}


class WeatherStation:
    """气象系统"""
    SENSOR_TAGS = {
        "temperature": "温度",
        "humidity": "湿度",
        "light": "光照",
        "co2": "CO2",
        "noise": "噪音",
    }

    def __init__(self):
        self.data = {k: 0 for k in self.SENSOR_TAGS}
        self.cloud = CloudClient()
        self.running = False
        self.root = None
        self.led_text = ""

    def read_sensors(self):
        """读取传感器数据"""
        vals = self.cloud.get_sensor_data(1, ",".join(self.SENSOR_TAGS.keys()))
        for tag in self.SENSOR_TAGS:
            if tag in vals:
                try:
                    self.data[tag] = float(vals[tag])
                except:
                    self.data[tag] = 0
            else:
                # 模拟数据
                if tag == "temperature":
                    self.data[tag] = random.uniform(20, 35)
                elif tag == "humidity":
                    self.data[tag] = random.uniform(40, 80)
                elif tag == "light":
                    self.data[tag] = random.uniform(100, 8000)
                elif tag == "co2":
                    self.data[tag] = random.uniform(300, 800)
                elif tag == "noise":
                    self.data[tag] = random.uniform(30, 70)

    def format_led(self):
        """格式化LED显示内容"""
        parts = []
        for tag, name in self.SENSOR_TAGS.items():
            val = self.data[tag]
            if tag == "temperature":
                parts.append("%s %.1f" % (name, val))
            elif tag == "humidity":
                parts.append("%s %.1f" % (name, val))
            elif tag == "light":
                parts.append("%s %d" % (name, int(val)))
            elif tag == "co2":
                parts.append("%s %d" % (name, int(val)))
            elif tag == "noise":
                parts.append("%s %.1f" % (name, val))
        return "，".join(parts)

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("气象系统")
        self.root.geometry("600x400")

        tk.Label(self.root, text="气象系统", font=("微软雅黑", 16, "bold")).pack(pady=10)

        # LED显示屏模拟
        led_frame = tk.Frame(self.root, bg="black", bd=2, relief=tk.SUNKEN)
        led_frame.pack(pady=10, padx=20, fill=tk.X)
        self.led_label = tk.Label(led_frame, text="", font=("Consolas", 14),
                                  bg="black", fg="#00ff00", anchor=tk.W, padx=10)
        self.led_label.pack(fill=tk.X, pady=10)

        # 传感器数据卡片
        card_frame = tk.Frame(self.root)
        card_frame.pack(pady=10, fill=tk.X, padx=20)
        self.sensor_labels = {}
        for i, (tag, name) in enumerate(self.SENSOR_TAGS.items()):
            f = tk.Frame(card_frame, bd=1, relief=tk.RAISED, padx=8, pady=5)
            f.grid(row=i//3, column=i%3, padx=5, pady=5, sticky=tk.W+tk.E)
            tk.Label(f, text=name, font=("微软雅黑", 10)).pack()
            lbl = tk.Label(f, text="--", font=("微软雅黑", 14, "bold"), fg="blue")
            lbl.pack()
            self.sensor_labels[tag] = lbl

        # 刷新时间
        self.refresh_label = tk.Label(self.root, text="上次刷新: --", font=("微软雅黑", 9))
        self.refresh_label.pack(pady=5)

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="启动", command=self.start,
                  font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="停止", command=self.stop,
                  font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

    def update_display(self):
        for tag, lbl in self.sensor_labels.items():
            val = self.data[tag]
            if tag in ("temperature", "humidity", "noise"):
                lbl.config(text="%.1f" % val)
            else:
                lbl.config(text="%d" % int(val))
        self.led_text = self.format_led()
        self.led_label.config(text=self.led_text)
        self.refresh_label.config(text="上次刷新: %s" % time.strftime("%H:%M:%S"))

    def monitor_loop(self):
        while self.running:
            self.read_sensors()
            if self.root:
                self.root.after(0, self.update_display)
            # 输出到LED（赛场真实LED屏）
            print("[LED] %s" % self.format_led())
            time.sleep(10)

    def start(self):
        if not self.running:
            self.running = True
            self.cloud.login()
            t = threading.Thread(target=self.monitor_loop, daemon=True)
            t.start()

    def stop(self):
        self.running = False

    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            print("气象系统（命令行模式）")
            self.cloud.login()
            self.running = True
            while self.running:
                try:
                    self.read_sensors()
                    print("[%s] %s" % (time.strftime("%H:%M:%S"), self.format_led()))
                    time.sleep(10)
                except KeyboardInterrupt:
                    break


if __name__ == "__main__":
    ws = WeatherStation()
    ws.run()
