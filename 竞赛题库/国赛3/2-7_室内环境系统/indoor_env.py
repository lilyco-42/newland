# -*- coding: utf-8 -*-
"""室内环境监控与控制系统 - Python 3.6 兼容版"""
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


class IndoorEnvApp:
    def __init__(self, root):
        self.root = root
        self.root.title("室内环境监控与控制系统")
        self.root.geometry("1000x680")
        self.root.configure(bg="#1a1a2e")

        # 传感器数据
        self.temperature = 25.0
        self.humidity = 55.0
        self.light = 450
        self.pm25 = 35

        # 控制状态
        self.ac_on = False
        self.ac_mode = "制冷"
        self.ac_target = 26
        self.light_on = True
        self.light_brightness = 80
        self.auto_mode = True

        # 历史数据
        self.temp_history = [25.0] * 30
        self.humid_history = [55.0] * 30

        self._build_ui()
        self._update_clock()
        self._start_sensor_loop()

    def _build_ui(self):
        # 顶部
        header = tk.Frame(self.root, bg="#0f3460", height=50)
        header.pack(fill="x")
        tk.Label(header, text="室内环境监控与控制系统", font=("微软雅黑", 20, "bold"),
                 fg="#e94560", bg="#0f3460").pack(side="left", padx=20)
        self.clock_label = tk.Label(header, text="", font=("微软雅黑", 12), fg="#aaa", bg="#0f3460")
        self.clock_label.pack(side="right", padx=20)
        self.auto_btn = tk.Button(header, text="自动模式: 开", font=("微软雅黑", 10),
                                  bg="#2d6a4f", fg="white", command=self._toggle_auto)
        self.auto_btn.pack(side="right", padx=10)

        main = tk.Frame(self.root, bg="#1a1a2e")
        main.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧 - 传感器数据
        left = tk.Frame(main, bg="#1a1a2e")
        left.pack(side="left", fill="both", expand=True, padx=(0, 10))

        # 传感器卡片
        sensors_frame = tk.Frame(left, bg="#1a1a2e")
        sensors_frame.pack(fill="x", pady=5)
        self.temp_card = self._make_sensor_card(sensors_frame, "温度", "25.0°C", "#e94560", 0)
        self.humid_card = self._make_sensor_card(sensors_frame, "湿度", "55.0%", "#4ecdc4", 1)
        self.light_card = self._make_sensor_card(sensors_frame, "光照", "450 lux", "#ffd700", 2)
        self.pm25_card = self._make_sensor_card(sensors_frame, "PM2.5", "35 μg/m³", "#ff6b6b", 3)

        # 图表区域
        chart_frame = tk.Frame(left, bg="#16213e", bd=1, relief="solid")
        chart_frame.pack(fill="both", expand=True, pady=5)
        tk.Label(chart_frame, text="温湿度趋势 (最近30秒)", font=("微软雅黑", 12, "bold"),
                 fg="#e94560", bg="#16213e").pack(pady=5)
        self.chart_canvas = tk.Canvas(chart_frame, bg="#1a1a2e", highlightthickness=0)
        self.chart_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.root.after(200, self._draw_chart)

        # 右侧 - 控制面板
        right = tk.Frame(main, bg="#16213e", bd=1, relief="solid", width=300)
        right.pack(side="right", fill="y")
        right.pack_propagate(False)

        # 空调控制
        tk.Label(right, text="空调控制", font=("微软雅黑", 14, "bold"),
                 fg="#e94560", bg="#16213e").pack(pady=(15, 5))
        self.ac_frame = tk.Frame(right, bg="#0f3460", padx=10, pady=10)
        self.ac_frame.pack(fill="x", padx=15, pady=5)
        self.ac_status = tk.Label(self.ac_frame, text="状态: 关闭", font=("微软雅黑", 11),
                                  fg="#aaa", bg="#0f3460")
        self.ac_status.pack(anchor="w")
        self.ac_toggle = tk.Button(self.ac_frame, text="开启空调", font=("微软雅黑", 10, "bold"),
                                   bg="#2d6a4f", fg="white", width=20, command=self._toggle_ac)
        self.ac_toggle.pack(pady=5)
        mode_frame = tk.Frame(self.ac_frame, bg="#0f3460")
        mode_frame.pack(fill="x", pady=3)
        tk.Label(mode_frame, text="模式:", font=("微软雅黑", 10), fg="#aaa", bg="#0f3460").pack(side="left")
        self.ac_mode_var = tk.StringVar(value="制冷")
        for m in ["制冷", "制热", "送风"]:
            tk.Radiobutton(mode_frame, text=m, variable=self.ac_mode_var, value=m,
                           font=("微软雅黑", 9), fg="#eee", bg="#0f3460",
                           selectcolor="#1a1a2e", command=self._on_mode_change).pack(side="left", padx=5)
        temp_frame = tk.Frame(self.ac_frame, bg="#0f3460")
        temp_frame.pack(fill="x", pady=3)
        tk.Label(temp_frame, text="目标温度:", font=("微软雅黑", 10), fg="#aaa", bg="#0f3460").pack(side="left")
        self.temp_scale = tk.Scale(temp_frame, from_=16, to_=30, orient="horizontal",
                                   bg="#0f3460", fg="#eee", highlightthickness=0,
                                   command=self._on_temp_change)
        self.temp_scale.set(26)
        self.temp_scale.pack(side="right", fill="x", expand=True)

        ttk.Separator(right).pack(fill="x", padx=15, pady=10)

        # 灯光控制
        tk.Label(right, text="灯光控制", font=("微软雅黑", 14, "bold"),
                 fg="#ffd700", bg="#16213e").pack(pady=(0, 5))
        self.light_frame = tk.Frame(right, bg="#0f3460", padx=10, pady=10)
        self.light_frame.pack(fill="x", padx=15, pady=5)
        self.light_status = tk.Label(self.light_frame, text="状态: 开启", font=("微软雅黑", 11),
                                     fg="#ffd700", bg="#0f3460")
        self.light_status.pack(anchor="w")
        self.light_toggle = tk.Button(self.light_frame, text="关闭灯光", font=("微软雅黑", 10, "bold"),
                                      bg="#e94560", fg="white", width=20, command=self._toggle_light)
        self.light_toggle.pack(pady=5)
        bright_frame = tk.Frame(self.light_frame, bg="#0f3460")
        bright_frame.pack(fill="x", pady=3)
        tk.Label(bright_frame, text="亮度:", font=("微软雅黑", 10), fg="#aaa", bg="#0f3460").pack(side="left")
        self.bright_scale = tk.Scale(bright_frame, from_=10, to_=100, orient="horizontal",
                                     bg="#0f3460", fg="#eee", highlightthickness=0,
                                     command=self._on_brightness_change)
        self.bright_scale.set(80)
        self.bright_scale.pack(side="right", fill="x", expand=True)

        ttk.Separator(right).pack(fill="x", padx=15, pady=10)

        # 日志
        tk.Label(right, text="控制日志", font=("微软雅黑", 12, "bold"),
                 fg="#e94560", bg="#16213e").pack(pady=(0, 5))
        self.log_text = tk.Text(right, height=8, font=("Consolas", 9), bg="#1a1a2e", fg="#aaa",
                                state="disabled", relief="flat")
        self.log_text.pack(fill="x", padx=15, pady=(0, 10))

    def _make_sensor_card(self, parent, label, value, color, col):
        card = tk.Frame(parent, bg="#0f3460", padx=10, pady=8)
        card.pack(side="left", fill="x", expand=True, padx=3)
        tk.Label(card, text=label, font=("微软雅黑", 10), fg="#aaa", bg="#0f3460").pack()
        lbl = tk.Label(card, text=value, font=("微软雅黑", 16, "bold"), fg=color, bg="#0f3460",
                       name="sensor_%d" % col)
        lbl.pack()
        return card

    def _update_sensors(self):
        # 模拟传感器数据波动
        self.temperature += random.uniform(-0.3, 0.3)
        self.temperature = max(18.0, min(38.0, self.temperature))
        self.humidity += random.uniform(-1.0, 1.0)
        self.humidity = max(20.0, min(95.0, self.humidity))
        self.light += random.randint(-20, 20)
        self.light = max(0, min(1000, self.light))
        self.pm25 += random.randint(-3, 3)
        self.pm25 = max(0, min(200, self.pm25))

        # 自动控制逻辑
        if self.auto_mode:
            if self.ac_on:
                if self.ac_mode == "制冷" and self.temperature <= self.ac_target:
                    self.ac_on = False
                    self._log("自动: 温度达标，关闭空调")
                elif self.ac_mode == "制热" and self.temperature >= self.ac_target:
                    self.ac_on = False
                    self._log("自动: 温度达标，关闭空调")
            else:
                if self.ac_mode == "制冷" and self.temperature > self.ac_target + 2:
                    self.ac_on = True
                    self._log("自动: 温度过高，开启制冷")
                elif self.ac_mode == "制热" and self.temperature < self.ac_target - 2:
                    self.ac_on = True
                    self._log("自动: 温度过低，开启制热")
            if self.light and self.light < 100:
                self.light_on = True
                self._log("自动: 光照不足，开启灯光")

        # 更新界面
        cards = self.root.winfo_children()
        for child in self.root.winfo_children():
            if isinstance(child, tk.Frame):
                for sub in child.winfo_children():
                    if isinstance(sub, tk.Frame):
                        for item in sub.winfo_children():
                            if isinstance(item, tk.Frame):
                                self._update_card_value(item)

        # 更新历史
        self.temp_history.append(self.temperature)
        self.humid_history.append(self.humidity)
        if len(self.temp_history) > 30:
            self.temp_history = self.temp_history[-30:]
        if len(self.humid_history) > 30:
            self.humid_history = self.humid_history[-30:]

    def _update_card_value(self, card):
        for child in card.winfo_children():
            if isinstance(child, tk.Label):
                txt = child.cget("text")
                if "°C" in txt:
                    child.configure(text="%.1f°C" % self.temperature)
                elif "%" in txt and "lux" not in txt and "μg" not in txt:
                    child.configure(text="%.1f%%" % self.humidity)
                elif "lux" in txt:
                    child.configure(text="%d lux" % self.light)
                elif "μg" in txt:
                    child.configure(text="%d μg/m³" % self.pm25)

    def _draw_chart(self):
        try:
            c = self.chart_canvas
            c.update_idletasks()
            w = c.winfo_width()
            h = c.winfo_height()
            if w < 50:
                self.root.after(200, self._draw_chart)
                return
            c.delete("all")
            # 绘制温度曲线
            max_t = max(self.temp_history) if max(self.temp_history) > 0 else 40
            min_t = min(self.temp_history) if min(self.temp_history) < max_t else 0
            range_t = max_t - min_t if max_t != min_t else 1
            points_t = []
            for i, t in enumerate(self.temp_history):
                x = 40 + i * (w - 60) / 29.0
                y = 20 + (1 - (t - min_t) / range_t) * (h - 50)
                points_t.append((x, y))
            for i in range(len(points_t) - 1):
                c.create_line(points_t[i][0], points_t[i][1], points_t[i + 1][0], points_t[i + 1][1],
                              fill="#e94560", width=2)
            # 绘制湿度曲线
            max_h = max(self.humid_history) if max(self.humid_history) > 0 else 100
            min_h = min(self.humid_history) if min(self.humid_history) < max_h else 0
            range_h = max_h - min_h if max_h != min_h else 1
            points_h = []
            for i, h_val in enumerate(self.humid_history):
                x = 40 + i * (w - 60) / 29.0
                y = 20 + (1 - (h_val - min_h) / range_h) * (h - 50)
                points_h.append((x, y))
            for i in range(len(points_h) - 1):
                c.create_line(points_h[i][0], points_h[i][1], points_h[i + 1][0], points_h[i + 1][1],
                              fill="#4ecdc4", width=2)
            # 图例
            c.create_text(w - 80, 15, text="━ 温度", fill="#e94560", font=("微软雅黑", 9))
            c.create_text(w - 20, 15, text="━ 湿度", fill="#4ecdc4", font=("微软雅黑", 9))
            # Y轴标签
            c.create_text(15, 20, text="%.0f°" % max_t, fill="#aaa", font=("微软雅黑", 8))
            c.create_text(15, h - 25, text="%.0f°" % min_t, fill="#aaa", font=("微软雅黑", 8))
        except Exception:
            pass
        self.root.after(1000, self._draw_chart)

    def _toggle_ac(self):
        self.ac_on = not self.ac_on
        if self.ac_on:
            self.ac_status.configure(text="状态: 运行中 (%s %d°C)" % (self.ac_mode_var.get(), self.ac_target), fg="#4ecdc4")
            self.ac_toggle.configure(text="关闭空调", bg="#e94560")
            self._log("手动开启空调: %s %d°C" % (self.ac_mode_var.get(), self.ac_target))
        else:
            self.ac_status.configure(text="状态: 关闭", fg="#aaa")
            self.ac_toggle.configure(text="开启空调", bg="#2d6a4f")
            self._log("手动关闭空调")
        self._send_control("ac", "on" if self.ac_on else "off")

    def _toggle_light(self):
        self.light_on = not self.light_on
        if self.light_on:
            self.light_status.configure(text="状态: 开启 (%d%%)" % self.light_brightness, fg="#ffd700")
            self.light_toggle.configure(text="关闭灯光", bg="#e94560")
            self._log("手动开启灯光: %d%%" % self.light_brightness)
        else:
            self.light_status.configure(text="状态: 关闭", fg="#aaa")
            self.light_toggle.configure(text="开启灯光", bg="#2d6a4f")
            self._log("手动关闭灯光")
        self._send_control("light", "on" if self.light_on else "off")

    def _toggle_auto(self):
        self.auto_mode = not self.auto_mode
        if self.auto_mode:
            self.auto_btn.configure(text="自动模式: 开", bg="#2d6a4f")
            self._log("切换到自动模式")
        else:
            self.auto_btn.configure(text="自动模式: 关", bg="#e94560")
            self._log("切换到手动模式")

    def _on_mode_change(self):
        self.ac_mode = self.ac_mode_var.get()
        if self.ac_on:
            self.ac_status.configure(text="状态: 运行中 (%s %d°C)" % (self.ac_mode, self.ac_target))
            self._log("空调模式切换: %s" % self.ac_mode)

    def _on_temp_change(self, val):
        self.ac_target = int(val)
        if self.ac_on:
            self.ac_status.configure(text="状态: 运行中 (%s %d°C)" % (self.ac_mode, self.ac_target))

    def _on_brightness_change(self, val):
        self.light_brightness = int(val)
        if self.light_on:
            self.light_status.configure(text="状态: 开启 (%d%%)" % self.light_brightness)

    def _log(self, msg):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        line = "[%s] %s" % (ts, msg)
        self.log_text.configure(state="normal")
        self.log_text.insert("1.0", line + "\n")
        lines = int(self.log_text.index("end-1c").split(".")[0])
        if lines > 50:
            self.log_text.delete("1.0", "%d.0" % (lines - 50))
        self.log_text.configure(state="disabled")

    def _send_control(self, device, action):
        def _do():
            try:
                data = json.dumps({
                    "device": device, "action": action,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }).encode("utf-8")
                req = urllib.request.Request(
                    "%s/v4/datas" % API_URL,
                    data=data,
                    headers={"Content-Type": "application/json", "Authorization": "Bearer %s" % API_TOKEN}
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _upload_sensor_data(self):
        def _do():
            try:
                data = json.dumps({
                    "temperature": round(self.temperature, 1),
                    "humidity": round(self.humidity, 1),
                    "light": self.light,
                    "pm25": self.pm25,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }).encode("utf-8")
                req = urllib.request.Request(
                    "%s/v4/datas" % API_URL,
                    data=data,
                    headers={"Content-Type": "application/json", "Authorization": "Bearer %s" % API_TOKEN}
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _start_sensor_loop(self):
        def _loop():
            while True:
                self.root.after(0, self._update_sensors)
                self.root.after(0, self._upload_sensor_data)
                time.sleep(2)
        t = threading.Thread(target=_loop, daemon=True)
        t.start()

    def _update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.configure(text=now)
        self.root.after(1000, self._update_clock)


if __name__ == "__main__":
    root = tk.Tk()
    app = IndoorEnvApp(root)
    root.mainloop()