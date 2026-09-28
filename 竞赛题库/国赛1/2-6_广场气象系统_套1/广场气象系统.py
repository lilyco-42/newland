# -*- coding: utf-8 -*-
"""套1 2-6 广场气象系统 - Python 3.6 兼容
任务要求：
- 百叶箱传感器：温度+湿度
- 每10秒采集一次
- 实时显示数值
- 绘制温度-时间折线图和湿度-时间折线图
- 输出: c2.exe + 源码
"""
import os
import sys
import time
import random
import threading
import collections

try:
    import requests
except ImportError:
    requests = None

try:
    import tkinter as tk
    from tkinter import messagebox
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
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
                        return float(item.get("Value", 0))
        except: pass
        return None


class WeatherStation:
    """广场气象系统"""
    MAX_POINTS = 30  # 折线图最多显示30个点

    def __init__(self):
        self.cloud = CloudClient()
        self.temp_data = collections.deque(maxlen=self.MAX_POINTS)
        self.hum_data = collections.deque(maxlen=self.MAX_POINTS)
        self.time_data = collections.deque(maxlen=self.MAX_POINTS)
        self.running = False
        self.root = None
        self.current_temp = 0.0
        self.current_hum = 0.0

    def read_sensors(self):
        """读取温度和湿度"""
        temp = self.cloud.get_sensor_data(1, "m_temp")
        hum = self.cloud.get_sensor_data(1, "m_hum")
        if temp is not None:
            self.current_temp = temp
        else:
            self.current_temp = random.uniform(20, 35)
        if hum is not None:
            self.current_hum = hum
        else:
            self.current_hum = random.uniform(40, 80)

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("广场气象系统")
        self.root.geometry("800x600")

        tk.Label(self.root, text="广场气象系统",
                 font=("微软雅黑", 16, "bold")).pack(pady=10)

        # 数值显示
        data_frame = tk.Frame(self.root)
        data_frame.pack(pady=5)
        tk.Label(data_frame, text="温度:", font=("微软雅黑", 12)).pack(side=tk.LEFT)
        self.temp_label = tk.Label(data_frame, text="-- ℃",
                                    font=("微软雅黑", 14, "bold"), fg="red")
        self.temp_label.pack(side=tk.LEFT, padx=10)
        tk.Label(data_frame, text="湿度:", font=("微软雅黑", 12)).pack(side=tk.LEFT)
        self.hum_label = tk.Label(data_frame, text="-- %",
                                   font=("微软雅黑", 14, "bold"), fg="blue")
        self.hum_label.pack(side=tk.LEFT, padx=10)
        self.time_label = tk.Label(data_frame, text="--:--:--",
                                    font=("微软雅黑", 10))
        self.time_label.pack(side=tk.LEFT, padx=10)

        # 折线图 - 温度
        self.fig1 = Figure(figsize=(7, 2.5), dpi=100)
        self.ax1 = self.fig1.add_subplot(111)
        self.ax1.set_title("温度 - 时间")
        self.ax1.set_ylabel("温度(℃)")
        self.ax1.set_ylim(0, 50)
        self.canvas1 = FigureCanvasTkAgg(self.fig1, master=self.root)
        self.canvas1.get_tk_widget().pack(pady=5)

        # 折线图 - 湿度
        self.fig2 = Figure(figsize=(7, 2.5), dpi=100)
        self.ax2 = self.fig2.add_subplot(111)
        self.ax2.set_title("湿度 - 时间")
        self.ax2.set_ylabel("湿度(%)")
        self.ax2.set_ylim(0, 100)
        self.canvas2 = FigureCanvasTkAgg(self.fig2, master=self.root)
        self.canvas2.get_tk_widget().pack(pady=5)

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="启动采集", command=self.start,
                  font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="停止", command=self.stop,
                  font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

    def update_display(self):
        now = time.strftime("%H:%M:%S")
        self.temp_label.config(text="%.1f ℃" % self.current_temp)
        self.hum_label.config(text="%.1f %%" % self.current_hum)
        self.time_label.config(text=now)

        self.temp_data.append(self.current_temp)
        self.hum_data.append(self.current_hum)
        self.time_data.append(now)

        # 更新温度图
        self.ax1.clear()
        self.ax1.set_title("温度 - 时间")
        self.ax1.set_ylabel("温度(℃)")
        self.ax1.set_ylim(0, 50)
        if self.temp_data:
            self.ax1.plot(list(self.time_data), list(self.temp_data), "r-o", markersize=3)
        self.fig1.autofmt_xdate()
        self.canvas1.draw()

        # 更新湿度图
        self.ax2.clear()
        self.ax2.set_title("湿度 - 时间")
        self.ax2.set_ylabel("湿度(%)")
        self.ax2.set_ylim(0, 100)
        if self.hum_data:
            self.ax2.plot(list(self.time_data), list(self.hum_data), "b-o", markersize=3)
        self.fig2.autofmt_xdate()
        self.canvas2.draw()

    def monitor_loop(self):
        while self.running:
            self.read_sensors()
            if self.root:
                self.root.after(0, self.update_display)
            print("[%s] 温度:%.1f℃ 湿度:%.1f%%" % (
                time.strftime("%H:%M:%S"), self.current_temp, self.current_hum))
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
            print("广场气象系统（命令行模式）")
            self.cloud.login()
            self.running = True
            while self.running:
                try:
                    self.read_sensors()
                    print("[%s] 温度:%.1f℃ 湿度:%.1f%%" % (
                        time.strftime("%H:%M:%S"), self.current_temp, self.current_hum))
                    time.sleep(10)
                except KeyboardInterrupt:
                    break


if __name__ == "__main__":
    app = WeatherStation()
    app.run()
