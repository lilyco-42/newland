# -*- coding: utf-8 -*-
"""水质监测系统 - Python 3.6 兼容版"""
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

# 监测点位
MONITOR_POINTS = [
    {"id": "M01", "name": "进水口", "location": "A栋旁"},
    {"id": "M02", "name": "沉淀池", "location": "中央区域"},
    {"id": "M03", "name": "养殖区", "location": "B栋旁"},
    {"id": "M04", "name": "排水口", "location": "C栋旁"},
]

# 阈值配置
PH_LOW = 6.0
PH_HIGH = 8.5
TURBIDITY_HIGH = 50.0
DO_LOW = 5.0
TEMP_HIGH = 35.0
AMMONIA_HIGH = 2.0


class WaterQualityPoint:
    def __init__(self, info):
        self.id = info["id"]
        self.name = info["name"]
        self.location = info["location"]
        self.ph = 7.0 + random.uniform(-0.5, 0.5)
        self.turbidity = 15.0 + random.random() * 20
        self.do_val = 7.0 + random.random() * 2
        self.temperature = 22.0 + random.random() * 8
        self.ammonia = 0.5 + random.random() * 1.0
        self.status = "normal"
        self.alerts = []

    def update_data(self):
        self.ph += random.uniform(-0.1, 0.1)
        self.ph = max(4.0, min(10.0, self.ph))
        self.turbidity += random.uniform(-2, 2)
        self.turbidity = max(0, min(100, self.turbidity))
        self.do_val += random.uniform(-0.3, 0.3)
        self.do_val = max(0, min(15, self.do_val))
        self.temperature += random.uniform(-0.3, 0.3)
        self.temperature = max(10, min(45, self.temperature))
        self.ammonia += random.uniform(-0.1, 0.1)
        self.ammonia = max(0, min(5, self.ammonia))

        self.status = "normal"
        self.alerts = []
        if self.ph < PH_LOW or self.ph > PH_HIGH:
            self.status = "warning"
            self.alerts.append("pH异常: %.1f" % self.ph)
        if self.turbidity > TURBIDITY_HIGH:
            self.status = "warning"
            self.alerts.append("浊度过高: %.1f NTU" % self.turbidity)
        if self.do_val < DO_LOW:
            self.status = "danger"
            self.alerts.append("溶解氧不足: %.1f mg/L" % self.do_val)
        if self.temperature > TEMP_HIGH:
            self.status = "warning"
            self.alerts.append("温度过高: %.1f°C" % self.temperature)
        if self.ammonia > AMMONIA_HIGH:
            self.status = "danger"
            self.alerts.append("氨氮超标: %.1f mg/L" % self.ammonia)


