# -*- coding: utf-8 -*-
"""
钻井深度监测功能开发（第2套 模块二 2-6）
超声波传感器模拟钻井深度监测；频闪红灯、常亮绿灯接入联动控制器。

功能：
  1. 每 5 秒获取一次超声波数据并显示；同时动态绘制“数据-时间”折线图（仅显示最近 6 次）
  2. 超声波数据 >= 50cm -> 频闪红灯亮（界面红灯动画），红灯灭绿灯灭
  3. 超声波数据 <  50cm -> 常亮绿灯亮（界面绿灯动画），绿灯灭红灯灭
  4. 点击“导出Excel”：最近 20 条监测数据按记录时间倒序导出
     （导出记录包含“时间”和“超声波数据”两列）
  5. 数据/控制走串口（联动控制器）直连，不使用云服务系统

数据帧示例（按实际联动控制器协议调整）：
  dist:63.5   或  D:63.5\r\n   等
运行：python drilling_monitor.py
打包：pyinstaller -F -w -n 钻井深度监测 drilling_monitor.py
"""
import json
import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "serial": {"port": "COM6", "baud": 115200, "enabled": True},
    "threshold": 50,
    "sample_interval_sec": 5,
    "chart_points": 6,
    "export_rows": 20,
    "export_dir": "导出",
}

COLOR_BG = "#1e272e"
COLOR_PANEL = "#2f3640"
COLOR_TEXT = "#f5f6fa"
COLOR_RED = "#e84118"
COLOR_GREEN = "#44bd32"
COLOR_OFF = "#576574"


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict):
                for k, v in data.items():
                    cfg[k] = v
        except Exception:
            pass
    return cfg


class SerialPoller(threading.Thread):
    """轮询串口（联动控制器/超声波）获取距离。"""

    def __init__(self, cfg, q):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.q = q
        self.running = True

    def run(self):
        while self.running:
            try:
                if not self.cfg["serial"]["enabled"]:
                    time.sleep(3)
                    continue
                import serial
                ser = serial.Serial(self.cfg["serial"]["port"],
                                    self.cfg["serial"]["baud"], timeout=2)
                buf = b""
                while self.running:
                    chunk = ser.read(128)
                    if not chunk:
                        continue
                    buf += chunk
                    while b"\n" in buf:
                        line, _, buf = buf.partition(b"\n")
                        line = line.strip()
                        if line:
                            self.q.put(line.decode("utf-8", "ignore"))
                ser.close()
            except Exception as exc:
                self.q.put(("ERR", str(exc)))
                time.sleep(3)


class DrillApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("钻井深度监测")
        root.geometry("660x560")
        root.configure(bg=COLOR_BG)
        self.q = queue.Queue()
        self.poller = SerialPoller(cfg, self.q)
        self.poller.start()

        self.dist = 0.0
        self.history = []          # (time_str, value) 全量，用于导出
        self.chart_vals = []       # 最近 6 次，仅用于折线图
        self.red_on = False
        self.green_on = False
        self.blink = False

        self._build_ui()
        self._poll()
        self._sample()
        self._animate()

    # ---------------------------------------------------------- UI
    def _build_ui(self):
        top = tk.Frame(self.root, bg=COLOR_PANEL, padx=10, pady=8)
        top.pack(fill="x", padx=8, pady=8)

        self.lbl_dist = tk.Label(top, text="超声波数据：-- cm", fg="#00d8d6",
                                 bg=COLOR_PANEL, font=("Consolas", 26, "bold"))
        self.lbl_dist.pack(side="left", padx=12)

        # 灯图标：Canvas 红/绿灯
        self.red_cv = tk.Canvas(top, width=64, height=64, bg=COLOR_PANEL, highlightthickness=0)
        self.red_cv.pack(side="left", padx=8)
        self.red_lamp = self.red_cv.create_oval(12, 12, 52, 52, fill=COLOR_OFF, outline="#fff")
        self.red_lbl = tk.Label(top, text="频闪红灯", fg=COLOR_TEXT, bg=COLOR_PANEL)
        self.red_lbl.pack(side="left")

        self.green_cv = tk.Canvas(top, width=64, height=64, bg=COLOR_PANEL, highlightthickness=0)
        self.green_cv.pack(side="left", padx=8)
        self.green_lamp = self.green_cv.create_oval(12, 12, 52, 52, fill=COLOR_OFF, outline="#fff")
        self.green_lbl = tk.Label(top, text="常亮绿灯", fg=COLOR_TEXT, bg=COLOR_PANEL)
        self.green_lbl.pack(side="left")

        tk.Button(top, text="导出Excel", command=self._export,
                  bg="#1e90ff", fg="white").pack(side="right", padx=8)

        # 折线图
        chart_frm = tk.Frame(self.root, bg=COLOR_PANEL)
        chart_frm.pack(fill="both", expand=True, padx=8, pady=6)
        tk.Label(chart_frm, text="数据-时间折线图（最近6次）", fg=COLOR_TEXT,
                 bg=COLOR_PANEL).pack()
        self.chart = tk.Canvas(chart_frm, width=620, height=280, bg="#0f1420",
                               highlightthickness=0)
        self.chart.pack(fill="both", expand=True, padx=6, pady=4)

        self.status = tk.StringVar(value="串口：未连接")
        tk.Label(self.root, textvariable=self.status, fg="#7f8c8d", bg=COLOR_BG,
                 font=("Microsoft YaHei", 9)).pack(side="bottom", pady=4)

    # ---------------------------------------------------------- logic
    def _extract_dist(self, line):
        """从帧中解析超声波距离(cm)。按实际协议调整。"""
        try:
            text = line.strip()
            for marker in ("dist:", "D:", "距离:"):
                if marker in text:
                    number = text.split(marker, 1)[1].strip().split()[0]
                    return float(number)
            # 纯数字：默认 cm
            if text.replace(".", "", 1).isdigit():
                return float(text)
        except Exception:
            pass
        return None

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if isinstance(item, tuple):
                    self.status.set("串口：%s" % item[1])
                elif isinstance(item, str):
                    v = self._extract_dist(item)
                    if v is not None:
                        self._on_sample(v)
        except queue.Empty:
            pass
        self.root.after(150, self._poll)

    def _sample(self):
        """定时模拟采样兜底：若串口未启用，用随机值演示界面效果。"""
        if not self.cfg["serial"]["enabled"]:
            import random
            self._on_sample(round(random.uniform(20, 80), 1))
        self.root.after(int(self.cfg["sample_interval_sec"] * 1000), self._sample)

    def _on_sample(self, value):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.dist = value
        self.history.append((now, value))
        self.chart_vals.append(value)
        # 折线图仅显示最近 6 次
        n = self.cfg["chart_points"]
        if len(self.chart_vals) > n:
            self.chart_vals = self.chart_vals[-n:]
        self.lbl_dist.config(text="超声波数据：%.1f cm" % value)
        # 阈值控制
        th = self.cfg["threshold"]
        self.red_on = value >= th
        self.green_on = value < th
        # 联动控制器下发（不与云服务通信；此处串口写控制帧占位）
        # self._send_lamp("red", 1 if self.red_on else 0)
        # self._send_lamp("green", 1 if self.green_on else 0)
        self._draw_chart()

    def _draw_chart(self):
        c = self.chart
        c.delete("all")
        w, h = int(c["width"]), int(c["height"])
        if not self.chart_vals:
            return
        vmin, vmax = 0, 100
        lo, hi = min(self.chart_vals), max(self.chart_vals)
        if lo == hi:
            lo, hi = lo - 10, hi + 10
        pad = 30
        step_total = max(len(self.chart_vals) - 1, 1)
        pts = []
        for i, v in enumerate(self.chart_vals):
            x = pad + i * (w - 2 * pad) / step_total
            y = h - pad - (v - lo) * (h - 2 * pad) / (hi - lo)
            pts.append((x, y))
        # 网格线
        for g in range(0, 6):
            gy = pad + g * (h - 2 * pad) / 5
            c.create_line(pad, gy, w - pad, gy, fill="#22303c")
        # 折线 + 点
        for i in range(len(pts) - 1):
            c.create_line(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1],
                          fill="#00d8d6", width=2)
        for x, y in pts:
            c.create_oval(x - 3, y - 3, x + 3, y + 3, fill="#00d8d6")
        # 时间标签（最近一次）
        c.create_text(w - pad, h - 10, text=self.history[-1][0], fill="#7f8c8d",
                      anchor="se", font=("Consolas", 8))

    def _animate(self):
        if self.red_on:
            fill = COLOR_RED if self.blink else COLOR_OFF
        else:
            fill = COLOR_OFF
        self.red_cv.itemconfig(self.red_lamp, fill=fill)
        self.green_cv.itemconfig(
            self.green_lamp, fill=COLOR_GREEN if self.green_on else COLOR_OFF)
        self.blink = not self.blink
        self.root.after(400, self._animate)

    def _export(self):
        """导出最近 20 条，按记录时间倒序（时间、超声波数据两列）。"""
        rows = sorted(self.history, key=lambda r: r[0], reverse=True)[:self.cfg["export_rows"]]
        if not rows:
            return
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         self.cfg["export_dir"])
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "超声波数据_%s.xlsx" % datetime.now().strftime("%Y%m%d_%H%M%S"))
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "超声波数据"
            ws.append(["时间", "超声波数据"])
            for t, v in rows:
                ws.append([t, v])
            wb.save(path)
            self.status.set("已导出：%s" % path)
        except ImportError:
            # 兜底：导出 CSV（Excel 可直接打开）
            import csv
            path = path.replace(".xlsx", ".csv")
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["时间", "超声波数据"])
                for t, v in rows:
                    w.writerow([t, v])
            self.status.set("已导出（csv）：%s" % path)


def main():
    cfg = load_config()
    root = tk.Tk()
    DrillApp(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()