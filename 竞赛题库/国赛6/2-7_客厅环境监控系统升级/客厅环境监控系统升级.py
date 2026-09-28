# -*- coding: utf-8 -*-
"""套6 2-7 客厅环境监控系统升级 - Python 3.6 兼容
任务要求：
- 温湿度+光照+人体传感器采集
- 光照<=100lux -> LED灯亮；>100lux -> LED灯灭
- 人体红外：有人/无人状态显示
- 每30秒刷新一次数据表格
"""
import os, sys, time, random, threading, collections
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
            if r.json()["Status"] == 0:
                self.token = r.json()["ResultObj"]["AccessToken"]
                return True
        except: pass
        return False
    def get_sensor_data(self, device_id, api_tag):
        if not self.token or not requests: return None
        try:
            r = requests.get("%s/Devices/%s/Datas" % (CLOUD_BASE, device_id),
                headers={"AccessToken": self.token}, params={"ApiTags": api_tag}, timeout=5)
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
                params={"deviceId": device_id, "apiTag": api_tag}, json=value, timeout=5)
        except: pass

class RoomMonitor:
    def __init__(self):
        self.cloud = CloudClient()
        self.temp = 0.0; self.hum = 0.0; self.light = 0; self.body = "无人"
        self.led_on = False; self.running = False; self.root = None
        self.data_history = []

    def read_sensors(self):
        val = self.cloud.get_sensor_data(1, "m_temp")
        self.temp = float(val) if val else random.uniform(20, 32)
        val = self.cloud.get_sensor_data(1, "m_hum")
        self.hum = float(val) if val else random.uniform(40, 75)
        val = self.cloud.get_sensor_data(1, "m_light")
        self.light = int(float(val)) if val else random.randint(10, 500)
        val = self.cloud.get_sensor_data(1, "z_body")
        self.body = "有人" if val not in ("0", "false", "", None) else "无人"
        self.led_on = self.light <= 100
        self.cloud.send_command(1, "m_lamp", {"value": "1" if self.led_on else "0"})
        now = time.strftime("%H:%M:%S")
        self.data_history.append((now, self.temp, self.hum, self.light, self.body))

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("客厅环境监控系统升级")
        self.root.geometry("700x520")
        tk.Label(self.root, text="客厅环境监控系统", font=("微软雅黑", 16, "bold")).pack(pady=10)
        cf = tk.Frame(self.root, bd=1, relief=tk.RAISED, padx=10, pady=5)
        cf.pack(pady=5, fill=tk.X, padx=20)
        self.labels = {}
        for name, unit in [("温度","℃"),("湿度","%"),("光照","lux"),("人体","")]:
            f = tk.Frame(cf); f.pack(side=tk.LEFT, padx=12)
            tk.Label(f, text=name, font=("微软雅黑", 10)).pack()
            lbl = tk.Label(f, text="--", font=("微软雅黑", 14, "bold"), fg="blue")
            lbl.pack(); self.labels[name] = lbl
        lf = tk.Frame(self.root); lf.pack(pady=5)
        self.led_canvas = tk.Canvas(lf, width=30, height=30, bg="gray")
        self.led_canvas.pack(side=tk.LEFT, padx=5)
        tk.Label(lf, text="LED灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.led_status = tk.Label(lf, text="灭", font=("微软雅黑", 10))
        self.led_status.pack(side=tk.LEFT, padx=5)
        tk.Label(self.root, text="数据记录(每30秒):", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        tf = tk.Frame(self.root); tf.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        for j, col in enumerate(("时间","温度","湿度","光照","人体")):
            tk.Label(tf, text=col, font=("微软雅黑", 9, "bold"), bd=1, relief=tk.SUNKEN, width=12).grid(row=0, column=j)
        self.rows = []
        for i in range(8):
            row = [tk.Label(tf, text="", font=("Consolas",9), bd=1, relief=tk.SUNKEN, width=12) for _ in range(5)]
            for j, lbl in enumerate(row): lbl.grid(row=i+1, column=j)
            self.rows.append(row)
        bf = tk.Frame(self.root); bf.pack(pady=5)
        tk.Button(bf, text="启动", command=self.start, font=("微软雅黑",10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="停止", command=self.stop, font=("微软雅黑",10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

    def update_display(self):
        self.labels["温度"].config(text="%.1f" % self.temp)
        self.labels["湿度"].config(text="%.1f" % self.hum)
        self.labels["光照"].config(text="%d" % self.light)
        self.labels["人体"].config(text=self.body, fg="red" if self.body=="有人" else "gray")
        self.led_canvas.config(bg="yellow" if self.led_on else "gray")
        self.led_status.config(text="亮" if self.led_on else "灭", fg="green" if self.led_on else "gray")
        recent = self.data_history[-8:]
        for i, row in enumerate(self.rows):
            if i < len(recent):
                r = recent[-(i+1)]
                for j, lbl in enumerate(row): lbl.config(text=str(r[j]))
            else:
                for lbl in row: lbl.config(text="")

    def monitor_loop(self):
        while self.running:
            self.read_sensors()
            if self.root: self.root.after(0, self.update_display)
            time.sleep(30)

    def start(self):
        if not self.running:
            self.running = True; self.cloud.login()
            threading.Thread(target=self.monitor_loop, daemon=True).start()
    def stop(self): self.running = False
    def run(self):
        if HAS_GUI: self.build_gui(); self.root.mainloop()
        else:
            self.cloud.login(); self.running = True
            while self.running:
                try: self.read_sensors(); time.sleep(30)
                except KeyboardInterrupt: break

if __name__ == "__main__":
    RoomMonitor().run()
