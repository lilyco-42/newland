# -*- coding: utf-8 -*-
"""物流运输监控系统 - Python 3.6 兼容版"""
import tkinter as tk
from tkinter import ttk, messagebox
import time
import datetime
import json
import math
import threading
import random

try:
    import urllib.request
except ImportError:
    pass

API_URL = "http://api.nlecloud.com"
API_TOKEN = "your_token_here"

# 车辆配置
VEHICLES = [
    {"id": "V001", "plate": "粤A·12345", "route": "广州-深圳", "driver": "张师傅"},
    {"id": "V002", "plate": "粤B·67890", "route": "广州-东莞", "driver": "李师傅"},
    {"id": "V003", "plate": "粤C·11111", "route": "广州-佛山", "driver": "王师傅"},
    {"id": "V004", "plate": "粤D·22222", "route": "广州-珠海", "driver": "赵师傅"},
    {"id": "V005", "plate": "粤E·33333", "route": "广州-惠州", "driver": "刘师傅"},
]

# 城市坐标 (简化)
CITIES = {
    "广州": (23.13, 113.26), "深圳": (22.55, 114.06), "东莞": (23.04, 113.75),
    "佛山": (23.02, 113.12), "珠海": (22.27, 113.58), "惠州": (23.11, 114.42),
}


class Vehicle:
    def __init__(self, info):
        self.id = info["id"]
        self.plate = info["plate"]
        self.route = info["route"]
        self.driver = info["driver"]
        self.cities = self.route.split("-")
        self.lat = CITIES[self.cities[0]][0]
        self.lng = CITIES[self.cities[0]][1]
        self.temp = 2.0 + random.random() * 3
        self.speed = 60 + random.random() * 40
        self.status = "行驶中"
        self.progress = 0.0
        self.alerts = []

    def update_position(self):
        if self.progress < 1.0:
            self.progress += random.uniform(0.005, 0.02)
            if self.progress > 1.0:
                self.progress = 1.0
                self.status = "已到达"
            start = CITIES[self.cities[0]]
            end = CITIES[self.cities[1]]
            self.lat = start[0] + (end[0] - start[0]) * self.progress
            self.lng = start[1] + (end[1] - start[1]) * self.progress
            self.speed = 60 + random.random() * 40
            self.temp += random.uniform(-0.3, 0.3)
            self.temp = max(-5.0, min(15.0, self.temp))
            if self.temp > 8.0:
                self.status = "温度预警"
                self.alerts.append("温度过高: %.1f°C" % self.temp)
            elif self.temp < -2.0:
                self.status = "温度预警"
                self.alerts.append("温度过低: %.1f°C" % self.temp)


class TransportMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("物流运输监控系统")
        self.root.geometry("1050x680")
        self.root.configure(bg="#0d1117")

        self.vehicles = [Vehicle(v) for v in VEHICLES]
        self.selected_vehicle = 0
        self._build_ui()
        self._update_clock()
        self._start_data_loop()

    def _build_ui(self):
        # 顶部
        header = tk.Frame(self.root, bg="#161b22", height=50)
        header.pack(fill="x")
        tk.Label(header, text="物流运输监控系统", font=("微软雅黑", 20, "bold"),
                 fg="#388bfd", bg="#161b22").pack(side="left", padx=20)
        self.clock_label = tk.Label(header, text="", font=("微软雅黑", 12), fg="#aaa", bg="#161b22")
        self.clock_label.pack(side="right", padx=20)

        main = tk.Frame(self.root, bg="#0d1117")
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧 - 车辆列表与地图
        left = tk.Frame(main, bg="#0d1117")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 车辆列表
        tk.Label(left, text="运输车辆", font=("微软雅黑", 13, "bold"),
                 fg="#388bfd", bg="#0d1117").pack(anchor="w", pady=(0, 5))
        list_frame = tk.Frame(left, bg="#161b22", bd=1, relief="solid")
        list_frame.pack(fill="x", pady=(0, 10))

        headers = ["车牌", "路线", "司机", "状态", "进度"]
        for j, h in enumerate(headers):
            tk.Label(list_frame, text=h, font=("微软雅黑", 10, "bold"),
                     fg="#388bfd", bg="#161b22", width=12, padx=5, pady=5).grid(row=0, column=j, sticky="w")

        self.vehicle_rows = []
        for i, v in enumerate(self.vehicles):
            row_frame = tk.Frame(list_frame, bg="#161b22")
            row_frame.grid(row=i + 1, column=0, columnspan=5, sticky="w", padx=5, pady=2)
            plate_lbl = tk.Label(row_frame, text=v.plate, font=("微软雅黑", 9),
                                 fg="#e6e6e6", bg="#161b22", width=12, anchor="w")
            plate_lbl.pack(side="left")
            route_lbl = tk.Label(row_frame, text=v.route, font=("微软雅黑", 9),
                                 fg="#8b949e", bg="#161b22", width=12, anchor="w")
            route_lbl.pack(side="left")
            driver_lbl = tk.Label(row_frame, text=v.driver, font=("微软雅黑", 9),
                                  fg="#8b949e", bg="#161b22", width=12, anchor="w")
            driver_lbl.pack(side="left")
            status_lbl = tk.Label(row_frame, text=v.status, font=("微软雅黑", 9),
                                  fg="#56d364", bg="#161b22", width=12, anchor="w")
            status_lbl.pack(side="left")
            prog_lbl = tk.Label(row_frame, text="0%", font=("微软雅黑", 9),
                                fg="#388bfd", bg="#161b22", width=12, anchor="w")
            prog_lbl.pack(side="left")
            self.vehicle_rows.append((plate_lbl, route_lbl, driver_lbl, status_lbl, prog_lbl))

        # 地图模拟
        tk.Label(left, text="运输路线", font=("微软雅黑", 13, "bold"),
                 fg="#388bfd", bg="#0d1117").pack(anchor="w", pady=(0, 5))
        self.map_canvas = tk.Canvas(left, bg="#161b22", highlightthickness=0, height=250)
        self.map_canvas.pack(fill="both", expand=True)

        # 右侧 - 详情与温度监控
        right = tk.Frame(main, bg="#0d1117", width=320)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # 车辆详情
        tk.Label(right, text="车辆详情", font=("微软雅黑", 13, "bold"),
                 fg="#388bfd", bg="#0d1117").pack(anchor="w", pady=(0, 5))
        self.detail_frame = tk.Frame(right, bg="#161b22", padx=10, pady=10)
        self.detail_frame.pack(fill="x", pady=(0, 10))
        self.detail_plate = tk.Label(self.detail_frame, text="车牌: -", font=("微软雅黑", 11),
                                     fg="#e6e6e6", bg="#161b22", anchor="w")
        self.detail_plate.pack(fill="x")
        self.detail_route = tk.Label(self.detail_frame, text="路线: -", font=("微软雅黑", 11),
                                     fg="#8b949e", bg="#161b22", anchor="w")
        self.detail_route.pack(fill="x")
        self.detail_speed = tk.Label(self.detail_frame, text="速度: - km/h", font=("微软雅黑", 11),
                                     fg="#56d364", bg="#161b22", anchor="w")
        self.detail_speed.pack(fill="x")
        self.detail_pos = tk.Label(self.detail_frame, text="位置: -", font=("微软雅黑", 11),
                                   fg="#8b949e", bg="#161b22", anchor="w")
        self.detail_pos.pack(fill="x")

        ttk.Separator(right).pack(fill="x", pady=5)

        # 温度监控
        tk.Label(right, text="车厢温度", font=("微软雅黑", 13, "bold"),
                 fg="#388bfd", bg="#0d1117").pack(anchor="w", pady=(5, 5))
        self.temp_canvas = tk.Canvas(right, bg="#161b22", highlightthickness=0, height=80)
        self.temp_canvas.pack(fill="x", pady=(0, 10))
        self.temp_label = tk.Label(right, text="当前温度: 2.0°C", font=("微软雅黑", 14, "bold"),
                                   fg="#388bfd", bg="#161b22")
        self.temp_label.pack(pady=(0, 5))
        self.temp_status = tk.Label(right, text="温度正常", font=("微软雅黑", 11),
                                    fg="#56d364", bg="#161b22")
        self.temp_status.pack(pady=(0, 10))

        ttk.Separator(right).pack(fill="x", pady=5)

        # 报警日志
        tk.Label(right, text="报警日志", font=("微软雅黑", 13, "bold"),
                 fg="#ff4444", bg="#0d1117").pack(anchor="w", pady=(5, 5))
        self.alert_text = tk.Text(right, height=10, font=("微软雅黑", 9), bg="#161b22", fg="#e6e6e6",
                                  state="disabled", relief="flat", wrap="word")
        self.alert_text.pack(fill="both", expand=True)

        # 控制
        btn_frame = tk.Frame(right, bg="#0d1117")
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="导出数据", font=("微软雅黑", 10), bg="#238636", fg="white",
                  command=self._export_data).pack(side="left", fill="x", expand=True, padx=2)

    def _update_vehicles(self):
        for i, v in enumerate(self.vehicles):
            v.update_position()
            if i < len(self.vehicle_rows):
                _, _, _, status_lbl, prog_lbl = self.vehicle_rows[i]
                status_color = "#56d364" if v.status == "行驶中" else "#e3b341"
                status_lbl.configure(text=v.status, fg=status_color)
                prog_lbl.configure(text="%d%%" % int(v.progress * 100))

        # 更新选中车辆详情
        v = self.vehicles[self.selected_vehicle]
        self.detail_plate.configure(text="车牌: %s" % v.plate)
        self.detail_route.configure(text="路线: %s (%s)" % (v.route, v.driver))
        self.detail_speed.configure(text="速度: %.0f km/h" % v.speed)
        self.detail_pos.configure(text="位置: %.4f, %.4f" % (v.lat, v.lng))

        # 温度
        self.temp_label.configure(text="当前温度: %.1f°C" % v.temp)
        if v.temp > 8.0:
            self.temp_status.configure(text="温度过高!", fg="#ff4444")
        elif v.temp < -2.0:
            self.temp_status.configure(text="温度过低!", fg="#ff4444")
        else:
            self.temp_status.configure(text="温度正常", fg="#56d364")

        self._draw_map()
        self._draw_temp_bar(v.temp)

        # 更新报警日志
        all_alerts = []
        for veh in self.vehicles:
            for a in veh.alerts[-3:]:
                all_alerts.append("[%s] %s: %s" % (veh.plate, veh.route, a))
        self.alert_text.configure(state="normal")
        self.alert_text.delete("1.0", "end")
        self.alert_text.insert("1.0", "\n".join(all_alerts[-10:]))
        self.alert_text.configure(state="disabled")

    def _draw_map(self):
        c = self.map_canvas
        c.update_idletasks()
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50:
            return
        c.delete("all")

        # 绘制路线
        colors = ["#388bfd", "#56d364", "#e3b341", "#ff7b72", "#bc8cff"]
        for i, v in enumerate(self.vehicles):
            start = CITIES[v.cities[0]]
            end = CITIES[v.cities[1]]
            x1 = 50 + (start[1] - 113) * (w - 100) / 2.0
            y1 = h - 30 - (start[0] - 22) * (h - 60) / 2.0
            x2 = 50 + (end[1] - 113) * (w - 100) / 2.0
            y2 = h - 30 - (end[0] - 22) * (h - 60) / 2.0
            c.create_line(x1, y1, x2, y2, fill=colors[i % len(colors)], width=2, dash=(4, 4))

            # 车辆位置
            cx = x1 + (x2 - x1) * v.progress
            cy = y1 + (y2 - y1) * v.progress
            r = 6
            c.create_oval(cx - r, cy - r, cx + r, cy + r, fill=colors[i % len(colors)], outline="white")
            c.create_text(cx, cy - 12, text=v.plate, fill=colors[i % len(colors)], font=("微软雅黑", 7))

            # 城市标注
            c.create_text(x1, y1 + 12, text=v.cities[0], fill="#8b949e", font=("微软雅黑", 8))
            c.create_text(x2, y2 + 12, text=v.cities[1], fill="#8b949e", font=("微软雅黑", 8))

    def _draw_temp_bar(self, temp):
        c = self.temp_canvas
        c.update_idletasks()
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 50:
            return
        c.delete("all")
        # 温度条
        bar_x = 40
        bar_w = w - 80
        bar_h = 20
        bar_y = (h - bar_h) / 2
        c.create_rectangle(bar_x, bar_y, bar_x + bar_w, bar_y + bar_h, outline="#30363d", width=1)
        # 温度范围 -5到15
        ratio = (temp - (-5)) / 20.0
        ratio = max(0, min(1, ratio))
        fill_x = bar_x + bar_w * ratio
        color = "#388bfd" if -2 <= temp <= 8 else "#ff4444"
        c.create_rectangle(bar_x, bar_y, fill_x, bar_y + bar_h, fill=color, outline="")
        # 标记
        c.create_text(bar_x, bar_y - 8, text="-5°C", fill="#8b949e", font=("微软雅黑", 7))
        c.create_text(bar_x + bar_w, bar_y - 8, text="15°C", fill="#8b949e", font=("微软雅黑", 7))
        c.create_text(fill_x, bar_y + bar_h + 12, text="%.1f°C" % temp, fill=color, font=("微软雅黑", 9, "bold"))

    def _upload_data(self):
        def _do():
            try:
                for v in self.vehicles:
                    data = json.dumps({
                        "vehicle_id": v.id, "plate": v.plate,
                        "lat": round(v.lat, 4), "lng": round(v.lng, 4),
                        "temperature": round(v.temp, 1), "speed": round(v.speed, 1),
                        "progress": round(v.progress, 2), "status": v.status,
                        "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }).encode("utf-8")
                    req = urllib.request.Request(
                        "%s/v4/datas" % API_URL, data=data,
                        headers={"Content-Type": "application/json",
                                 "Authorization": "Bearer %s" % API_TOKEN}
                    )
                    urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _export_data(self):
        filename = "transport_data_%s.csv" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("车牌,路线,司机,纬度,经度,温度,速度,进度,状态\n")
            for v in self.vehicles:
                f.write("%s,%s,%s,%.4f,%.4f,%.1f,%.0f,%d%%,%s\n" % (
                    v.plate, v.route, v.driver, v.lat, v.lng, v.temp, v.speed,
                    int(v.progress * 100), v.status))
        messagebox.showinfo("导出成功", "数据已导出到 %s" % filename)

    def _start_data_loop(self):
        def _loop():
            while True:
                self.root.after(0, self._update_vehicles)
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
    app = TransportMonitorApp(root)
    root.mainloop()