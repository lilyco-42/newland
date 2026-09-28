# -*- coding: utf-8 -*-
"""套2 2-6 钻井深度监测 - Python 3.6 兼容
任务要求：
- 每秒采集超声波数据，显示在界面+折线图（最近30次）
- 超声波>=50cm -> 频闪红灯亮，<50cm -> 常亮绿灯亮
- 红灯/绿灯亮时界面显示动画，灭时显示灭图标
- 导出Excel（最近50条，按时间倒序，含时间和超声波数据两列）
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

# Excel导出
try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

# GUI
try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
    import matplotlib
    matplotlib.use("TkAgg")
    from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
    from matplotlib.figure import Figure
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

# 云平台
CLOUD_BASE = "http://api.nlecloud.com"
CLOUD_USER = "13329262958"
CLOUD_PASS = "qwe123456789"


class CloudClient:
    def __init__(self):
        self.token = ""

    def login(self):
        if not requests:
            return False
        try:
            r = requests.post("%s/Users/Login" % CLOUD_BASE,
                json={"Account": CLOUD_USER, "Password": CLOUD_PASS, "IsRememberMe": True},
                timeout=5)
            data = r.json()
            if data["Status"] == 0:
                self.token = data["ResultObj"]["AccessToken"]
                return True
        except Exception:
            pass
        return False

    def get_sensor_data(self, device_id, api_tag):
        if not self.token or not requests:
            return None
        try:
            r = requests.get("%s/Devices/%s/Datas" % (CLOUD_BASE, device_id),
                headers={"AccessToken": self.token},
                params={"ApiTags": api_tag}, timeout=5)
            data = r.json()
            if data["Status"] == 0 and data["ResultObj"]:
                for item in data["ResultObj"].get("PageSet", []):
                    if item.get("ApiTag", "").lower() == api_tag.lower():
                        return float(item.get("Value", 0))
        except Exception:
            pass
        return None

    def send_command(self, device_id, api_tag, value):
        if not self.token or not requests:
            return
        try:
            requests.post("%s/Cmds" % CLOUD_BASE,
                headers={"AccessToken": self.token},
                params={"deviceId": device_id, "apiTag": api_tag},
                json=value, timeout=5)
        except Exception:
            pass


class DrillingMonitor:
    """钻井深度监测系统"""
    def __init__(self):
        self.data_history = collections.deque(maxlen=30)
        self.time_history = collections.deque(maxlen=30)
        self.excel_data = []  # 最近50条
        self.cloud = CloudClient()
        self.running = False
        self.root = None

    def simulate_data(self):
        """模拟超声波数据（赛场用真实传感器）"""
        return random.uniform(20, 80)

    def get_distance(self):
        """获取超声波距离"""
        # 尝试从云平台获取
        val = self.cloud.get_sensor_data(1, "m_ultrasonic")
        if val is not None:
            return val
        # 模拟数据
        return self.simulate_data()

    def check_lights(self, distance):
        """根据距离控制灯光"""
        red_on = distance >= 50
        green_on = distance < 50
        return red_on, green_on

    def export_excel(self):
        """导出最近50条数据到Excel"""
        if not Workbook:
            print("[ERR] openpyxl not installed")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="导出超声波数据")
        if not filepath:
            return
        wb = Workbook()
        ws = wb.active
        ws.title = "超声波监测数据"
        ws.append(["时间", "超声波数据(cm)"])
        # 按时间倒序
        records = sorted(self.excel_data[-50:], key=lambda x: x[0], reverse=True)
        for t, v in records:
            ws.append([t, round(v, 2)])
        wb.save(filepath)
        print("[OK] 导出 %d 条 -> %s" % (len(records), filepath))

    def build_gui(self):
        """构建GUI"""
        self.root = tk.Tk()
        self.root.title("钻井深度监测系统")
        self.root.geometry("800x600")

        # 标题
        tk.Label(self.root, text="钻井深度监测系统", font=("微软雅黑", 16, "bold")).pack(pady=10)

        # 数据显示区
        data_frame = tk.Frame(self.root)
        data_frame.pack(pady=5)

        tk.Label(data_frame, text="超声波距离:", font=("微软雅黑", 12)).pack(side=tk.LEFT)
        self.dist_label = tk.Label(data_frame, text="-- cm", font=("微软雅黑", 14, "bold"), fg="blue")
        self.dist_label.pack(side=tk.LEFT, padx=10)

        tk.Label(data_frame, text="采集时间:", font=("微软雅黑", 12)).pack(side=tk.LEFT)
        self.time_label = tk.Label(data_frame, text="--:--:--", font=("微软雅黑", 12))
        self.time_label.pack(side=tk.LEFT, padx=10)

        # 灯光状态
        light_frame = tk.Frame(self.root)
        light_frame.pack(pady=5)
        self.red_canvas = tk.Canvas(light_frame, width=40, height=40, bg="gray")
        self.red_canvas.pack(side=tk.LEFT, padx=10)
        tk.Label(light_frame, text="频闪红灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.green_canvas = tk.Canvas(light_frame, width=40, height=40, bg="gray")
        self.green_canvas.pack(side=tk.LEFT, padx=10)
        tk.Label(light_frame, text="常亮绿灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)

        # 折线图
        self.fig = Figure(figsize=(7, 3), dpi=100)
        self.ax = self.fig.add_subplot(111)
        self.ax.set_title("超声波数据-时间")
        self.ax.set_xlabel("时间")
        self.ax.set_ylabel("距离(cm)")
        self.ax.set_ylim(0, 100)
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.root)
        self.canvas.get_tk_widget().pack(pady=10)

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="启动监测", command=self.start_monitor,
                  font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="停止监测", command=self.stop_monitor,
                  font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="导出Excel", command=self.export_excel,
                  font=("微软雅黑", 10), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)

    def update_display(self, distance, red_on, green_on):
        """更新界面显示"""
        now = time.strftime("%H:%M:%S")
        self.dist_label.config(text="%.1f cm" % distance)
        self.time_label.config(text=now)

        # 红灯动画
        if red_on:
            self.red_canvas.config(bg="red")
        else:
            self.red_canvas.config(bg="gray")

        # 绿灯
        if green_on:
            self.green_canvas.config(bg="green")
        else:
            self.green_canvas.config(bg="gray")

        # 更新折线图
        self.data_history.append(distance)
        self.time_history.append(now)
        self.ax.clear()
        self.ax.set_title("超声波数据-时间")
        self.ax.set_ylabel("距离(cm)")
        self.ax.set_ylim(0, 100)
        if self.data_history:
            self.ax.plot(list(self.time_history), list(self.data_history), "b-o", markersize=3)
            self.ax.axhline(y=50, color="r", linestyle="--", label="阈值50cm")
            self.ax.legend()
        self.fig.autofmt_xdate()
        self.canvas.draw()

        # 记录数据
        self.excel_data.append((now, distance))

    def monitor_loop(self):
        """监测循环"""
        while self.running:
            distance = self.get_distance()
            red_on, green_on = self.check_lights(distance)

            # 控制云平台设备
            self.cloud.send_command(1, "m_strobe_red", {"value": "1" if red_on else "0"})
            self.cloud.send_command(1, "m_steady_green", {"value": "1" if green_on else "0"})

            # 更新GUI
            if self.root:
                self.root.after(0, self.update_display, distance, red_on, green_on)

            time.sleep(1)

    def start_monitor(self):
        if not self.running:
            self.running = True
            self.cloud.login()
            t = threading.Thread(target=self.monitor_loop, daemon=True)
            t.start()

    def stop_monitor(self):
        self.running = False

    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            # 无GUI模式（命令行）
            print("钻井深度监测系统（命令行模式）")
            self.cloud.login()
            self.running = True
            while self.running:
                try:
                    distance = self.get_distance()
                    red_on, green_on = self.check_lights(distance)
                    now = time.strftime("%H:%M:%S")
                    print("[%s] 距离:%.1fcm 红灯:%s 绿灯:%s" % (
                        now, distance, "ON" if red_on else "OFF",
                        "ON" if green_on else "OFF"))
                    self.excel_data.append((now, distance))
                    time.sleep(1)
                except KeyboardInterrupt:
                    break


if __name__ == "__main__":
    app = DrillingMonitor()
    app.run()
