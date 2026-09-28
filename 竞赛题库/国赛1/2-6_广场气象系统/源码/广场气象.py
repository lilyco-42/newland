# -*- coding: utf-8 -*-
"""
广场气象系统（子任务2-6）
=======================================
功能：
    1. 调用物联网云服务系统 API，读取选手个人账户下百叶箱传感器的最新
       温度(m_louverbox_temp)、湿度(m_louverbox_hum)数据及其采集时间。
    2. 启动后每隔 10 秒读取一次数据。
    3. 实时显示：最新温度值、温度采集时间、最新湿度值、湿度采集时间。
    4. 绘制“温度-时间”折线图 与“湿度-时间”折线图，随采集实时更新。
    5. demo 模式：无硬件/无网络时用内置模拟数据验证界面与图表。

运行环境：Python 3.x + tkinter + requests
运行方法：python 广场气象.py
打包 exe：pyinstaller -F -w 广场气象.py  -> 重命名为 c2.exe
"""
import json
import os
import random
import sys
import threading
import time
import tkinter as tk
from datetime import datetime

sys.dont_write_bytecode = True

import nle_cloud
from nle_cloud import create_client, normalize_number

# 配置文件与本程序同目录
if getattr(sys, "frozen", False):
    HERE = os.path.dirname(sys.executable)
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
CFG_PATH = os.path.join(HERE, "config.json")

DEFAULT_CFG = {
    "server_url": "http://192.168.0.138",
    "username": "",
    "password": "",
    "mode": "demo",                 # cloud=真实云, demo=模拟
    "tag_temp": "m_louverbox_temp",
    "tag_hum": "m_louverbox_hum",
    "refresh_second": 10,           # 题目要求每隔 10 秒读一次
}

MAX_POINTS = 30                     # 折线图保留的最大数据点


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    if os.path.isfile(CFG_PATH):
        try:
            with open(CFG_PATH, "r", encoding="utf-8") as f:
                cfg.update(json.load(f))
        except Exception:
            pass
    else:
        save_cfg(cfg)
    return cfg


def save_cfg(cfg):
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


# ---------------- 模拟客户端（无硬件验证用） ---------------- #
class DemoClient(object):
    def __init__(self):
        self.temp = 26.0
        self.hum = 60.0

    def login(self, username=None, password=None):
        return True, "演示模式登录成功(模拟百叶箱数据)"

    def fetch_sensor(self, tags, device_ids=None):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.temp = max(18.0, min(35.0, self.temp + random.uniform(-0.8, 0.8)))
        self.hum = max(35.0, min(85.0, self.hum + random.uniform(-2.0, 2.0)))
        out = {}
        for tag in tags:
            t = str(tag).lower()
            v = self.temp if "temp" in t else self.hum
            out[tag] = {"value": round(v, 1), "time": now,
                        "device": "模拟百叶箱", "device_id": 1}
        return out


