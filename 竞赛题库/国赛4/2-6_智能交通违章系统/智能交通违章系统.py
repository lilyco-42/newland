# -*- coding: utf-8 -*-
"""套4 2-6 智能交通违章系统 - Python 3.6 兼容
任务要求：
- 模拟智能交通车辆闯红灯监控
- 通过摄像头拍照登记车辆违章信息
- 检测红绿灯状态（通过行程开关传感器）
- 红灯时检测到车辆通过 -> 拍照记录违章
- 违章记录列表（时间、车牌、违章类型、照片路径）
- 导出Excel违章记录
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


class TrafficViolationSystem:
    """智能交通违章系统"""
    PLATES = ["粤A12345", "粤B67890", "粤C11111", "粤D22222", "粤E33333"]
    VIOLATION_TYPES = ["闯红灯", "超速", "违规变道", "逆行"]

    def __init__(self):
        self.cloud = CloudClient()
        self.violations = collections.deque(maxlen=200)
        self.excel_data = []
        self.running = False
        self.red_light = False  # True=红灯
        self.root = None

    def get_light_state(self):
        """获取红绿灯状态（通过行程开关传感器）"""
        val = self.cloud.get_sensor_data(1, "m_travelSwitch")
        if val is not None:
            # 行程开关默认闭合=绿灯，断开=红灯
            return val == "0" or val == "false"
        return self.red_light

    def detect_vehicle(self):
        """模拟车辆检测（赛场用摄像头+地感线圈）"""
        if random.random() < 0.3:  # 30%概率有车经过
            return random.choice(self.PLATES)
        return None

    def take_photo(self, plate):
        """拍照记录违章"""
        photo_path = "违章照片_%s_%s.jpg" % (plate, time.strftime("%H%M%S"))
        # 赛场实际会调用摄像头拍照
        return photo_path

    def record_violation(self, plate, photo_path):
        """记录违章"""
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        vtype = "闯红灯"
        self.violations.appendleft((now, plate, vtype, photo_path))
        self.excel_data.append((now, plate, vtype, photo_path))

        # 控制多层指示灯红灯闪烁
        self.cloud.send_command(1, "m_multi_red", {"value": "1"})
        time.sleep(0.5)
        self.cloud.send_command(1, "m_multi_red", {"value": "0"})

        return now, vtype

    def export_excel(self):
        if not Workbook:
            print("[ERR] openpyxl not installed")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="导出违章记录")
        if not filepath:
            return
        wb = Workbook()
        ws = wb.active
        ws.title = "违章记录"
        ws.append(["时间", "车牌号", "违章类型", "照片路径"])
        records = sorted(self.excel_data[-50:], key=lambda x: x[0], reverse=True)
        for row in records:
            ws.append(list(row))
        wb.save(filepath)
        print("[OK] 导出 %d 条 -> %s" % (len(records), filepath))

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("智能交通违章系统")
        self.root.geometry("700x550")

        tk.Label(self.root, text="智能交通违章监控系统",
                 font=("微软雅黑", 16, "bold")).pack(pady=10)

        # 交通灯状态
        light_frame = tk.Frame(self.root)
        light_frame.pack(pady=5)
        self.red_canvas = tk.Canvas(light_frame, width=40, height=40, bg="gray")
        self.red_canvas.pack(side=tk.LEFT, padx=5)
        tk.Label(light_frame, text="红灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        self.green_canvas = tk.Canvas(light_frame, width=40, height=40, bg="gray")
        self.green_canvas.pack(side=tk.LEFT, padx=5)
        tk.Label(light_frame, text="绿灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)

        self.light_status = tk.Label(self.root, text="当前: 绿灯", font=("微软雅黑", 11, "bold"))
        self.light_status.pack(pady=3)

        # 违章信息区
        info_frame = tk.Frame(self.root, bd=1, relief=tk.GROOVE, padx=10, pady=5)
        info_frame.pack(pady=5, fill=tk.X, padx=20)
        tk.Label(info_frame, text="最近违章:", font=("微软雅黑", 10)).pack(anchor=tk.W)
        self.violation_info = tk.Label(info_frame, text="无", font=("微软雅黑", 10), fg="red")
        self.violation_info.pack(anchor=tk.W)

        # 违章记录列表
        tk.Label(self.root, text="违章记录:", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        list_frame = tk.Frame(self.root)
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        scrollbar = tk.Scrollbar(list_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.record_list = tk.Listbox(list_frame, font=("Consolas", 9), yscrollcommand=scrollbar.set)
        self.record_list.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.record_list.yview)

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=10)
        tk.Button(btn_frame, text="启动监控", command=self.start,
                  font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="停止", command=self.stop,
                  font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="手动模拟车辆", command=self.simulate_pass,
                  font=("微软雅黑", 10), bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="导出Excel", command=self.export_excel,
                  font=("微软雅黑", 10), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)

    def simulate_pass(self):
        """手动模拟车辆经过"""
        plate = random.choice(self.PLATES)
        self.process_vehicle(plate)

    def process_vehicle(self, plate):
        is_red = self.get_light_state()
        self.update_light_display()

        if is_red:
            photo = self.take_photo(plate)
            now, vtype = self.record_violation(plate, photo)
            info = "[%s] %s %s - %s" % (now, plate, vtype, photo)
            self.violation_info.config(text=info)
            self.record_list.insert(0, info)
            print("[VIOLATION] %s" % info)
        else:
            print("[OK] %s 绿灯通行" % plate)

    def update_light_display(self):
        is_red = self.get_light_state()
        if is_red:
            self.red_canvas.config(bg="red")
            self.green_canvas.config(bg="gray")
            self.light_status.config(text="当前: 红灯", fg="red")
        else:
            self.red_canvas.config(bg="gray")
            self.green_canvas.config(bg="green")
            self.light_status.config(text="当前: 绿灯", fg="green")

    def monitor_loop(self):
        while self.running:
            plate = self.detect_vehicle()
            if plate:
                if self.root:
                    self.root.after(0, self.process_vehicle, plate)
                else:
                    self.process_vehicle(plate)
            time.sleep(1)

    def start(self):
        if not self.running:
            self.running = True
            self.cloud.login()
            t = threading.Thread(target=self.monitor_loop, daemon=True)
            t.start()

    def stop(self):
        self.running = False
        # 熄灭所有灯
        self.cloud.send_command(1, "m_multi_red", {"value": "0"})
        self.cloud.send_command(1, "m_multi_green", {"value": "0"})

    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            print("智能交通违章系统（命令行模式）")
            self.cloud.login()
            self.running = True
            while self.running:
                try:
                    plate = self.detect_vehicle()
                    if plate:
                        self.process_vehicle(plate)
                    time.sleep(1)
                except KeyboardInterrupt:
                    break
            self.stop()


if __name__ == "__main__":
    app = TrafficViolationSystem()
    app.run()
