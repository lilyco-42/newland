# -*- coding: utf-8 -*-
"""森林火灾监控系统 - Python 3.6 兼容版"""
import tkinter as tk
from tkinter import ttk, messagebox
import time
import datetime
import json
import threading
import random

try:
    import urllib.request
except ImportError:
    pass

API_URL = "http://api.nlecloud.com"
API_TOKEN = "your_token_here"

# 区域配置
ZONES = ["A区-松林", "B区-竹林", "C区-灌木", "D区-草地", "E区-混合林",
         "F区-阔叶林", "G区-针叶林", "H区-湿地", "I区-山坡", "J区-山谷"]

# 阈值配置
TEMP_WARNING = 35.0
TEMP_DANGER = 42.0
SMOKE_WARNING = 50.0
SMOKE_DANGER = 80.0


class FireZone:
    def __init__(self, name, zone_id):
        self.name = name
        self.zone_id = zone_id
        self.temperature = 25.0 + random.random() * 10
        self.smoke = 10 + random.random() * 30
        self.status = "safe"

    def update_data(self, temp, smoke):
        self.temperature = temp
        self.smoke = smoke
        if smoke > SMOKE_DANGER or temp > TEMP_DANGER:
            self.status = "danger"
        elif smoke > SMOKE_WARNING or temp > TEMP_WARNING:
            self.status = "warning"
        else:
            self.status = "safe"


class FireMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("森林火灾监控系统")
        self.root.geometry("1050x680")
        self.root.configure(bg="#0d1117")

        self.zones = []
        for i, name in enumerate(ZONES):
            self.zones.append(FireZone(name, i))

        self.alerts = []
        self.zone_labels = []
        self.zone_canvases = []
        self._build_ui()
        self._update_clock()
        self._start_data_loop()

    def _build_ui(self):
        # 顶部
        header = tk.Frame(self.root, bg="#161b22", height=50)
        header.pack(fill="x")
        tk.Label(header, text="森林火灾监控系统", font=("微软雅黑", 20, "bold"),
                 fg="#ff4444", bg="#161b22").pack(side="left", padx=20)
        self.clock_label = tk.Label(header, text="", font=("微软雅黑", 12), fg="#aaa", bg="#161b22")
        self.clock_label.pack(side="right", padx=20)
        self.status_label = tk.Label(header, text="● 系统运行中", font=("微软雅黑", 11),
                                     fg="#56d364", bg="#161b22")
        self.status_label.pack(side="right", padx=20)

        main = tk.Frame(self.root, bg="#0d1117")
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧 - 区域地图
        left = tk.Frame(main, bg="#0d1117")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left, text="监控区域", font=("微软雅黑", 13, "bold"),
                 fg="#ff4444", bg="#0d1117").pack(anchor="w", pady=(0, 5))

        zone_grid = tk.Frame(left, bg="#0d1117")
        zone_grid.pack(fill="both", expand=True)
        self.zone_labels = []
        for i in range(len(ZONES)):
            row = i // 5
            col = i % 5
            frame = tk.Frame(zone_grid, bg="#161b22", bd=1, relief="solid", padx=5, pady=5)
            frame.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
            name_lbl = tk.Label(frame, text=ZONES[i], font=("微软雅黑", 9), fg="#8b949e", bg="#161b22")
            name_lbl.pack()
            temp_lbl = tk.Label(frame, text="25.0°C", font=("微软雅黑", 16, "bold"),
                                fg="#ff4444", bg="#161b22")
            temp_lbl.pack()
            smoke_lbl = tk.Label(frame, text="烟雾: 10", font=("微软雅黑", 10), fg="#8b949e", bg="#161b22")
            smoke_lbl.pack()
            status_lbl = tk.Label(frame, text="安全", font=("微软雅黑", 9, "bold"),
                                  fg="#56d364", bg="#161b22")
            status_lbl.pack()
            self.zone_labels.append((frame, temp_lbl, smoke_lbl, status_lbl))
            for c in range(5):
                zone_grid.columnconfigure(c, weight=1)

        # 右侧 - 报警与统计
        right = tk.Frame(main, bg="#0d1117", width=320)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # 统计
        tk.Label(right, text="实时统计", font=("微软雅黑", 13, "bold"),
                 fg="#ff4444", bg="#0d1117").pack(anchor="w", pady=(0, 5))
        stats_frame = tk.Frame(right, bg="#161b22", padx=10, pady=10)
        stats_frame.pack(fill="x", pady=(0, 10))
        self.stat_safe = tk.Label(stats_frame, text="安全: 0", font=("微软雅黑", 11), fg="#56d364", bg="#161b22")
        self.stat_safe.pack(side="left", padx=5)
        self.stat_warn = tk.Label(stats_frame, text="预警: 0", font=("微软雅黑", 11), fg="#e3b341", bg="#161b22")
        self.stat_warn.pack(side="left", padx=5)
        self.stat_danger = tk.Label(stats_frame, text="危险: 0", font=("微软雅黑", 11), fg="#ff7b72", bg="#161b22")
        self.stat_danger.pack(side="left", padx=5)

        # 最高温度
        max_frame = tk.Frame(right, bg="#161b22", padx=10, pady=10)
        max_frame.pack(fill="x", pady=(0, 10))
        tk.Label(max_frame, text="最高温度:", font=("微软雅黑", 10), fg="#8b949e", bg="#161b22").pack(side="left")
        self.max_temp_label = tk.Label(max_frame, text="0°C", font=("微软雅黑", 14, "bold"),
                                       fg="#ff4444", bg="#161b22")
        self.max_temp_label.pack(side="right")

        max_smoke_frame = tk.Frame(right, bg="#161b22", padx=10, pady=10)
        max_smoke_frame.pack(fill="x", pady=(0, 10))
        tk.Label(max_smoke_frame, text="最高烟雾:", font=("微软雅黑", 10), fg="#8b949e", bg="#161b22").pack(side="left")
        self.max_smoke_label = tk.Label(max_smoke_frame, text="0", font=("微软雅黑", 14, "bold"),
                                        fg="#e3b341", bg="#161b22")
        self.max_smoke_label.pack(side="right")

        ttk.Separator(right).pack(fill="x", pady=5)

        # 报警列表
        tk.Label(right, text="报警信息", font=("微软雅黑", 13, "bold"),
                 fg="#ff4444", bg="#0d1117").pack(anchor="w", pady=(5, 5))
        self.alert_text = tk.Text(right, height=15, font=("微软雅黑", 9), bg="#161b22", fg="#e6e6e6",
                                  state="disabled", relief="flat", wrap="word")
        self.alert_text.pack(fill="both", expand=True)

        # 控制按钮
        btn_frame = tk.Frame(right, bg="#0d1117")
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="导出数据", font=("微软雅黑", 10), bg="#238636", fg="white",
                  command=self._export_data).pack(side="left", fill="x", expand=True, padx=2)
        tk.Button(btn_frame, text="静音报警", font=("微软雅黑", 10), bg="#da3633", fg="white",
                  command=self._mute_alert).pack(side="left", fill="x", expand=True, padx=2)

    def _update_zones(self):
        safe = warn = danger = 0
        max_t = 0
        max_s = 0
        for i, zone in enumerate(self.zones):
            # 模拟数据波动
            zone.temperature += random.uniform(-0.5, 0.5)
            zone.smoke += random.uniform(-3, 3)
            zone.temperature = max(15.0, min(60.0, zone.temperature))
            zone.smoke = max(0.0, min(100.0, zone.smoke))
            zone.update_data(zone.temperature, zone.smoke)

            if zone.status == "safe":
                safe += 1
                color = "#56d364"
                status_text = "安全"
            elif zone.status == "warning":
                warn += 1
                color = "#e3b341"
                status_text = "预警"
            else:
                danger += 1
                color = "#ff7b72"
                status_text = "危险"

            frame, temp_lbl, smoke_lbl, status_lbl = self.zone_labels[i]
            frame.configure(bg=color + "33" if zone.status != "safe" else "#161b22")
            temp_lbl.configure(text="%.1f°C" % zone.temperature, fg=color)
            smoke_lbl.configure(text="烟雾: %d" % int(zone.smoke))
            status_lbl.configure(text=status_text, fg=color)

            if zone.temperature > max_t:
                max_t = zone.temperature
            if zone.smoke > max_s:
                max_s = zone.smoke

            # 生成报警
            if zone.status == "danger" and random.random() < 0.3:
                ts = datetime.datetime.now().strftime("%H:%M:%S")
                alert_msg = "[%s] %s 温度%.1f°C 烟雾%.0f 超过危险阈值!" % (
                    ts, zone.name, zone.temperature, zone.smoke)
                self.alerts.insert(0, alert_msg)
                if len(self.alerts) > 50:
                    self.alerts = self.alerts[:50]

        self.stat_safe.configure(text="安全: %d" % safe)
        self.stat_warn.configure(text="预警: %d" % warn)
        self.stat_danger.configure(text="危险: %d" % danger)
        self.max_temp_label.configure(text="%.1f°C" % max_t)
        self.max_smoke_label.configure(text="%.0f" % max_s)

        self.alert_text.configure(state="normal")
        self.alert_text.delete("1.0", "end")
        self.alert_text.insert("1.0", "\n".join(self.alerts))
        self.alert_text.configure(state="disabled")

    def _upload_data(self):
        def _do():
            try:
                for zone in self.zones:
                    data = json.dumps({
                        "zone_id": zone.zone_id,
                        "temperature": round(zone.temperature, 1),
                        "smoke": round(zone.smoke, 1),
                        "status": zone.status,
                        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        "%s/v4/datas" % API_URL,
                        data=data,
                        headers={"Content-Type": "application/json",
                                 "Authorization": "Bearer %s" % API_TOKEN}
                    )
                    urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _export_data(self):
        filename = "fire_data_%s.csv" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("区域,温度,烟雾,状态\n")
            for z in self.zones:
                f.write("%s,%.1f,%.1f,%s\n" % (z.name, z.temperature, z.smoke, z.status))
        messagebox.showinfo("导出成功", "数据已导出到 %s" % filename)

    def _mute_alert(self):
        messagebox.showinfo("提示", "报警已静音/取消静音")

    def _start_data_loop(self):
        def _loop():
            while True:
                self.root.after(0, self._update_zones)
                self.root.after(0, self._upload_data)
                time.sleep(3)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def _update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.configure(text=now)
        self.root.after(1000, self._update_clock)


if __name__ == "__main__":
    root = tk.Tk()
    app = FireMonitorApp(root)
    root.mainloop()