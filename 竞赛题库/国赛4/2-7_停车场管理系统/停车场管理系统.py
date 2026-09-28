# -*- coding: utf-8 -*-
"""套4 2-7 停车场管理系统 - Python 3.6 兼容
任务要求：
- UHF RFID读取车辆标签 -> 开启道闸（电动推杆伸出）
- 自动计算停车时间与收费
- 语音播报（TTS）
- 车位状态显示（空闲/占用）
- 车辆进出记录列表
- 导出Excel（时间、车牌、停车时长、收费）
"""
import os
import sys
import time
import random
import threading
import collections
import subprocess

try:
    import requests
except ImportError:
    requests = None

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

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
            data = r.json()
            if data["Status"] == 0:
                self.token = data["ResultObj"]["AccessToken"]
                return True
        except: pass
        return False
    def send_command(self, device_id, api_tag, value):
        if not self.token or not requests: return
        try:
            requests.post("%s/Cmds" % CLOUD_BASE,
                headers={"AccessToken": self.token},
                params={"deviceId": device_id, "apiTag": api_tag},
                json=value, timeout=5)
        except: pass
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


class ParkingSystem:
    """停车场管理系统"""
    PRICE_PER_HOUR = 5  # 每小时5元
    TOTAL_SPACES = 100

    def __init__(self):
        self.cloud = CloudClient()
        self.records = []  # (plate, entry_time, exit_time, duration, fee)
        self.parked = {}  # plate -> entry_time
        self.available = self.TOTAL_SPACES
        self.running = False
        self.root = None
        self.excel_data = []

    def speak(self, text):
        """语音播报"""
        try:
            # Windows TTS
            cmd = 'powershell -Command "Add-Type -AssemblyName System.Speech; '\
                  '$s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '\
                  '$s.Speak(\'%s\')"' % text
            subprocess.Popen(cmd, shell=True,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except:
            print("[TTS] %s" % text)

    def open_gate(self):
        """开闸（电动推杆缩回）"""
        self.cloud.send_command(1, "m_pushrod_back", {"value": "1"})
        self.cloud.send_command(1, "m_pushrod_putt", {"value": "0"})
        # 多层灯绿灯亮
        self.cloud.send_command(1, "m_multi_green", {"value": "1"})

    def close_gate(self):
        """关闸（电动推杆伸出）"""
        self.cloud.send_command(1, "m_pushrod_putt", {"value": "1"})
        self.cloud.send_command(1, "m_pushrod_back", {"value": "0"})
        self.cloud.send_command(1, "m_multi_green", {"value": "0"})

    def vehicle_enter(self, plate):
        """车辆进入"""
        if plate in self.parked:
            return
        now = time.time()
        self.parked[plate] = now
        self.available -= 1
        self.open_gate()
        self.speak("车辆 %s 已进入停车场" % plate)
        print("[ENTER] %s %s" % (plate, time.strftime("%H:%M:%S")))
        time.sleep(2)
        self.close_gate()

    def vehicle_exit(self, plate):
        """车辆离开"""
        if plate not in self.parked:
            self.speak("未找到车辆 %s" % plate)
            return
        entry = self.parked.pop(plate)
        now = time.time()
        duration_min = (now - entry) / 60
        duration_hr = max(duration_min / 60, 0.5)  # 最小0.5小时
        fee = int(duration_hr * self.PRICE_PER_HOUR)
        self.available += 1

        record = (plate, time.strftime("%H:%M:%S", time.localtime(entry)),
                  time.strftime("%H:%M:%S"), "%.1f分钟" % duration_min, "%d元" % fee)
        self.records.append(record)
        self.excel_data.append(record)

        self.open_gate()
        self.speak("车辆 %s 停车 %.1f 分钟，收费 %d 元" % (plate, duration_min, fee))
        print("[EXIT] %s 停车%.1f分钟 收费%d元" % (plate, duration_min, fee))
        time.sleep(2)
        self.close_gate()

    def export_excel(self):
        if not Workbook: return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="导出停车记录")
        if not filepath: return
        wb = Workbook()
        ws = wb.active
        ws.title = "停车记录"
        ws.append(["车牌", "进入时间", "离开时间", "停车时长", "收费"])
        for row in self.excel_data[-50:]:
            ws.append(list(row))
        wb.save(filepath)
        print("[OK] 导出 -> %s" % filepath)

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("停车场管理系统")
        self.root.geometry("650x500")

        tk.Label(self.root, text="停车场管理系统",
                 font=("微软雅黑", 16, "bold")).pack(pady=10)

        # 车位信息
        info_frame = tk.Frame(self.root, bd=1, relief=tk.GROOVE, padx=10, pady=5)
        info_frame.pack(pady=5, fill=tk.X, padx=20)
        tk.Label(info_frame, text="总车位: %d" % self.TOTAL_SPACES,
                 font=("微软雅黑", 11)).pack(side=tk.LEFT, padx=10)
        self.space_label = tk.Label(info_frame, text="空闲: %d" % self.available,
                                     font=("微软雅黑", 11, "bold"), fg="green")
        self.space_label.pack(side=tk.LEFT, padx=10)
        self.occupied_label = tk.Label(info_frame, text="占用: 0",
                                        font=("微软雅黑", 11), fg="red")
        self.occupied_label.pack(side=tk.LEFT, padx=10)

        # 道闸状态
        self.gate_label = tk.Label(self.root, text="道闸: 关闭",
                                    font=("微软雅黑", 10))
        self.gate_label.pack(pady=3)

        # 模拟读卡
        card_frame = tk.Frame(self.root)
        card_frame.pack(pady=5)
        tk.Label(card_frame, text="模拟RFID:", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        tk.Button(card_frame, text="粤A12345进入",
                  command=lambda: self.vehicle_enter("粤A12345"),
                  font=("微软雅黑", 9), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=3)
        tk.Button(card_frame, text="粤A12345离开",
                  command=lambda: self.vehicle_exit("粤A12345"),
                  font=("微软雅黑", 9), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=3)
        tk.Button(card_frame, text="粤B67890进入",
                  command=lambda: self.vehicle_enter("粤B67890"),
                  font=("微软雅黑", 9), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=3)
        tk.Button(card_frame, text="粤B67890离开",
                  command=lambda: self.vehicle_exit("粤B67890"),
                  font=("微软雅黑", 9), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=3)

        # 记录列表
        tk.Label(self.root, text="停车记录:", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        self.record_list = tk.Listbox(self.root, font=("Consolas", 9), height=10)
        self.record_list.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="启动监听", command=self.start,
                  font=("微软雅黑", 10), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="导出Excel", command=self.export_excel,
                  font=("微软雅黑", 10), bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)

    def update_gui(self):
        self.space_label.config(text="空闲: %d" % self.available)
        self.occupied_label.config(text="占用: %d" % (self.TOTAL_SPACES - self.available))
        self.record_list.delete(0, tk.END)
        for r in reversed(self.records[-20:]):
            self.record_list.insert(tk.END, "%s | %s进 %s出 | %s | %s" % r)

    def monitor_loop(self):
        while self.running:
            val = self.cloud.get_sensor_data(1, "m_rfid")
            if val:
                if val in self.parked:
                    self.vehicle_exit(val)
                else:
                    self.vehicle_enter(val)
                if self.root:
                    self.root.after(0, self.update_gui)
            time.sleep(1)

    def start(self):
        if not self.running:
            self.running = True
            self.cloud.login()
            t = threading.Thread(target=self.monitor_loop, daemon=True)
            t.start()

    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            print("停车场管理系统（命令行模式）")
            while True:
                try:
                    cmd = input("输入车牌(enter=进入, exit=离开): ").strip()
                    if cmd.startswith("exit "):
                        self.vehicle_exit(cmd[5:])
                    elif cmd:
                        self.vehicle_enter(cmd)
                except (KeyboardInterrupt, EOFError):
                    break


if __name__ == "__main__":
    app = ParkingSystem()
    app.run()
