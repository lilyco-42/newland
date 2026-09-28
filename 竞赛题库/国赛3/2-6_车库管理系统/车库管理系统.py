# -*- coding: utf-8 -*-
"""套3 2-6 车库管理系统 - Python 3.6 兼容
任务要求：
- 红外对射传感器检测车辆进出
- LED显示屏显示车位信息
- 车位总数10个，进出计数
- 满位时显示提示
- 小车入库动画效果
- TCP串口服务器模式
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


class GarageSystem:
    """车库管理系统"""
    TOTAL_SPACES = 10

    def __init__(self):
        self.cloud = CloudClient()
        self.parked_count = 0
        self.total_in = 0
        self.total_out = 0
        self.running = False
        self.root = None
        self.spaces = [False] * self.TOTAL_SPACES  # False=空闲

    def vehicle_enter(self):
        """车辆入库"""
        if self.parked_count >= self.TOTAL_SPACES:
            print("[FULL] 车位已满！")
            if self.root and hasattr(self, 'full_label'):
                self.root.after(0, lambda: self.full_label.config(text="车位已满！", fg="red"))
            return False
        # 找空位
        for i in range(self.TOTAL_SPACES):
            if not self.spaces[i]:
                self.spaces[i] = True
                break
        self.parked_count += 1
        self.total_in += 1
        print("[IN] 车辆入库，当前%d/%d" % (self.parked_count, self.TOTAL_SPACES))
        if self.root:
            self.root.after(0, self.update_display)
        return True

    def vehicle_exit(self):
        """车辆出库"""
        if self.parked_count <= 0:
            return False
        # 找已停车位
        for i in range(self.TOTAL_SPACES):
            if self.spaces[i]:
                self.spaces[i] = False
                break
        self.parked_count -= 1
        self.total_out += 1
        print("[OUT] 车辆出库，当前%d/%d" % (self.parked_count, self.TOTAL_SPACES))
        if self.root:
            self.root.after(0, self.update_display)
        return True

    def update_display(self):
        if not self.root: return
        self.count_label.config(text="%d / %d" % (self.parked_count, self.TOTAL_SPACES))
        self.in_label.config(text=str(self.total_in))
        self.out_label.config(text=str(self.total_out))
        if self.parked_count >= self.TOTAL_SPACES:
            self.full_label.config(text="已满", fg="red")
        else:
            self.full_label.config(text="空闲%d位" % (self.TOTAL_SPACES - self.parked_count), fg="green")
        # 更新车位指示灯
        for i, lbl in enumerate(self.space_labels):
            if self.spaces[i]:
                lbl.config(bg="red", text="占")
            else:
                lbl.config(bg="green", text="空")

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("车库管理系统")
        self.root.geometry("650x500")

        tk.Label(self.root, text="车库管理系统",
                 font=("微软雅黑", 16, "bold")).pack(pady=10)

        # LED显示模拟
        led_frame = tk.Frame(self.root, bg="black", bd=2, relief=tk.SUNKEN)
        led_frame.pack(pady=5, padx=20, fill=tk.X)
        led_inner = tk.Frame(led_frame, bg="black")
        led_inner.pack(pady=10)
        tk.Label(led_inner, text="车位:", bg="black", fg="#00ff00",
                 font=("Consolas", 14)).pack(side=tk.LEFT)
        self.count_label = tk.Label(led_inner, text="0 / 10", bg="black", fg="#00ff00",
                                     font=("Consolas", 18, "bold"))
        self.count_label.pack(side=tk.LEFT, padx=10)
        self.full_label = tk.Label(led_inner, text="空闲10位", bg="black", fg="green",
                                    font=("Consolas", 14))
        self.full_label.pack(side=tk.LEFT, padx=10)

        # 统计
        stat_frame = tk.Frame(self.root)
        stat_frame.pack(pady=5)
        tk.Label(stat_frame, text="入库:", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)
        self.in_label = tk.Label(stat_frame, text="0", font=("微软雅黑", 12, "bold"))
        self.in_label.pack(side=tk.LEFT)
        tk.Label(stat_frame, text="出库:", font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=15)
        self.out_label = tk.Label(stat_frame, text="0", font=("微软雅黑", 12, "bold"))
        self.out_label.pack(side=tk.LEFT)

        # 车位指示
        tk.Label(self.root, text="车位状态:", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        space_frame = tk.Frame(self.root)
        space_frame.pack(pady=5, padx=20)
        self.space_labels = []
        for i in range(self.TOTAL_SPACES):
            lbl = tk.Label(space_frame, text="空", bg="green", fg="white",
                          font=("微软雅黑", 9), width=4, height=2, relief=tk.RAISED)
            lbl.grid(row=i//5, column=i%5, padx=3, pady=3)
            self.space_labels.append(lbl)

        # 模拟按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="车辆入库", command=self.vehicle_enter,
                  font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="车辆出库", command=self.vehicle_exit,
                  font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

    def monitor_loop(self):
        while self.running:
            # 检测红外对射传感器
            val1 = self.cloud.get_sensor_data(1, "m_infrared1")
            val2 = self.cloud.get_sensor_data(1, "m_infrared2")
            if val1 == "1":
                self.vehicle_enter()
            elif val2 == "1":
                self.vehicle_exit()
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
            print("车库管理系统（命令行模式）")
            self.running = True
            while self.running:
                try:
                    cmd = input("in=入库 out=出库: ").strip()
                    if cmd == "in": self.vehicle_enter()
                    elif cmd == "out": self.vehicle_exit()
                except (KeyboardInterrupt, EOFError):
                    break


if __name__ == "__main__":
    app = GarageSystem()
    app.run()
