# -*- coding: utf-8 -*-
"""套5 2-7 智能商超系统 - Python 3.6 兼容
任务要求：
- UHF RFID读取3个客人标签(A消费24元/B消费30元/C消费27元)
- 读取消费额+TTS语音播报
"""
import os, sys, time, random, threading, subprocess
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

class Supermarket:
    """智能商超系统"""
    CUSTOMERS = {
        "RFID_A001": {"name": "客人A", "amount": 24},
        "RFID_A002": {"name": "客人B", "amount": 30},
        "RFID_A003": {"name": "客人C", "amount": 27},
    }
    def __init__(self):
        self.cloud = CloudClient()
        self.total_sales = 0
        self.records = []
        self.running = False
        self.root = None

    def speak(self, text):
        try:
            cmd = 'powershell -Command "Add-Type -AssemblyName System.Speech; $s=New-Object System.Speech.Synthesis.SpeechSynthesizer; $s.Speak(\'%s\')"' % text
            subprocess.Popen(cmd, shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except: print("[TTS] %s" % text)

    def on_card_read(self, rfid):
        info = self.CUSTOMERS.get(rfid)
        if info:
            self.total_sales += info["amount"]
            now = time.strftime("%H:%M:%S")
            self.records.append((now, rfid, info["name"], info["amount"]))
            msg = "%s消费%d元，今日总销售额%d元" % (info["name"], info["amount"], self.total_sales)
            self.speak(msg)
            print("[SALE] %s" % msg)
            if self.root: self.root.after(0, self.refresh_display)
        else:
            self.speak("未识别的标签")

    def refresh_display(self):
        if not hasattr(self, 'sales_label'): return
        self.sales_label.config(text="今日总销售额: %d元" % self.total_sales)
        self.record_list.delete(0, tk.END)
        for r in reversed(self.records[-15:]):
            self.record_list.insert(tk.END, "%s  %s  %s  %d元" % r)

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("智能商超系统")
        self.root.geometry("550x450")
        tk.Label(self.root, text="智能商超系统", font=("微软雅黑", 16, "bold")).pack(pady=10)
        self.sales_label = tk.Label(self.root, text="今日总销售额: 0元", font=("微软雅黑", 14, "bold"), fg="red")
        self.sales_label.pack(pady=5)
        tk.Label(self.root, text="模拟读卡:", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        card_f = tk.Frame(self.root)
        card_f.pack(pady=5)
        for rfid, info in self.CUSTOMERS.items():
            tk.Button(card_f, text="%s(%d元)" % (info["name"], info["amount"]),
                      command=lambda r=rfid: self.on_card_read(r),
                      font=("微软雅黑", 9), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Label(self.root, text="消费记录:", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        self.record_list = tk.Listbox(self.root, font=("Consolas", 9), height=10)
        self.record_list.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        tk.Button(self.root, text="启动监听", command=self.start, font=("微软雅黑", 10), bg="#2196F3", fg="white").pack(pady=5)

    def monitor_loop(self):
        while self.running:
            val = self.cloud.get_sensor_data(1, "m_rfid")
            if val:
                self.on_card_read(val)
            time.sleep(1)

    def start(self):
        if not self.running:
            self.running = True
            self.cloud.login()
            threading.Thread(target=self.monitor_loop, daemon=True).start()

    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            self.cloud.login()
            self.running = True
            while self.running:
                try:
                    rfid = input("RFID: ").strip()
                    if rfid: self.on_card_read(rfid)
                except (KeyboardInterrupt, EOFError): break

if __name__ == "__main__":
    Supermarket().run()
