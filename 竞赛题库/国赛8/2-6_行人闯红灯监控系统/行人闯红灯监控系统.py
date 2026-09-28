# -*- coding: utf-8 -*-
"""套8 2-6 行人闯红灯监控系统 - Python 3.6 兼容
任务要求：
- 微动开关控制红绿灯
- 红外对射检测行人
- 三种状态：绿灯放行/红灯禁止/行人闯红灯
- TCP串口服务器COM3控制ZigBee D4/D3/D6灯同步
"""
import os, sys, time, random, threading
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
                self.token = r.json()["ResultObj"]["AccessToken"]; return True
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
                    if item.get("ApiTag", "").lower() == api_tag.lower(): return item.get("Value", "")
        except: pass
        return None
    def send_command(self, device_id, api_tag, value):
        if not self.token or not requests: return
        try:
            requests.post("%s/Cmds" % CLOUD_BASE, headers={"AccessToken": self.token},
                params={"deviceId": device_id, "apiTag": api_tag}, json=value, timeout=5)
        except: pass

class PedestrianMonitor:
    """行人闯红灯监控系统"""
    # 状态: green=绿灯放行, red=红灯禁止, violation=行人闯红灯
    def __init__(self):
        self.cloud = CloudClient()
        self.state = "green"
        self.running = False; self.root = None

    def read_sensors(self):
        # 行程开关：默认闭合=绿灯，断开=红灯
        sw = self.cloud.get_sensor_data(1, "m_travelSwitch_singleWheel")
        is_red = sw in ("0", "false")
        # 红外对射
        ir = self.cloud.get_sensor_data(1, "m_light_curtain")
        ir_alarm = ir not in ("0", "false", "", None)

        if not is_red:
            self.state = "green"
        elif is_red and not ir_alarm:
            self.state = "red"
        elif is_red and ir_alarm:
            self.state = "violation"

    def control_lights(self):
        if self.state == "green":
            self.cloud.send_command(1, "m_multi_green", {"value": "1"})
            self.cloud.send_command(1, "m_multi_red", {"value": "0"})
            self.cloud.send_command(1, "m_multi_yellow", {"value": "0"})
        elif self.state in ("red", "violation"):
            self.cloud.send_command(1, "m_multi_red", {"value": "1"})
            self.cloud.send_command(1, "m_multi_green", {"value": "0"})
            self.cloud.send_command(1, "m_multi_yellow", {"value": "0"})

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("行人闯红灯监控系统"); self.root.geometry("650x480")
        tk.Label(self.root, text="行人闯红灯监控系统", font=("微软雅黑", 16, "bold")).pack(pady=10)
        # 状态图片区
        self.state_label = tk.Label(self.root, text="[绿灯放行]", bg="green", fg="white",
                                     font=("微软雅黑", 18, "bold"), width=30, height=6)
        self.state_label.pack(pady=10)
        # 红绿灯
        lf = tk.Frame(self.root); lf.pack(pady=5)
        self.red_canvas = tk.Canvas(lf, width=40, height=40, bg="gray")
        self.red_canvas.pack(side=tk.LEFT, padx=5)
        tk.Label(lf, text="红灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.green_canvas = tk.Canvas(lf, width=40, height=40, bg="gray")
        self.green_canvas.pack(side=tk.LEFT, padx=10)
        tk.Label(lf, text="绿灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        # 模拟按钮
        bf = tk.Frame(self.root); bf.pack(pady=10)
        tk.Button(bf, text="绿灯", command=lambda: self.set_state("green"),
                  font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="红灯", command=lambda: self.set_state("red"),
                  font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="行人闯入", command=lambda: self.set_state("violation"),
                  font=("微软雅黑", 10), bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="启动", command=self.start, font=("微软雅黑", 10), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)

    def set_state(self, s):
        self.state = s; self.update_display(); self.control_lights()

    def update_display(self):
        if self.state == "green":
            self.state_label.config(text="[绿灯放行]", bg="green")
            self.red_canvas.config(bg="gray"); self.green_canvas.config(bg="green")
        elif self.state == "red":
            self.state_label.config(text="[红灯禁止]", bg="red")
            self.red_canvas.config(bg="red"); self.green_canvas.config(bg="gray")
        elif self.state == "violation":
            self.state_label.config(text="[行人闯红灯！]", bg="orange")
            self.red_canvas.config(bg="red"); self.green_canvas.config(bg="gray")

    def monitor_loop(self):
        while self.running:
            self.read_sensors()
            self.control_lights()
            if self.root: self.root.after(0, self.update_display)
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
                try: self.read_sensors(); self.control_lights(); time.sleep(1)
                except KeyboardInterrupt: break

if __name__ == "__main__":
    PedestrianMonitor().run()
