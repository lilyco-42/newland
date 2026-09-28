# -*- coding: utf-8 -*-
"""
运输数据监控系统(窗帘控制)

功能:
  1. 点击"开始"后实时获取并显示云平台温湿度、光照值。
  2. 光照感应控制:
     - 用手遮住光照传感器(光照值低于阈值) -> 同时打开运输系统中的灯和风扇,
       风扇动画启动, 灯为点亮状态;
     - 将手拿开(光照值恢复正常) -> 关闭灯和风扇, 风扇动画停止, 灯为熄灭状态。

运行: python transport_monitor.py  (参数见同目录 config.json)
"""
import json
import math
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

import nle_cloud

APP_NAME = "窗帘控制"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, "config.json")

DEFAULT_CONFIG = {
    "server_url": "https://api.nlecloud.com",
    "username": "13329262958",
    "password": "qwe123456789",
    "mode": "cloud",
    "device_ids": [],
    "sensor_tags": {
        "temp": "m_louverbox_temp",
        "hum": "m_louverbox_hum",
        "light": "m_light",
    },
    "ctrl_tags": {
        "fan": "m_fan",
        "lamp": "m_lamp",
    },
    "interval_second": 3,
    "light_threshold": 20.0,
}


class FanCanvas(tk.Canvas):
    """风扇动画画布: 旋转的风扇叶片。"""

    def __init__(self, master, size=150, **kw):
        super(FanCanvas, self).__init__(master, width=size, height=size,
                                        bg="#FFFFFF", highlightthickness=1,
                                        highlightbackground="#CCCCCC", **kw)
        self.size = size
        self._angle = 0
        self._running = False
        self._draw_id = None
        self._draw()

    def _draw(self):
        self.delete("all")
        c = self.size // 2
        r = self.size * 0.38
        for i in range(4):
            a = self._angle + i * 90
            x1 = c + r * math.cos(math.radians(a))
            y1 = c + r * math.sin(math.radians(a))
            x2 = c + r * math.cos(math.radians(a + 30))
            y2 = c + r * math.sin(math.radians(a + 30))
            self.create_line(c, c, x1, y1, width=self.size * 0.05, fill="#2196F3",
                             capstyle=tk.ROUND)
            self.create_oval(x1 - 6, y1 - 6, x1 + 6, y1 + 6, fill="#1976D2", outline="")
            self.create_oval(x2 - 4, y2 - 4, x2 + 4, y2 + 4, fill="#64B5F6", outline="")
        self.create_oval(c - 14, c - 14, c + 14, c + 14, fill="#FF9800", outline="#E65100", width=2)
        if self._running:
            self.create_text(c, self.size - 14, text="运行中", fill="#4CAF50", font=("Microsoft YaHei", 10))

    def start(self):
        if self._running:
            return
        self._running = True
        self._tick()

    def stop(self):
        self._running = False
        if self._draw_id is not None:
            self.after_cancel(self._draw_id)
            self._draw_id = None
        self._angle = 0
        self._draw()

    def _tick(self):
        if not self._running:
            return
        self._angle = (self._angle + 12) % 360
        self._draw()
        self._draw_id = self.after(50, self._tick)


class TransportMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("560x600")
        self.root.configure(bg="#F5F5F5")
        self.root.resizable(False, False)

        if not os.path.exists(CONFIG_PATH):
            nle_cloud.save_config(CONFIG_PATH, DEFAULT_CONFIG)
        self.cfg = nle_cloud.load_config(CONFIG_PATH, DEFAULT_CONFIG)
        self.mode = self.cfg.get("mode", "cloud")
        if self.mode not in ("cloud", "demo"):
            self.mode = "cloud"

        self.client = nle_cloud.create_client(
            self.mode, self.cfg["server_url"], self.cfg["username"], self.cfg["password"]
        )
        self.logged_in = False
        self.running = False
        self.polling = False
        self.prev_light_on = None
        self.manual_on = False          # 手动控制标志

        self._build_ui()
        self._set_status("未连接", "#d9534f")
        self.root.after(300, self._auto_login)

    # ---------------- 界面 ----------------
    def _set_status(self, text, color):
        self.var_status.set(text)
        try:
            self.lb_status.config(fg=color)
        except Exception:
            pass

    def _build_ui(self):
        top = tk.Frame(self.root)
        top.pack(fill="x", padx=10, pady=(10, 4))

        tk.Label(top, text="服务器:", font=("Microsoft YaHei", 10)).pack(side="left")
        self.var_server = tk.StringVar(value=self.cfg["server_url"])
        ent_server = tk.Entry(top, textvariable=self.var_server, width=18, font=("Microsoft YaHei", 10))
        ent_server.pack(side="left", padx=(2, 8))

        tk.Label(top, text="用户名:", font=("Microsoft YaHei", 10)).pack(side="left")
        self.var_user = tk.StringVar(value=self.cfg["username"])
        tk.Entry(top, textvariable=self.var_user, width=11, font=("Microsoft YaHei", 10)).pack(side="left", padx=(2, 6))

        tk.Label(top, text="密码:", font=("Microsoft YaHei", 10)).pack(side="left")
        self.var_pwd = tk.StringVar(value=self.cfg["password"])
        tk.Entry(top, textvariable=self.var_pwd, width=11, show="*", font=("Microsoft YaHei", 10)).pack(side="left", padx=(2, 6))

        btn_login = tk.Button(top, text="登录", width=7, command=self.on_login, font=("Microsoft YaHei", 10))
        btn_login.pack(side="left", padx=4)
        btn_config = tk.Button(top, text="设置", width=7, command=self.on_settings, font=("Microsoft YaHei", 10))
        btn_config.pack(side="left", padx=4)

        tk.Label(top, text="模式:", font=("Microsoft YaHei", 10)).pack(side="left", padx=(4, 2))
        self.var_mode = tk.StringVar(value=self.mode)
        cmb_mode = ttk.Combobox(top, textvariable=self.var_mode, state="readonly", width=7,
                                values=["cloud", "demo"], font=("Microsoft YaHei", 10))
        cmb_mode.pack(side="left", padx=2)
        cmb_mode.bind("<<ComboboxSelected>>", self._on_mode_changed)

        self.var_status = tk.StringVar(value="未连接")
        self.lb_status = tk.Label(top, textvariable=self.var_status, font=("Microsoft YaHei", 10), fg="#d9534f")
        self.lb_status.pack(side="left", padx=8)

        # 标题
        tk.Label(self.root, text="运输数据监控系统",
                 font=("Microsoft YaHei", 16, "bold"), bg="#1565C0", fg="#FFFFFF",
                 pady=8).pack(fill="x")

        # 数据区
        self._data_lbs = {}
        card = tk.Frame(self.root, bd=1, relief="groove")
        card.pack(fill="x", padx=10, pady=6, ipady=6)
        self.var_temp = tk.StringVar(value="--")
        self.var_hum = tk.StringVar(value="--")
        self.var_light = tk.StringVar(value="--")
        self._make_data(card, "温度", self.var_temp, "℃", 0)
        self._make_data(card, "湿度", self.var_hum, "%RH", 1)
        self._make_data(card, "光照值", self.var_light, "lx", 2)
        self.var_update = tk.StringVar(value="采集时间: --")
        tk.Label(card, textvariable=self.var_update, font=("Microsoft YaHei", 9), fg="#888").pack()

        # 设备区
        dev = tk.Frame(self.root)
        dev.pack(fill="x", padx=10, pady=6)

        left = tk.LabelFrame(dev, text="风扇")
        left.pack(side="left", fill="x", expand=True, padx=4)
        self.fan = FanCanvas(left, size=140)
        self.fan.pack(pady=6)
        self.var_fan = tk.StringVar(value="风扇: 停止")
        tk.Label(left, textvariable=self.var_fan, font=("Microsoft YaHei", 11), fg="#9E9E9E").pack(pady=2)

        right = tk.LabelFrame(dev, text="运输灯")
        right.pack(side="right", fill="x", expand=True, padx=4)
        self.lb_lamp = tk.Label(right, text="●", font=("Arial", 64), bg="#ECECEC", fg="#9E9E9E")
        self.lb_lamp.pack(pady=8)
        self.var_lamp = tk.StringVar(value="灯: 熄灭")
        tk.Label(right, textvariable=self.var_lamp, font=("Microsoft YaHei", 11), fg="#9E9E9E").pack(pady=2)

        # 控制区
        ctrl = tk.Frame(self.root)
        ctrl.pack(fill="x", padx=10, pady=8)

        self.btn_start = tk.Button(ctrl, text="开始", bg="#4CAF50", fg="#FFFFFF",
                                   font=("Microsoft YaHei", 13, "bold"), relief=tk.FLAT,
                                   height=1, command=self.on_start)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=3)

        self.btn_stop = tk.Button(ctrl, text="停止", bg="#F44336", fg="#FFFFFF",
                                  font=("Microsoft YaHei", 13, "bold"), relief=tk.FLAT,
                                  height=1, command=self.on_stop, state=tk.DISABLED)
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=3)

        tk.Button(ctrl, text="设置", bg="#FF9800", fg="#FFFFFF",
                  font=("Microsoft YaHei", 13, "bold"), relief=tk.FLAT,
                  height=1, command=self.on_settings).pack(side="left", fill="x", expand=True, padx=3)

    def _make_data(self, parent, name, var, unit, col):
        fm = tk.Frame(parent, padx=8)
        fm.pack(side="left", fill="x", expand=True)
        tk.Label(fm, text=name, font=("Microsoft YaHei", 12)).pack()
        tk.Label(fm, textvariable=var, font=("Arial", 22, "bold"), fg="#1565C0").pack()
        tk.Label(fm, text=unit, font=("Microsoft YaHei", 10), fg="#666").pack()

    # ---------------- 登录 / 模式 ----------------
    def _auto_login(self):
        if self.mode == "demo":
            self.on_login(quiet=True)
        elif self.cfg.get("username") or self.cfg.get("password"):
            self.on_login(quiet=True)

    def _on_mode_changed(self, _event=None):
        mode = self.var_mode.get()
        if mode not in ("cloud", "demo"):
            mode = "cloud"
        self.mode = mode
        self.cfg["mode"] = mode
        nle_cloud.save_config(CONFIG_PATH, self.cfg)
        self.client = nle_cloud.create_client(
            mode,
            self.var_server.get().strip() or self.cfg["server_url"],
            self.var_user.get().strip(),
            self.var_pwd.get().strip(),
        )
        self.logged_in = False
        if mode == "demo":
            self.on_login(quiet=True)
        else:
            self._set_status("已切换为云服务系统模式", "#f0ad4e")
            if self.cfg.get("username") or self.cfg.get("password"):
                self.on_login(quiet=True)

    def on_settings(self):
        from tkinter import simpledialog
        st = self.cfg["sensor_tags"]
        for key, label in (("temp", "温度传感器标识:"), ("hum", "湿度传感器标识:"),
                           ("light", "光照传感器标识:")):
            answer = simpledialog.askstring("设置传感器标识", label,
                                            parent=self.root, initialvalue=st.get(key, ""))
            if answer:
                st[key] = answer.strip()
        ct = self.cfg["ctrl_tags"]
        for key, label in (("fan", "风扇执行器标识:"), ("lamp", "灯执行器标识:")):
            answer = simpledialog.askstring("设置执行器标识", label,
                                            parent=self.root, initialvalue=ct.get(key, ""))
            if answer:
                ct[key] = answer.strip()
        threshold = simpledialog.askfloat("设置光照阈值", "光照阈值(低于则开灯开风扇):",
                                          parent=self.root,
                                          initialvalue=float(self.cfg.get("light_threshold", 20)))
        if threshold is not None:
            self.cfg["light_threshold"] = threshold
        self.cfg["server_url"] = self.var_server.get().strip() or DEFAULT_CONFIG["server_url"]
        self.cfg["username"] = self.var_user.get().strip()
        self.cfg["password"] = self.var_pwd.get().strip()
        nle_cloud.save_config(CONFIG_PATH, self.cfg)
        messagebox.showinfo(APP_NAME, "设置已保存")

    def on_login(self, quiet=False):
        if self.mode != "demo":
            self.client.base_url = self.var_server.get().strip()
        ok, msg = self.client.login(self.var_user.get().strip(), self.var_pwd.get().strip())
        if ok:
            self.logged_in = True
            self.cfg["server_url"] = self.client.base_url
            self.cfg["username"] = self.client.username
            self.cfg["password"] = self.client.password
            nle_cloud.save_config(CONFIG_PATH, self.cfg)
            self._set_status("已连接: " + msg, "#5cb85c")
            if not quiet:
                messagebox.showinfo(APP_NAME, msg, parent=self.root)
        else:
            self.logged_in = False
            self._set_status("连接失败: " + msg, "#d9534f")
            if not quiet:
                messagebox.showerror(APP_NAME, msg, parent=self.root)

    # ---------------- 开始/停止 ----------------
    def on_start(self):
        if not self.logged_in:
            messagebox.showwarning(APP_NAME, "请先登录云服务系统", parent=self.root)
            return
        if self.running:
            return
        self.running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.prev_light_on = None
        self._set_status("采集运行中", "#5cb85c")
        if not self.polling:
            self.polling = True
            threading.Thread(target=self._poll_loop, daemon=True).start()

    def on_stop(self):
        self.running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self._set_status("已停止", "#888")
        self._set_device(False)

    def _poll_loop(self):
        while self.polling:
            if self.running:
                try:
                    self._poll_once()
                except Exception:
                    pass
            else:
                time.sleep(0.2)

    def _poll_once(self):
        st = self.cfg["sensor_tags"]
        tags = [st["temp"], st["hum"], st["light"]]
        data = self.client.fetch_sensor(tags, self.cfg.get("device_ids") or None)
        now = time.strftime("%Y-%m-%d %H:%M:%S")

        temp = data.get(st["temp"])
        hum = data.get(st["hum"])
        light = data.get(st["light"])

        if temp:
            val = nle_cloud.normalize_number(temp["value"])
            self.after_recall(lambda: self._set_value(self.var_temp, "%.1f" % val if val is not None else "--"))
        if hum:
            val = nle_cloud.normalize_number(hum["value"])
            self.after_recall(lambda: self._set_value(self.var_hum, "%.1f" % val if val is not None else "--"))
        if light:
            val = nle_cloud.normalize_number(light["value"])
            self.after_recall(lambda: self._set_value(self.var_light, "%.1f" % val if val is not None else "--"))
            self.after_recall(lambda: self.var_update.set("采集时间: " + (light["time"] or now)))

        # 光照感应控制
        if light is not None:
            light_val = nle_cloud.normalize_number(light["value"])
            threshold = float(self.cfg.get("light_threshold", 20))
            on = (light_val is not None and light_val < threshold)
            if self.prev_light_on is None or self.prev_light_on != on:
                self.prev_light_on = on
                self.after_recall(lambda: self._set_device(on))
                self._push_cmds(on)

    def after_recall(self, fn):
        try:
            self.root.after(0, fn)
        except Exception:
            pass

    def _set_value(self, var, text):
        var.set(text)

    def _set_device(self, on):
        if on:
            self.fan.start()
            self.var_fan.set("风扇: 运行中")
            self.lb_fan_color("#4CAF50")
            self.lb_lamp.config(text="💡", bg="#FFF8E1", fg="#FFC107")
            self.var_lamp.set("灯: 点亮")
            self.lb_lamp_color("#FFC107")
        else:
            self.fan.stop()
            self.var_fan.set("风扇: 停止")
            self.lb_fan_color("#9E9E9E")
            self.lb_lamp.config(text="●", bg="#ECECEC", fg="#9E9E9E")
            self.var_lamp.set("灯: 熄灭")
            self.lb_lamp_color("#9E9E9E")

    def lb_fan_color(self, color):
        for w in self.root.winfo_children():
            pass
        # 通过 group 找到风扇状态标签
        self._find_and_color("风扇", color)

    def lb_lamp_color(self, color):
        self._find_and_color("灯", color)

    def _find_and_color(self, prefix, color):
        def walk(widgets):
            for w in widgets:
                try:
                    var = getattr(w, "textvariable", None)
                    if var is not None and var.get().startswith(prefix):
                        w.config(fg=color)
                except Exception:
                    pass
                walk(w.winfo_children())
        walk(self.root.winfo_children())

    def _push_cmds(self, on):
        """下发命令到云端: 风扇和灯。"""
        if self.mode == "demo":
            return
        ct = self.cfg["ctrl_tags"]
        value = 1 if on else 0
        dev_ids = self.cfg.get("device_ids") or []
        if not dev_ids:
            try:
                dev_ids = [d.get("DeviceID") for d in self.client.query_devices()
                           if d.get("DeviceID") is not None]
            except Exception:
                return
        for tag in (ct.get("fan"), ct.get("lamp")):
            if not tag:
                continue
            for dev_id in dev_ids:
                threading.Thread(target=self._send, args=(dev_id, tag, value), daemon=True).start()

    def _send(self, dev_id, tag, value):
        try:
            self.client.send_command(dev_id, tag, value)
        except Exception:
            pass

    def _set_data_label(self, var, text, color="#1565C0"):
        var.set(text)


def main():
    root = tk.Tk()
    try:
        app = TransportMonitorApp(root)
    except Exception as exc:
        messagebox.showerror(APP_NAME, "程序启动失败: %s" % exc)
        return
    root.mainloop()


if __name__ == "__main__":
    main()