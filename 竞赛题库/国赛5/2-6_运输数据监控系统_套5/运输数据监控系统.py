# -*- coding: utf-8 -*-
"""套5 2-6 运输数据监控系统 - Python 3.6 兼容
任务要求：
- 云平台温湿度+光照传感器数据
- 光照被遮挡时开灯+风扇动画
- 拿开遮挡关闭灯和风扇
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

class TransportMonitor:
    """运输数据监控系统"""
    def __init__(self):
        self.cloud = CloudClient()
        self.temp = 0.0
        self.hum = 0.0
        self.light = 0
        self.light_blocked = False
        self.fan_on = False
        self.lamp_on = False
        self.running = False
        self.root = None
        self.fan_angle = 0

    def read_sensors(self):
        val = self.cloud.get_sensor_data(1, "m_temp")
        self.temp = float(val) if val else random.uniform(20, 35)
        val = self.cloud.get_sensor_data(1, "m_hum")
        self.hum = float(val) if val else random.uniform(40, 80)
        val = self.cloud.get_sensor_data(1, "m_light")
        self.light = int(float(val)) if val else random.randint(10, 5000)
        self.light_blocked = self.light < 100

    def control_devices(self):
        if self.light_blocked:
            self.lamp_on = True
            self.fan_on = True
            self.cloud.send_command(1, "m_lamp", {"value": "1"})
            self.cloud.send_command(1, "m_fan", {"value": "1"})
        else:
            self.lamp_on = False
            self.fan_on = False
            self.cloud.send_command(1, "m_lamp", {"value": "0"})
            self.cloud.send_command(1, "m_fan", {"value": "0"})

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("运输数据监控系统")
        self.root.geometry("650x500")
        tk.Label(self.root, text="运输数据监控系统", font=("微软雅黑", 16, "bold")).pack(pady=10)
        data_frame = tk.Frame(self.root)
        data_frame.pack(pady=5)
        tk.Label(data_frame, text="温度:", font=("微软雅黑", 11)).pack(side=tk.LEFT)
        self.temp_lbl = tk.Label(data_frame, text="--", font=("微软雅黑", 13, "bold"), fg="red")
        self.temp_lbl.pack(side=tk.LEFT, padx=5)
        tk.Label(data_frame, text="湿度:", font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=10)
        self.hum_lbl = tk.Label(data_frame, text="--", font=("微软雅黑", 13, "bold"), fg="blue")
        self.hum_lbl.pack(side=tk.LEFT, padx=5)
        tk.Label(data_frame, text="光照:", font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=10)
        self.light_lbl = tk.Label(data_frame, text="--", font=("微软雅黑", 13, "bold"))
        self.light_lbl.pack(side=tk.LEFT, padx=5)
        # 设备状态
        dev_frame = tk.Frame(self.root, bd=1, relief=tk.GROOVE, padx=10, pady=5)
        dev_frame.pack(pady=10, fill=tk.X, padx=20)
        tk.Label(dev_frame, text="设备状态", font=("微软雅黑", 11, "bold")).pack(anchor=tk.W)
        self.lamp_canvas = tk.Canvas(dev_frame, width=40, height=40, bg="gray")
        self.lamp_canvas.pack(side=tk.LEFT, padx=10)
        tk.Label(dev_frame, text="灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.fan_canvas = tk.Canvas(dev_frame, width=50, height=50, bg="white")
        self.fan_canvas.pack(side=tk.LEFT, padx=15)
        tk.Label(dev_frame, text="风扇", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.block_label = tk.Label(dev_frame, text="光照正常", font=("微软雅黑", 10), fg="green")
        self.block_label.pack(side=tk.LEFT, padx=15)
        # 按钮
        btn = tk.Frame(self.root)
        btn.pack(pady=10)
        tk.Button(btn, text="启动", command=self.start, font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn, text="停止", command=self.stop, font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

    def update_display(self):
        self.temp_lbl.config(text="%.1f℃" % self.temp)
        self.hum_lbl.config(text="%.1f%%" % self.hum)
        self.light_lbl.config(text="%d lux" % self.light)
        self.lamp_canvas.config(bg="yellow" if self.lamp_on else "gray")
        if self.fan_on:
            self.fan_angle = (self.fan_angle + 30) % 360
            self.fan_canvas.delete("all")
            self.fan_canvas.create_text(25, 25, text="F", font=("Arial", 16, "bold"), angle=self.fan_angle)
        else:
            self.fan_canvas.delete("all")
            self.fan_canvas.create_text(25, 25, text="F", font=("Arial", 16), fill="gray")
        self.block_label.config(text="光被遮挡！" if self.light_blocked else "光照正常",
                                fg="red" if self.light_blocked else "green")

    def monitor_loop(self):
        while self.running:
            self.read_sensors()
            self.control_devices()
            if self.root:
                self.root.after(0, self.update_display)
            time.sleep(1)

    def start(self):
        if not self.running:
            self.running = True
            self.cloud.login()
            threading.Thread(target=self.monitor_loop, daemon=True).start()
    def stop(self):
        self.running = False
    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            self.cloud.login()
            self.running = True
            while self.running:
                try:
                    self.read_sensors()
                    self.control_devices()
                    print("[%s] T:%.1f H:%.1f L:%d blocked=%s" % (time.strftime("%H:%M:%S"), self.temp, self.hum, self.light, self.light_blocked))
                    time.sleep(1)
                except KeyboardInterrupt:
                    break

if __name__ == "__main__":
    TransportMonitor().run()
