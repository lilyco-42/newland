# -*- coding: utf-8 -*-
"""
大厅环境系统（第4套 模块二 2-7）
模拟大厅环境，TCP模式(串口服务器)获取 ZigBee 温湿度、烟雾(有线)、人体(有线)数据，
电动推杆模拟闸门开/关，支持手动/自动模式。

功能：
  1. 手动/自动模式切换；手动模式启用界面开关按钮，自动模式禁用并执行自动逻辑
  2. 程序运行时门为关（电动推杆向外伸长到最长）
  3. 实时获取 ZigBee 温度、湿度、烟雾、人体数据并显示
  4. 自动模式：烟警 -> 报警灯开；温度>阈值 -> 风扇开；人体感应 -> 电灯开+开门，
     否则 关灯+关门
  5. 界面电灯/风扇/报警灯带动画（红绿圆点）

数据格式（TCP 文本，按实际协议调整）：
  温度:27.5 湿度:60 烟雾:0 人体:0
运行：python hall_env.py
"""
import json
import os
import queue
import socket
import threading
import time
import tkinter as tk

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "tcp": {"host": "192.168.1.10", "port": 8000},
    "devices": {
        "fan_coil": "kk_zzdt_fan",
        "lamp": "kk_zzdt_lamp",
        "alarm": "kk_alarm",
        "door": "kk_door",
    },
    "temp_threshold": 30.0,
}

COLOR_BG = "#22303c"
COLOR_PANEL = "#2c3e50"
COLOR_TEXT = "#ecf0f1"
COLOR_ON = "#2ecc71"
COLOR_OFF = "#7f8c8d"
COLOR_ALARM = "#e74c3c"


def load_config():
    cfg = json.loads(json.dumps(DEFAULT_CONFIG))
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
            for k, v in data.items():
                cfg[k] = v
        except Exception:
            pass
    return cfg


class SensorReader(threading.Thread):
    """从串口服务器 TCP 读取传感器数据帧。"""

    def __init__(self, cfg, data_q):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.data_q = data_q
        self.running = True

    def run(self):
        while self.running:
            try:
                s = socket.create_connection(
                    (self.cfg["tcp"]["host"], self.cfg["tcp"]["port"]), timeout=5)
                s.settimeout(2)
                buf = b""
                while self.running:
                    try:
                        chunk = s.recv(1024)
                    except socket.timeout:
                        continue
                    if not chunk:
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, sep, buf = buf.partition(b"\n")
                        line = line.strip()
                        if line:
                            self.data_q.put(line.decode("utf-8", "ignore"))
                s.close()
            except Exception as exc:
                self.data_q.put(("ERR", str(exc)))
                time.sleep(3)


class HallApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("\u5927\u5385\u73af\u5883\u7cfb\u7edf")
        root.geometry("560x480")
        root.configure(bg=COLOR_BG)
        self.data_q = queue.Queue()
        self.reader = SensorReader(cfg, self.data_q)
        self.reader.start()

        self.temp = 0.0
        self.hum = 0.0
        self.smoke = 0
        self.human = 0
        self.auto_mode = tk.BooleanVar(value=True)
        self.fan = False
        self.lamp = False
        self.alarm = False
        self.door_open = False

        self._build_ui()
        self._poll_data()
        self._auto_loop()

    def _build_ui(self):
        frm = tk.Frame(self.root, bg=COLOR_PANEL, padx=10, pady=10)
        frm.pack(fill="both", expand=True, padx=10, pady=10)

        tk.Label(frm, text="\u5927\u5385\u73af\u5883\u7cfb\u7edf",
                 fg=COLOR_TEXT, bg=COLOR_PANEL, font=("Microsoft YaHei", 14, "bold")).grid(row=0, column=0, columnspan=4, pady=4)

        self.lbl_temp = self._stat_label(frm, 1, 0, "\u6e29\u5ea6")
        self.lbl_hum = self._stat_label(frm, 1, 1, "\u6e7f\u5ea6")
        self.lbl_smoke = self._stat_label(frm, 1, 2, "\u70df\u96fe")
        self.lbl_human = self._stat_label(frm, 1, 3, "\u4eba\u4f53")

        mode_frm = tk.Frame(frm, bg=COLOR_PANEL)
        mode_frm.grid(row=2, column=0, columnspan=4, pady=8)
        tk.Radiobutton(mode_frm, text="\u81ea\u52a8\u6a21\u5f0f", variable=self.auto_mode, value=True,
                       command=self._apply_mode, fg=COLOR_TEXT, bg=COLOR_PANEL,
                       selectcolor=COLOR_PANEL).pack(side="left", padx=8)
        tk.Radiobutton(mode_frm, text="\u624b\u52a8\u6a21\u5f0f", variable=self.auto_mode, value=False,
                       command=self._apply_mode, fg=COLOR_TEXT, bg=COLOR_PANEL,
                       selectcolor=COLOR_PANEL).pack(side="left", padx=8)

        self.lbl_thresh = tk.Label(frm, text="\u6e29\u5ea6\u9608\u503c", fg=COLOR_TEXT, bg=COLOR_PANEL)
        self.lbl_thresh.grid(row=3, column=0, sticky="e")
        self.ent_thresh = tk.Entry(frm, width=8)
        self.ent_thresh.insert(0, str(self.cfg["temp_threshold"]))
        self.ent_thresh.grid(row=3, column=1, sticky="w")

        self.btn_fan = self._device_button(frm, 4, 0, "\u98ce\u6247", self._toggle_fan)
        self.btn_lamp = self._device_button(frm, 4, 1, "\u7535\u706f", self._toggle_lamp)
        self.btn_alarm = self._device_button(frm, 4, 2, "\u62a5\u8b66\u706f", self._toggle_alarm)
        self.btn_door = self._device_button(frm, 4, 3, "\u95f8\u95e8", self._toggle_door)

    def _stat_label(self, frm, r, c, name):
        lbl = tk.Label(frm, text="%s: --" % name, fg=COLOR_TEXT, bg=COLOR_PANEL,
                       font=("Microsoft YaHei", 11))
        lbl.grid(row=r, column=c, padx=10, pady=4)
        return lbl

    def _device_button(self, frm, r, c, name, cmd):
        btn = tk.Button(frm, text=name, command=cmd, width=8,
                        bg="#34495e", fg=COLOR_TEXT, activebackground="#16a085")
        btn.grid(row=r, column=c, padx=8, pady=6)
        return btn

    def _apply_mode(self):
        state = "disabled" if self.auto_mode.get() else "normal"
        for b in (self.btn_fan, self.btn_lamp, self.btn_alarm, self.btn_door):
            b.config(state=state)

    def _parse_line(self, line):
        # 期望格式: 温度:27.5 湿度:60 烟雾:0 人体:0
        try:
            d = {}
            for part in line.split():
                if ":" in part:
                    k, v = part.split(":", 1)
                    d[k] = v
            if "温度" in d:
                self.temp = float(d["温度"])
            if "湿度" in d:
                self.hum = float(d["湿度"])
            if "烟雾" in d:
                self.smoke = int(float(d["烟雾"]))
            if "人体" in d:
                self.human = int(float(d["人体"]))
        except Exception:
            pass

    def _poll_data(self):
        try:
            while True:
                item = self.data_q.get_nowait()
                if isinstance(item, tuple):
                    continue
                self._parse_line(item)
        except queue.Empty:
            pass
        self.lbl_temp.config(text="温度: %.1f" % self.temp)
        self.lbl_hum.config(text="湿度: %.1f" % self.hum)
        self.lbl_smoke.config(text="烟雾: %s" % ("\u6709" if self.smoke else "\u65e0"))
        self.lbl_human.config(text="人体: %s" % ("\u6709\u4eba" if self.human else "\u65e0\u4eba"))
        self.root.after(300, self._poll_data)

    def _auto_loop(self):
        if self.auto_mode.get():
            try:
                self.cfg["temp_threshold"] = float(self.ent_thresh.get())
            except Exception:
                pass
            th = self.cfg["temp_threshold"]
            self.alarm = bool(self.smoke)
            self.fan = self.temp > th
            if self.human:
                self.lamp = True
                self.door_open = True
            else:
                self.lamp = False
                self.door_open = False
            self._refresh()
        self.root.after(1000, self._auto_loop)

    def _refresh(self):
        self.btn_fan.config(bg=COLOR_ON if self.fan else "#34495e")
        self.btn_lamp.config(bg=COLOR_ON if self.lamp else "#34495e")
        self.btn_alarm.config(bg=COLOR_ALARM if self.alarm else "#34495e")
        door_state = "\u5f00" if self.door_open else "\u5173"
        self.btn_door.config(text="\u95f8\u95e8(%s)" % door_state)

    def _toggle_fan(self):
        self.fan = not self.fan
        self._refresh()

    def _toggle_lamp(self):
        self.lamp = not self.lamp
        self._refresh()

    def _toggle_alarm(self):
        self.alarm = not self.alarm
        self._refresh()

    def _toggle_door(self):
        self.door_open = not self.door_open
        self._refresh()


def main():
    cfg = load_config()
    root = tk.Tk()
    HallApp(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()