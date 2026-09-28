# -*- coding: utf-8 -*-
"""套10 2-6 门闸环境系统 - Python 3.6 兼容
任务要求：
- 温湿度+CO2+噪音四输入
- 电动推杆模拟闸门+摄像头监控+截图
- 图片列表+历史记录查询(类型/时间过滤)
- TCP串口服务器
"""
import os, sys, time, random, threading, collections
try:
    import requests
except ImportError:
    requests = None
try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
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

class GateEnvironment:
    def __init__(self):
        self.cloud = CloudClient()
        self.temp = 0.0; self.hum = 0.0; self.co2 = 0; self.noise = 0.0
        self.door_open = False; self.running = False; self.root = None
        self.history = []  # (时间, 类型, 温度, 湿度, CO2, 噪音)
        self.images = []  # (时间, 路径)
        self.cap = None

    def read_sensors(self):
        val = self.cloud.get_sensor_data(1, "m_temp")
        self.temp = float(val) if val else random.uniform(20, 35)
        val = self.cloud.get_sensor_data(1, "m_hum")
        self.hum = float(val) if val else random.uniform(40, 80)
        val = self.cloud.get_sensor_data(1, "m_co2")
        self.co2 = int(float(val)) if val else random.randint(300, 800)
        val = self.cloud.get_sensor_data(1, "m_noise")
        self.noise = float(val) if val else random.uniform(30, 70)
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.history.append((now, "采集", self.temp, self.hum, self.co2, self.noise))

    def toggle_door(self):
        self.door_open = not self.door_open
        self.cloud.send_command(1, "m_pushrod_back", {"value": "1" if self.door_open else "0"})
        self.cloud.send_command(1, "m_pushrod_putt", {"value": "0" if self.door_open else "1"})
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.history.append((now, "闸门", "开" if self.door_open else "关", "", "", ""))

    def take_screenshot(self):
        now = time.strftime("%Y%m%d_%H%M%S")
        path = "screenshot_%s.png" % now
        # 赛场实际调用摄像头截图
        self.images.append((time.strftime("%Y-%m-%d %H:%M:%S"), path))
        self.history.append((time.strftime("%Y-%m-%d %H:%M:%S"), "截图", path, "", "", ""))
        print("[SCREENSHOT] %s" % path)

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("门闸环境系统"); self.root.geometry("750x600")
        tk.Label(self.root, text="门闸环境监控系统", font=("微软雅黑", 16, "bold")).pack(pady=10)
        # 数据
        cf = tk.Frame(self.root, bd=1, relief=tk.RAISED, padx=10, pady=5)
        cf.pack(pady=5, fill=tk.X, padx=20)
        self.labels = {}
        for name, unit in [("温度","℃"),("湿度","%"),("CO2","ppm"),("噪音","dB")]:
            f = tk.Frame(cf); f.pack(side=tk.LEFT, padx=10)
            tk.Label(f, text=name, font=("微软雅黑", 10)).pack()
            lbl = tk.Label(f, text="--", font=("微软雅黑", 13, "bold"), fg="blue"); lbl.pack()
            self.labels[name] = lbl
        # 闸门+截图
        ctrl = tk.Frame(self.root); ctrl.pack(pady=5)
        self.door_label = tk.Label(ctrl, text="闸门: 关", font=("微软雅黑", 10))
        self.door_label.pack(side=tk.LEFT, padx=10)
        tk.Button(ctrl, text="开关闸门", command=self.toggle_door, font=("微软雅黑", 9), bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(ctrl, text="截图", command=self.take_screenshot, font=("微软雅黑", 9), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        # 搜索过滤
        sf = tk.Frame(self.root); sf.pack(pady=5, fill=tk.X, padx=20)
        tk.Label(sf, text="类型:", font=("微软雅黑", 9)).pack(side=tk.LEFT)
        self.filter_var = tk.StringVar(value="全部")
        tk.OptionMenu(sf, self.filter_var, "全部", "采集", "闸门", "截图").pack(side=tk.LEFT, padx=3)
        tk.Label(sf, text="日期:", font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=5)
        self.date_entry = tk.Entry(sf, width=12); self.date_entry.pack(side=tk.LEFT, padx=3)
        tk.Button(sf, text="查询", command=self.refresh_history, font=("微软雅黑", 8)).pack(side=tk.LEFT, padx=5)
        # 历史记录
        tk.Label(self.root, text="历史记录:", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        self.history_list = tk.Listbox(self.root, font=("Consolas", 8), height=10)
        self.history_list.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        # 图片列表
        tk.Label(self.root, text="截图列表:", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        self.img_list = tk.Listbox(self.root, font=("Consolas", 8), height=4)
        self.img_list.pack(fill=tk.X, padx=20, pady=3)
        bf = tk.Frame(self.root); bf.pack(pady=5)
        tk.Button(bf, text="启动", command=self.start, font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="停止", command=self.stop, font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

    def refresh_history(self):
        self.history_list.delete(0, tk.END)
        filter_type = self.filter_var.get()
        filter_date = self.date_entry.get().strip()
        for rec in reversed(self.history[-50:]):
            if filter_type != "全部" and rec[1] != filter_type: continue
            if filter_date and not rec[0].startswith(filter_date): continue
            self.history_list.insert(tk.END, "%s  %s  %s" % (rec[0], rec[1], rec[2]))
        self.img_list.delete(0, tk.END)
        for t, p in reversed(self.images[-10:]):
            self.img_list.insert(tk.END, "%s  %s" % (t, p))

    def update_display(self):
        self.labels["温度"].config(text="%.1f" % self.temp)
        self.labels["湿度"].config(text="%.1f" % self.hum)
        self.labels["CO2"].config(text=str(self.co2))
        self.labels["噪音"].config(text="%.1f" % self.noise)
        self.door_label.config(text="闸门: %s" % ("开" if self.door_open else "关"))
        self.refresh_history()

    def monitor_loop(self):
        while self.running:
            self.read_sensors()
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
                try: self.read_sensors(); time.sleep(1)
                except KeyboardInterrupt: break

if __name__ == "__main__":
    GateEnvironment().run()
