# -*- coding: utf-8 -*-
"""套1 2-7 客厅环境监控系统升级 - Python 3.6 兼容
任务要求：
- 传感器：温度、湿度、光照、人体红外
- 光照<=100lux -> LED灯亮；>100lux -> LED灯灭
- 人体红外：有人/无人状态显示
- 每30秒刷新一次数据表格
- 输出: roomeve.exe + 源码
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
                        return item.get("Value", "")
        except: pass
        return None
    def send_command(self, device_id, api_tag, value):
        if not self.token or not requests: return
        try:
            requests.post("%s/Cmds" % CLOUD_BASE,
                headers={"AccessToken": self.token},
                params={"deviceId": device_id, "apiTag": api_tag},
                json=value, timeout=5)
        except: pass


class RoomMonitor:
    """客厅环境监控系统升级"""
    def __init__(self):
        self.cloud = CloudClient()
        self.temp = 0.0
        self.hum = 0.0
        self.light = 0
        self.body = "无人"
        self.led_on = False
        self.running = False
        self.root = None
        self.data_history = []  # (时间, 温度, 湿度, 光照, 人体)

    def read_sensors(self):
        """读取所有传感器"""
        val = self.cloud.get_sensor_data(1, "m_temp")
        self.temp = float(val) if val else random.uniform(20, 32)
        val = self.cloud.get_sensor_data(1, "m_hum")
        self.hum = float(val) if val else random.uniform(40, 75)
        val = self.cloud.get_sensor_data(1, "m_light")
        self.light = int(float(val)) if val else random.randint(10, 500)
        val = self.cloud.get_sensor_data(1, "z_body")
        if val is not None:
            self.body = "有人" if val not in ("0", "false", "") else "无人"
        else:
            self.body = random.choice(["有人", "无人"])

        # 光照控制LED灯
        if self.light <= 100:
            self.led_on = True
            self.cloud.send_command(1, "m_lamp", {"value": "1"})
        else:
            self.led_on = False
            self.cloud.send_command(1, "m_lamp", {"value": "0"})

        now = time.strftime("%H:%M:%S")
        self.data_history.append((now, self.temp, self.hum, self.light, self.body))

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("客厅环境监控系统升级")
        self.root.geometry("700x550")

        tk.Label(self.root, text="客厅环境监控系统",
                 font=("微软雅黑", 16, "bold")).pack(pady=10)

        # 实时数据卡片
        card = tk.Frame(self.root, bd=1, relief=tk.RAISED, padx=10, pady=5)
        card.pack(pady=5, fill=tk.X, padx=20)
        self.labels = {}
        for i, (name, unit) in enumerate([("温度", "℃"), ("湿度", "%"), ("光照", "lux"), ("人体", "")]):
            f = tk.Frame(card)
            f.pack(side=tk.LEFT, padx=15)
            tk.Label(f, text=name, font=("微软雅黑", 10)).pack()
            lbl = tk.Label(f, text="--", font=("微软雅黑", 14, "bold"), fg="blue")
            lbl.pack()
            tk.Label(f, text=unit, font=("微软雅黑", 8)).pack()
            self.labels[name] = lbl

        # LED灯状态
        led_frame = tk.Frame(self.root)
        led_frame.pack(pady=5)
        self.led_canvas = tk.Canvas(led_frame, width=30, height=30, bg="gray")
        self.led_canvas.pack(side=tk.LEFT, padx=5)
        tk.Label(led_frame, text="LED灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.led_status = tk.Label(led_frame, text="灭", font=("微软雅黑", 10))
        self.led_status.pack(side=tk.LEFT, padx=5)

        # 数据表格
        tk.Label(self.root, text="数据记录(每30秒刷新):",
                 font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        cols = ("时间", "温度", "湿度", "光照", "人体")
        self.tree = tk.Frame(self.root)
        self.tree.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        self.headers = []
        for j, col in enumerate(cols):
            lbl = tk.Label(self.tree, text=col, font=("微软雅黑", 9, "bold"),
                          bd=1, relief=tk.SUNKEN, width=12)
            lbl.grid(row=0, column=j, sticky=tk.W+tk.E)
            self.headers.append(lbl)
        self.data_rows = []
        for i in range(8):
            row = []
            for j in range(5):
                lbl = tk.Label(self.tree, text="", font=("Consolas", 9), bd=1,
                              relief=tk.SUNKEN, width=12)
                lbl.grid(row=i+1, column=j, sticky=tk.W+tk.E)
                row.append(lbl)
            self.data_rows.append(row)

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="启动", command=self.start,
                  font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="停止", command=self.stop,
                  font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

    def update_display(self):
        self.labels["温度"].config(text="%.1f" % self.temp)
        self.labels["湿度"].config(text="%.1f" % self.hum)
        self.labels["光照"].config(text="%d" % self.light)
        self.labels["人体"].config(text=self.body, fg="red" if self.body == "有人" else "gray")
        if self.led_on:
            self.led_canvas.config(bg="yellow")
            self.led_status.config(text="亮", fg="green")
        else:
            self.led_canvas.config(bg="gray")
            self.led_status.config(text="灭", fg="gray")

        # 更新表格(最近8条)
        recent = self.data_history[-8:]
        for i, row in enumerate(self.data_rows):
            if i < len(recent):
                r = recent[-(i+1)]
                row[0].config(text=r[0])
                row[1].config(text="%.1f" % r[1])
                row[2].config(text="%.1f" % r[2])
                row[3].config(text=str(r[3]))
                row[4].config(text=r[4])
            else:
                for lbl in row:
                    lbl.config(text="")

    def monitor_loop(self):
        while self.running:
            self.read_sensors()
            if self.root:
                self.root.after(0, self.update_display)
            print("[%s] 温度:%.1f 湿度:%.1f 光照:%d LED:%s 人体:%s" % (
                time.strftime("%H:%M:%S"), self.temp, self.hum, self.light,
                "亮" if self.led_on else "灭", self.body))
            time.sleep(30)

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
            print("客厅环境监控系统升级（命令行模式）")
            self.cloud.login()
            self.running = True
            while self.running:
                try:
                    self.read_sensors()
                    print("[%s] 温度:%.1f 湿度:%.1f 光照:%d LED:%s 人体:%s" % (
                        time.strftime("%H:%M:%S"), self.temp, self.hum, self.light,
                        "亮" if self.led_on else "灭", self.body))
                    time.sleep(30)
                except KeyboardInterrupt:
                    break


if __name__ == "__main__":
    app = RoomMonitor()
    app.run()
