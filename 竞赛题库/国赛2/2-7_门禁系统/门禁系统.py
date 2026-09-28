# -*- coding: utf-8 -*-
"""套2 2-7 门禁系统 - Python 3.6 兼容
任务要求：
- UHF射频读写器实时读取RFID卡信息
- 控制多层警示灯红灯亮灭（通过云服务系统）
- 读卡时：显示RFID号+刷卡时间+人员图像（显示2秒后消失）
- 刷卡记录列表（按时间倒序）
- 导出Excel（最近记录，含时间和卡号，按时间倒序）
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
    from PIL import Image, ImageTk
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


class AccessControl:
    """门禁系统"""
    def __init__(self):
        self.cloud = CloudClient()
        self.records = collections.deque(maxlen=100)
        self.excel_data = []
        self.running = False
        self.red_light_on = False
        self.root = None
        self.person_images = {}  # rfid -> image path

    def simulate_rfid(self):
        """模拟RFID读卡（赛场用真实UHF读写器）"""
        cards = ["E200001234560001", "E200001234560002", "E200001234560003"]
        names = {"E200001234560001": "张三", "E200001234560002": "李四", "E200001234560003": "王五"}
        card = random.choice(cards)
        return card, names.get(card, "未知")

    def toggle_red_light(self, on):
        """控制多层警示灯红灯"""
        self.red_light_on = on
        self.cloud.send_command(1, "m_multi_red", {"value": "1" if on else "0"})

    def export_excel(self):
        if not Workbook:
            print("[ERR] openpyxl not installed")
            return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            title="导出刷卡记录")
        if not filepath:
            return
        wb = Workbook()
        ws = wb.active
        ws.title = "刷卡记录"
        ws.append(["时间", "卡号"])
        records = sorted(self.excel_data[-50:], key=lambda x: x[0], reverse=True)
        for t, c in records:
            ws.append([t, c])
        wb.save(filepath)
        print("[OK] 导出 %d 条 -> %s" % (len(records), filepath))

    def on_card_read(self, rfid, name):
        """处理读卡事件"""
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.records.appendleft((now, rfid, name))
        self.excel_data.append((now, rfid))

        # 红灯闪烁
        self.toggle_red_light(True)

        # 更新界面
        if self.root and hasattr(self, 'rfid_label'):
            self.rfid_label.config(text=rfid)
            self.time_label.config(text=now)
            self.name_label.config(text=name)
            # 刷新列表
            self.refresh_records()
            # 2秒后隐藏图像
            self.root.after(2000, lambda: self.hide_person)

    def hide_person(self):
        if hasattr(self, 'person_label'):
            self.person_label.config(image="")
        self.toggle_red_light(False)

    def refresh_records(self):
        if not hasattr(self, 'record_list'): return
        self.record_list.delete(0, tk.END)
        for t, r, n in list(self.records)[:20]:
            self.record_list.insert(tk.END, "%s  %s  %s" % (t, r, n))

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("门禁系统")
        self.root.geometry("700x550")

        tk.Label(self.root, text="门禁系统", font=("微软雅黑", 16, "bold")).pack(pady=5)

        # 读卡信息
        info_frame = tk.Frame(self.root)
        info_frame.pack(pady=5, fill=tk.X, padx=20)
        tk.Label(info_frame, text="RFID:", font=("微软雅黑", 11)).grid(row=0, column=0, sticky=tk.E)
        self.rfid_label = tk.Label(info_frame, text="--", font=("Consolas", 12, "bold"), fg="blue")
        self.rfid_label.grid(row=0, column=1, padx=10)
        tk.Label(info_frame, text="时间:", font=("微软雅黑", 11)).grid(row=1, column=0, sticky=tk.E)
        self.time_label = tk.Label(info_frame, text="--", font=("微软雅黑", 11))
        self.time_label.grid(row=1, column=1, padx=10)
        tk.Label(info_frame, text="姓名:", font=("微软雅黑", 11)).grid(row=2, column=0, sticky=tk.E)
        self.name_label = tk.Label(info_frame, text="--", font=("微软雅黑", 11))
        self.name_label.grid(row=2, column=1, padx=10)

        # 人员图像
        self.person_label = tk.Label(self.root, text="[人员图像]", font=("微软雅黑", 10), bg="#eee", width=20, height=5)
        self.person_label.pack(pady=5)

        # 红灯状态
        light_frame = tk.Frame(self.root)
        light_frame.pack(pady=5)
        self.red_canvas = tk.Canvas(light_frame, width=40, height=40, bg="gray")
        self.red_canvas.pack(side=tk.LEFT, padx=5)
        tk.Label(light_frame, text="多层警示灯-红灯", font=("微软雅黑", 10)).pack(side=tk.LEFT)
        tk.Button(light_frame, text="手动开关", command=lambda: self.toggle_red_light(not self.red_light_on),
                  font=("微软雅黑", 9)).pack(side=tk.LEFT, padx=10)

        # 刷卡记录
        tk.Label(self.root, text="刷卡记录:", font=("微软雅黑", 11)).pack(anchor=tk.W, padx=20)
        self.record_list = tk.Listbox(self.root, height=8, font=("Consolas", 9))
        self.record_list.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="模拟读卡", command=self.simulate_card,
                  font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="导出Excel", command=self.export_excel,
                  font=("微软雅黑", 10), bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="启动监听", command=self.start_monitor,
                  font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="停止", command=self.stop_monitor,
                  font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)

    def simulate_card(self):
        rfid, name = self.simulate_rfid()
        self.on_card_read(rfid, name)

    def monitor_loop(self):
        while self.running:
            # 从云平台读取RFID数据
            val = self.cloud.get_sensor_data(1, "m_rfid")
            if val:
                self.on_card_read(val, "持卡人")
            time.sleep(1)

    def start_monitor(self):
        if not self.running:
            self.running = True
            self.cloud.login()
            t = threading.Thread(target=self.monitor_loop, daemon=True)
            t.start()

    def stop_monitor(self):
        self.running = False

    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            print("门禁系统（命令行模式）")
            self.cloud.login()
            self.running = True
            while self.running:
                try:
                    rfid, name = self.simulate_rfid()
                    now = time.strftime("%H:%M:%S")
                    print("[%s] 刷卡: %s (%s)" % (now, rfid, name))
                    self.excel_data.append((now, rfid))
                    time.sleep(3)
                except KeyboardInterrupt:
                    break


if __name__ == "__main__":
    app = AccessControl()
    app.run()