class WaterQualityApp:
    def __init__(self, root):
        self.root = root
        self.root.title("水质监测系统")
        self.root.geometry("1050x700")
        self.root.configure(bg="#0a1628")

        self.points = [WaterQualityPoint(p) for p in MONITOR_POINTS]
        self.point_labels = []
        self._build_ui()
        self._update_clock()
        self._start_data_loop()

    def _build_ui(self):
        # 顶部
        header = tk.Frame(self.root, bg="#0c2d6b", height=50)
        header.pack(fill="x")
        tk.Label(header, text="水质监测系统", font=("微软雅黑", 20, "bold"),
                 fg="#388bfd", bg="#0c2d6b").pack(side="left", padx=20)
        self.clock_label = tk.Label(header, text="", font=("微软雅黑", 12), fg="#aaa", bg="#0c2d6b")
        self.clock_label.pack(side="right", padx=20)
        self.status_label = tk.Label(header, text="● 系统运行中", font=("微软雅黑", 11),
                                     fg="#56d364", bg="#0c2d6b")
        self.status_label.pack(side="right", padx=20)

        main = tk.Frame(self.root, bg="#0a1628")
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧 - 监测点数据
        left = tk.Frame(main, bg="#0a1628")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        tk.Label(left, text="监测点位", font=("微软雅黑", 13, "bold"),
                 fg="#388bfd", bg="#0a1628").pack(anchor="w", pady=(0, 5))

        self.point_labels = []
        for i, point in enumerate(self.points):
            frame = tk.Frame(left, bg="#112240", padx=12, pady=10, bd=1, relief="solid")
            frame.pack(fill="x", pady=5)
            # 标题行
            title_frame = tk.Frame(frame, bg="#112240")
            title_frame.pack(fill="x")
            name_lbl = tk.Label(title_frame, text="%s %s" % (point.id, point.name),
                                font=("微软雅黑", 12, "bold"), fg="#388bfd", bg="#112240")
            name_lbl.pack(side="left")
            loc_lbl = tk.Label(title_frame, text="(%s)" % point.location,
                               font=("微软雅黑", 9), fg="#8b949e", bg="#112240")
            loc_lbl.pack(side="left", padx=5)
            status_lbl = tk.Label(title_frame, text="正常", font=("微软雅黑", 9, "bold"),
                                  fg="#56d364", bg="#112240")
            status_lbl.pack(side="right")
            # 数据行
            data_frame = tk.Frame(frame, bg="#112240")
            data_frame.pack(fill="x", pady=(5, 0))
            ph_lbl = tk.Label(data_frame, text="pH: 7.0", font=("微软雅黑", 10), fg="#a29bfe", bg="#112240")
            ph_lbl.pack(side="left", padx=(0, 15))
            turb_lbl = tk.Label(data_frame, text="浊度: 15 NTU", font=("微软雅黑", 10), fg="#ffeaa7", bg="#112240")
            turb_lbl.pack(side="left", padx=(0, 15))
            do_lbl = tk.Label(data_frame, text="DO: 7.0 mg/L", font=("微软雅黑", 10), fg="#00cec9", bg="#112240")
            do_lbl.pack(side="left", padx=(0, 15))
            temp_lbl = tk.Label(data_frame, text="温度: 22°C", font=("微软雅黑", 10), fg="#ff6b6b", bg="#112240")
            temp_lbl.pack(side="left", padx=(0, 15))
            nh3_lbl = tk.Label(data_frame, text="氨氮: 0.5 mg/L", font=("微软雅黑", 10), fg="#fdcb6e", bg="#112240")
            nh3_lbl.pack(side="left")
            self.point_labels.append({
                "frame": frame, "name": name_lbl, "status": status_lbl,
                "ph": ph_lbl, "turbidity": turb_lbl, "do": do_lbl,
                "temp": temp_lbl, "ammonia": nh3_lbl
            })

        # 右侧 - 报警与统计
        right = tk.Frame(main, bg="#0a1628", width=320)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # 统计
        tk.Label(right, text="实时统计", font=("微软雅黑", 13, "bold"),
                 fg="#388bfd", bg="#0a1628").pack(anchor="w", pady=(0, 5))
        stats_frame = tk.Frame(right, bg="#112240", padx=10, pady=10)
        stats_frame.pack(fill="x", pady=(0, 10))
        self.stat_normal = tk.Label(stats_frame, text="正常: 0", font=("微软雅黑", 11),
                                    fg="#56d364", bg="#112240")
        self.stat_normal.pack(side="left", padx=5)
        self.stat_warn = tk.Label(stats_frame, text="预警: 0", font=("微软雅黑", 11),
                                  fg="#e3b341", bg="#112240")
        self.stat_warn.pack(side="left", padx=5)
        self.stat_danger = tk.Label(stats_frame, text="异常: 0", font=("微软雅黑", 11),
                                    fg="#ff7b72", bg="#112240")
        self.stat_danger.pack(side="left", padx=5)

        # 平均值
        avg_frame = tk.Frame(right, bg="#112240", padx=10, pady=10)
        avg_frame.pack(fill="x", pady=(0, 10))
        self.avg_ph = tk.Label(avg_frame, text="平均pH: 7.0", font=("微软雅黑", 11, "bold"),
                               fg="#a29bfe", bg="#112240")
        self.avg_ph.pack(fill="x")
        self.avg_turb = tk.Label(avg_frame, text="平均浊度: 15 NTU", font=("微软雅黑", 11, "bold"),
                                 fg="#ffeaa7", bg="#112240")
        self.avg_turb.pack(fill="x")
        self.avg_do = tk.Label(avg_frame, text="平均DO: 7.0 mg/L", font=("微软雅黑", 11, "bold"),
                               fg="#00cec9", bg="#112240")
        self.avg_do.pack(fill="x")

        ttk.Separator(right).pack(fill="x", pady=5)

        # 阈值设置
        tk.Label(right, text="报警阈值", font=("微软雅黑", 13, "bold"),
                 fg="#388bfd", bg="#0a1628").pack(anchor="w", pady=(5, 5))
        thresh_frame = tk.Frame(right, bg="#112240", padx=10, pady=8)
        thresh_frame.pack(fill="x", pady=(0, 10))
        thresholds = [
            ("pH范围", "6.0 - 8.5"),
            ("浊度上限", "50 NTU"),
            ("DO下限", "5.0 mg/L"),
            ("温度上限", "35°C"),
            ("氨氮上限", "2.0 mg/L"),
        ]
        for label, val in thresholds:
            row = tk.Frame(thresh_frame, bg="#112240")
            row.pack(fill="x", pady=1)
            tk.Label(row, text=label, font=("微软雅黑", 9), fg="#8b949e", bg="#112240").pack(side="left")
            tk.Label(row, text=val, font=("微软雅黑", 9, "bold"), fg="#e6e6e6", bg="#112240").pack(side="right")

        ttk.Separator(right).pack(fill="x", pady=5)

        # 报警日志
        tk.Label(right, text="报警日志", font=("微软雅黑", 13, "bold"),
                 fg="#ff4444", bg="#0a1628").pack(anchor="w", pady=(5, 5))
        self.alert_text = tk.Text(right, height=10, font=("微软雅黑", 9), bg="#112240", fg="#e6e6e6",
                                  state="disabled", relief="flat", wrap="word")
        self.alert_text.pack(fill="both", expand=True)

        # 控制
        btn_frame = tk.Frame(right, bg="#0a1628")
        btn_frame.pack(fill="x", pady=5)
        tk.Button(btn_frame, text="导出数据", font=("微软雅黑", 10), bg="#238636", fg="white",
                  command=self._export_data).pack(side="left", fill="x", expand=True, padx=2)

    def _update_data(self):
        normal = warn = danger = 0
        all_alerts = []
        avg_ph = avg_turb = avg_do = 0

        for i, point in enumerate(self.points):
            point.update_data()
            if point.status == "normal":
                normal += 1
            elif point.status == "warning":
                warn += 1
            else:
                danger += 1

            avg_ph += point.ph
            avg_turb += point.turbidity
            avg_do += point.do_val

            if i < len(self.point_labels):
                lbls = self.point_labels[i]
                status_color = "#56d364" if point.status == "normal" else (
                    "#e3b341" if point.status == "warning" else "#ff7b72")
                status_text = "正常" if point.status == "normal" else (
                    "预警" if point.status == "warning" else "异常")
                lbls["status"].configure(text=status_text, fg=status_color)
                lbls["ph"].configure(text="pH: %.1f" % point.ph)
                lbls["turbidity"].configure(text="浊度: %.1f NTU" % point.turbidity)
                lbls["do"].configure(text="DO: %.1f mg/L" % point.do_val)
                lbls["temp"].configure(text="温度: %.1f°C" % point.temperature)
                lbls["ammonia"].configure(text="氨氮: %.1f mg/L" % point.ammonia)

            for a in point.alerts:
                all_alerts.append("[%s] %s: %s" % (point.id, point.name, a))

        n = len(self.points)
        self.stat_normal.configure(text="正常: %d" % normal)
        self.stat_warn.configure(text="预警: %d" % warn)
        self.stat_danger.configure(text="异常: %d" % danger)
        self.avg_ph.configure(text="平均pH: %.1f" % (avg_ph / n))
        self.avg_turb.configure(text="平均浊度: %.1f NTU" % (avg_turb / n))
        self.avg_do.configure(text="平均DO: %.1f mg/L" % (avg_do / n))

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        log_lines = ["[%s] %s" % (ts, a) for a in all_alerts]
        if not log_lines:
            log_lines = ["[%s] 所有监测点数据正常" % ts]
        self.alert_text.configure(state="normal")
        self.alert_text.delete("1.0", "end")
        self.alert_text.insert("1.0", "\n".join(log_lines))
        self.alert_text.configure(state="disabled")

    def _upload_data(self):
        def _do():
            try:
                for point in self.points:
                    data = json.dumps({
                        "point_id": point.id, "name": point.name,
                        "ph": round(point.ph, 1),
                        "turbidity": round(point.turbidity, 1),
                        "do": round(point.do_val, 1),
                        "temperature": round(point.temperature, 1),
                        "ammonia": round(point.ammonia, 2),
                        "status": point.status,
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
        filename = "water_quality_%s.csv" % datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        with open(filename, "w", encoding="utf-8") as f:
            f.write("监测点ID,名称,位置,pH,浊度NTU,溶解氧mg/L,温度°C,氨氮mg/L,状态\n")
            for p in self.points:
                f.write("%s,%s,%s,%.1f,%.1f,%.1f,%.1f,%.2f,%s\n" % (
                    p.id, p.name, p.location, p.ph, p.turbidity,
                    p.do_val, p.temperature, p.ammonia, p.status))
        messagebox.showinfo("导出成功", "数据已导出到 %s" % filename)

    def _start_data_loop(self):
        def _loop():
            while True:
                self.root.after(0, self._update_data)
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
    app = WaterQualityApp(root)
    root.mainloop()