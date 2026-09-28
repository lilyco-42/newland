# -*- coding: utf-8 -*-
"""套8 2-7 智能门禁系统 - Python 3.6 兼容
任务要求：
- RFID检测+电动推杆门+行程开关+接近开关+红外对射+LED显示屏
- 注册卡开门/非注册不开门+LED显示信息
- 云系统上报
"""
import os, sys, time, random, threading
try:
    import requests
except ImportError:
    requests = None
try:
    import tkinter as tk
    from tkinter import messagebox
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
                self.token = r.json()["ResultObj"]["AccessToken"]; return True
        except: pass
        return False
    def send_command(self, device_id, api_tag, value):
        if not self.token or not requests: return
        try:
            requests.post("%s/Cmds" % CLOUD_BASE, headers={"AccessToken": self.token},
                params={"deviceId": device_id, "apiTag": api_tag}, json=value, timeout=5)
        except: pass
    def get_sensor_data(self, device_id, api_tag):
        if not self.token or not requests: return None
        try:
            r = requests.get("%s/Devices/%s/Datas" % (CLOUD_BASE, device_id),
                headers={"AccessToken": self.token}, params={"ApiTags": api_tag}, timeout=5)
            data = r.json()
            if data["Status"] == 0 and data["ResultObj"]:
                for item in data["ResultObj"].get("PageSet", []):
                    if item.get("ApiTag", "").lower() == api_tag.lower(): return item.get("Value", "")
        except: pass
        return None

class SmartDoor:
    REGISTERED = {"RFID_001": "张三", "RFID_002": "李四"}
    def __init__(self):
        self.cloud = CloudClient()
        self.door_open = False; self.running = False; self.root = None
        self.led_text = "请刷卡"

    def on_card(self, rfid):
        name = self.REGISTERED.get(rfid)
        if name:
            self.open_door()
            self.led_text = "欢迎 %s" % name
        else:
            self.close_door()
            self.led_text = "未注册"
        if self.root: self.root.after(0, self.refresh_gui)

    def open_door(self):
        self.door_open = True
        self.cloud.send_command(1, "m_pushrod_back", {"value": "1"})
        self.cloud.send_command(1, "m_pushrod_putt", {"value": "0"})
        self.cloud.send_command(1, "m_multi_green", {"value": "1"})
        self.cloud.send_command(1, "m_multi_red", {"value": "0"})

    def close_door(self):
        self.door_open = False
        self.cloud.send_command(1, "m_pushrod_putt", {"value": "1"})
        self.cloud.send_command(1, "m_pushrod_back", {"value": "0"})
        self.cloud.send_command(1, "m_multi_green", {"value": "0"})
        self.cloud.send_command(1, "m_multi_red", {"value": "1"})

    def refresh_gui(self):
        if not hasattr(self, 'status_label'): return
        s = "开门" if self.door_open else "关门"
        c = "green" if self.door_open else "red"
        self.status_label.config(text="当前: %s" % s, fg=c)
        self.led_label.config(text=self.led_text)
        self.door_canvas.config(bg="#90EE90" if self.door_open else "#D3D3D3")

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("智能门禁系统"); self.root.geometry("550x450")
        tk.Label(self.root, text="智能门禁系统", font=("微软雅黑", 16, "bold")).pack(pady=10)
        self.door_canvas = tk.Canvas(self.root, width=200, height=100, bg="#D3D3D3")
        self.door_canvas.pack(pady=5)
        self.door_canvas.create_text(100, 50, text="门", font=("微软雅黑", 14))
        self.status_label = tk.Label(self.root, text="当前: 关门", font=("微软雅黑", 12))
        self.status_label.pack(pady=3)
        lf = tk.Frame(self.root, bg="black", bd=2, relief=tk.SUNKEN)
        lf.pack(pady=10, padx=30, fill=tk.X)
        self.led_label = tk.Label(lf, text="请刷卡", font=("Consolas", 16), bg="black", fg="#00ff00")
        self.led_label.pack(pady=8)
        cf = tk.Frame(self.root); cf.pack(pady=10)
        tk.Label(cf, text="模拟读卡:", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        for rfid, name in self.REGISTERED.items():
            tk.Button(cf, text="%s(%s)" % (rfid, name),
                      command=lambda r=rfid: self.on_card(r),
                      font=("微软雅黑", 9), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=3)
        tk.Button(cf, text="未知卡", command=lambda: self.on_card("RFID_XXX"),
                  font=("微软雅黑", 9), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=3)
        bf = tk.Frame(self.root); bf.pack(pady=5)
        tk.Button(bf, text="启动监听", command=self.start, font=("微软雅黑", 10), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)

    def monitor_loop(self):
        while self.running:
            val = self.cloud.get_sensor_data(1, "m_rfid")
            if val: self.on_card(val)
            time.sleep(1)

    def start(self):
        if not self.running:
            self.running = True; self.cloud.login()
            threading.Thread(target=self.monitor_loop, daemon=True).start()
    def run(self):
        if HAS_GUI: self.build_gui(); self.root.mainloop()
        else:
            self.cloud.login(); self.running = True
            while self.running:
                try:
                    rfid = input("RFID: ").strip()
                    if rfid: self.on_card(rfid)
                except (KeyboardInterrupt, EOFError): break

if __name__ == "__main__":
    SmartDoor().run()
