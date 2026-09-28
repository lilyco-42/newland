# -*- coding: utf-8 -*-
"""套4 2-7 大厅环境系统 - Python 3.6 兼容
任务要求：
- ZigBee温湿度+烟雾+人体传感器
- 电动推杆模拟闸门
- 手动/自动模式切换
- 自动: 烟雾报警灯+温度>阈值开风扇+人体控制灯和门
- TCP串口服务器
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

class HallEnvironment:
    def __init__(self):
        self.cloud = CloudClient()
        self.temp = 0.0; self.hum = 0.0; self.smoke = 0; self.body = "无人"
        self.mode = "auto"  # auto/manual
        self.fan_on = False; self.door_open = False; self.alarm_on = False; self.lamp_on = False
        self.running = False; self.root = None

    def read_sensors(self):
        val = self.cloud.get_sensor_data(1, "m_temp")
        self.temp = float(val) if val else random.uniform(20, 35)
        val = self.cloud.get_sensor_data(1, "m_hum")
        self.hum = float(val) if val else random.uniform(40, 80)
        val = self.cloud.get_sensor_data(1, "m_smoke")
        self.smoke = int(float(val)) if val else random.randint(0, 100)
        val = self.cloud.get_sensor_data(1, "z_body")
        self.body = "有人" if val not in ("0", "false", "", None) else "无人"

    def auto_control(self):
        if self.mode != "auto": return
        # 烟雾报警
        self.alarm_on = self.smoke > 50
        self.cloud.send_command(1, "m_strobe_red", {"value": "1" if self.alarm_on else "0"})
        # 温度>27开风扇
        self.fan_on = self.temp >= 27
        self.cloud.send_command(1, "m_fan", {"value": "1" if self.fan_on else "0"})
        # 人体控制灯和门
        if self.body == "有人":
            self.lamp_on = True; self.door_open = True
        else:
            self.lamp_on = False; self.door_open = False
        self.cloud.send_command(1, "m_lamp", {"value": "1" if self.lamp_on else "0"})
        self.cloud.send_command(1, "m_pushrod_back", {"value": "1" if self.door_open else "0"})
        self.cloud.send_command(1, "m_pushrod_putt", {"value": "0" if self.door_open else "1"})

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("大厅环境系统"); self.root.geometry("650x550")
        tk.Label(self.root, text="大厅环境系统", font=("微软雅黑", 16, "bold")).pack(pady=10)
        # 模式切换
        mf = tk.Frame(self.root); mf.pack(pady=5)
        self.mode_var = tk.StringVar(value="auto")
        tk.Radiobutton(mf, text="自动模式", variable=self.mode_var, value="auto",
                       command=self.switch_mode, font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=10)
        tk.Radiobutton(mf, text="手动模式", variable=self.mode_var, value="manual",
                       command=self.switch_mode, font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=10)
        # 数据
        cf = tk.Frame(self.root, bd=1, relief=tk.RAISED, padx=10, pady=5)
        cf.pack(pady=5, fill=tk.X, padx=20)
        self.labels = {}
        for name, unit in [("温度","℃"),("湿度","%"),("烟雾",""),("人体","")]:
            f = tk.Frame(cf); f.pack(side=tk.LEFT, padx=10)
            tk.Label(f, text=name, font=("微软雅黑", 10)).pack()
            lbl = tk.Label(f, text="--", font=("微软雅黑", 13, "bold"), fg="blue"); lbl.pack()
            self.labels[name] = lbl
        # 设备状态
        dev = tk.Frame(self.root, bd=1, relief=tk.GROOVE, padx=10, pady=5)
        dev.pack(pady=5, fill=tk.X, padx=20)
        self.fan_canvas = tk.Canvas(dev, width=40, height=40, bg="white"); self.fan_canvas.pack(side=tk.LEFT, padx=8)
        tk.Label(dev, text="风扇", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.door_canvas = tk.Canvas(dev, width=50, height=40, bg="gray"); self.door_canvas.pack(side=tk.LEFT, padx=8)
        tk.Label(dev, text="闸门", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.alarm_canvas = tk.Canvas(dev, width=40, height=40, bg="gray"); self.alarm_canvas.pack(side=tk.LEFT, padx=8)
        tk.Label(dev, text="报警灯", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.lamp_canvas = tk.Canvas(dev, width=40, height=40, bg="gray"); self.lamp_canvas.pack(side=tk.LEFT, padx=8)
        tk.Label(dev, text="灯", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        # 手动按钮
        self.manual_frame = tk.Frame(self.root)
        self.manual_frame.pack(pady=5)
        tk.Button(self.manual_frame, text="风扇开", command=lambda: self.set_device("fan", True)).pack(side=tk.LEFT, padx=3)
        tk.Button(self.manual_frame, text="风扇关", command=lambda: self.set_device("fan", False)).pack(side=tk.LEFT, padx=3)
        tk.Button(self.manual_frame, text="开门", command=lambda: self.set_device("door", True)).pack(side=tk.LEFT, padx=3)
        tk.Button(self.manual_frame, text="关门", command=lambda: self.set_device("door", False)).pack(side=tk.LEFT, padx=3)
        tk.Button(self.manual_frame, text="灯开", command=lambda: self.set_device("lamp", True)).pack(side=tk.LEFT, padx=3)
        tk.Button(self.manual_frame, text="灯关", command=lambda: self.set_device("lamp", False)).pack(side=tk.LEFT, padx=3)
        bf = tk.Frame(self.root); bf.pack(pady=10)
        tk.Button(bf, text="启动", command=self.start, font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="停止", command=self.stop, font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

    def switch_mode(self):
        self.mode = self.mode_var.get()

    def set_device(self, dev, on):
        if self.mode == "manual":
            if dev == "fan": self.fan_on = on
            elif dev == "door": self.door_open = on
            elif dev == "lamp": self.lamp_on = on
            self.cloud.send_command(1, "m_fan", {"value": "1" if self.fan_on else "0"})
            self.cloud.send_command(1, "m_lamp", {"value": "1" if self.lamp_on else "0"})
            self.cloud.send_command(1, "m_pushrod_back", {"value": "1" if self.door_open else "0"})
            if self.root: self.update_display()

    def update_display(self):
        self.labels["温度"].config(text="%.1f" % self.temp)
        self.labels["湿度"].config(text="%.1f" % self.hum)
        self.labels["烟雾"].config(text=str(self.smoke), fg="red" if self.smoke > 50 else "green")
        self.labels["人体"].config(text=self.body, fg="red" if self.body=="有人" else "gray")
        self.fan_canvas.config(bg="cyan" if self.fan_on else "white")
        self.door_canvas.config(bg="#90EE90" if self.door_open else "gray")
        self.alarm_canvas.config(bg="red" if self.alarm_on else "gray")
        self.lamp_canvas.config(bg="yellow" if self.lamp_on else "gray")

    def monitor_loop(self):
        while self.running:
            self.read_sensors()
            self.auto_control()
            if self.root: self.root.after(0, self.update_display)
            time.sleep(1)

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
                try: self.read_sensors(); self.auto_control(); time.sleep(1)
                except KeyboardInterrupt: break

if __name__ == "__main__":
    HallEnvironment().run()