# ---------------- 折线图组件 ---------------- #
class LineChart(tk.Canvas):
    """简易 tkinter 折线图：自动缩放 Y 轴，X 轴为采样序号。"""

    def __init__(self, master, title, unit, color, **kw):
        super(LineChart, self).__init__(master, **kw)
        self.title = title
        self.unit = unit
        self.color = color
        self.points = []            # [(x序号, y值), ...]

    def push(self, value):
        if value is None:
            return
        self.points.append(value)
        if len(self.points) > MAX_POINTS:
            self.points.pop(0)
        self.redraw()

    def redraw(self):
        self.delete("all")
        w = int(self["width"]); h = int(self["height"])
        pad_l, pad_r, pad_t, pad_b = 44, 12, 26, 22
        # 标题
        self.create_text(pad_l, 8, anchor="w",
                         text="%s（%s）" % (self.title, self.unit),
                         font=("Microsoft YaHei", 11, "bold"), fill="#333")
        if len(self.points) < 2:
            self.create_text(w // 2, h // 2, text="采集中...", fill="#999")
            return
        lo = min(self.points); hi = max(self.points)
        if hi - lo < 1:
            hi = lo + 1
        # 网格与坐标轴
        self.create_line(pad_l, pad_t, pad_l, h - pad_b, fill="#888")          # Y轴
        self.create_line(pad_l, h - pad_b, w - pad_r, h - pad_b, fill="#888")  # X轴
        # Y 刻度
        for i in range(5):
            gy = pad_t + (h - pad_t - pad_b) * i / 4.0
            val = hi - (hi - lo) * i / 4.0
            self.create_text(pad_l - 4, gy, anchor="e",
                             text="%.0f" % val, font=("Consolas", 8), fill="#666")
            self.create_line(pad_l, gy, w - pad_r, gy, fill="#EEE")
        # 折线
        n = len(self.points)
        pts = []
        for i, v in enumerate(self.points):
            x = pad_l + (w - pad_l - pad_r) * i / float(MAX_POINTS - 1)
            y = (h - pad_b) - (h - pad_t - pad_b) * (v - lo) / (hi - lo)
            pts.extend([x, y])
        self.create_line(pts, fill=self.color, width=2, smooth=True)
        # 最新点
        lx, ly = pts[-2], pts[-1]
        self.create_oval(lx - 3, ly - 3, lx + 3, ly + 3, fill=self.color, outline="")


# ---------------- 主程序 ---------------- #
class WeatherApp(object):
    def __init__(self, root):
        self.root = root
        self.cfg = load_cfg()
        self.tag_temp = self.cfg.get("tag_temp", "m_louverbox_temp")
        self.tag_hum = self.cfg.get("tag_hum", "m_louverbox_hum")
        self.interval = int(float(self.cfg.get("refresh_second", 10)))
        if self.interval < 1:
            self.interval = 10

        self.client = None
        self.logged = False
        self.temp = None
        self.hum = None
        self.temp_time = "--"
        self.hum_time = "--"
        self._after_id = None

        self._build_ui()
        self._login()
        self._refresh()

    def _build_ui(self):
        self.root.title("广场气象系统")
        self.root.geometry("860x620")
        self.root.configure(bg="#F5F8FB")

        # 标题栏
        tk.Label(self.root, text="广场气象监测系统",
                 font=("Microsoft YaHei", 16, "bold"), bg="#1565C0",
                 fg="#fff", pady=10).pack(fill="x")

        # 数值显示区：温度值/时间、湿度值/时间
        top = tk.Frame(self.root, bg="#F5F8FB")
        top.pack(fill="x", padx=12, pady=8)

        self.lb_temp_val = tk.Label(top, text="--", font=("Microsoft YaHei", 28, "bold"),
                                    fg="#E65100", bg="#F5F8FB")
        self.lb_temp_val.pack(side="left", padx=20)
        self.lb_temp_time = tk.Label(top, text="温度采集时间: --",
                                     font=("Microsoft YaHei", 10), fg="#666", bg="#F5F8FB")
        self.lb_temp_time.pack(side="left", padx=6)

        self.lb_hum_val = tk.Label(top, text="--", font=("Microsoft YaHei", 28, "bold"),
                                   fg="#2E7D32", bg="#F5F8FB")
        self.lb_hum_val.pack(side="right", padx=20)
        self.lb_hum_time = tk.Label(top, text="湿度采集时间: --",
                                    font=("Microsoft YaHei", 10), fg="#666", bg="#F5F8FB")
        self.lb_hum_time.pack(side="right", padx=6)

        # 两个折线图
        charts = tk.Frame(self.root, bg="#F5F8FB")
        charts.pack(fill="both", expand=True, padx=12, pady=6)
        self.temp_chart = LineChart(charts, "温度-时间", "°C", "#E65100",
                                    width=800, height=220, bg="white", highlightthickness=1)
        self.temp_chart.pack(pady=4)
        self.hum_chart = LineChart(charts, "湿度-时间", "%RH", "#2E7D32",
                                   width=800, height=220, bg="white", highlightthickness=1)
        self.hum_chart.pack(pady=4)

        # 状态栏
        self.status = tk.StringVar(value="状态: 正在初始化...")
        tk.Label(self.root, textvariable=self.status, font=("Microsoft YaHei", 9),
                 fg="#888").pack(side="bottom", pady=4)

    def _login(self):
        mode = self.cfg.get("mode", "demo")
        server = self.cfg.get("server_url", "")
        user = self.cfg.get("username", "")
        pwd = self.cfg.get("password", "")
        if mode == "demo":
            self.client = DemoClient()
        else:
            self.client = create_client(mode, server, user, pwd)
        ok, msg = self.client.login(user, pwd)
        self.logged = ok
        self.status.set("状态: %s" % msg)

    def _refresh(self):
        if not self.logged:
            self._login()
        try:
            tags = [self.tag_temp, self.tag_hum]
            data = self.client.fetch_sensor(tags)
            t_item = data.get(self.tag_temp) or {}
            h_item = data.get(self.tag_hum) or {}
            self.temp = normalize_number(t_item.get("value"))
            self.hum = normalize_number(h_item.get("value"))
            self.temp_time = t_item.get("time") or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            self.hum_time = h_item.get("time") or self.temp_time

            self.lb_temp_val.config(text="%.1f °C" % self.temp if self.temp is not None else "--")
            self.lb_temp_time.config(text="温度采集时间: %s" % self.temp_time)
            self.lb_hum_val.config(text="%.0f %%RH" % self.hum if self.hum is not None else "--")
            self.lb_hum_time.config(text="湿度采集时间: %s" % self.hum_time)

            self.temp_chart.push(self.temp)
            self.hum_chart.push(self.hum)
            self.status.set("状态: 数据正常，每 %d 秒刷新一次" % self.interval)
        except Exception as exc:
            self.status.set("状态: 数据读取失败 %s" % exc)

        self._after_id = self.root.after(self.interval * 1000, self._refresh)

    def on_close(self):
        if self._after_id is not None:
            try:
                self.root.after_cancel(self._after_id)
            except Exception:
                pass
        self.root.destroy()


def main():
    root = tk.Tk()
    app = WeatherApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
