# -*- coding: utf-8 -*-
"""
门闸环境监控系统（第10套 模块二 2-6）
功能：
  1. TCP 模式（串口服务器 NetAssist）获取 温度/湿度/CO2/噪音 数据，每 5 秒保存一次
  2. 电动推杆演示闸门开/关（界面动画 + 控制按钮）
  3. 摄像头实时画面 + 上下左右方向控制 + 截图 + 图片列表
  4. 历史记录查询：按类型（数据/截图）、开始/结束时间筛选，按时间倒序显示

数据帧示例（按实际协议调整）：
  温度:27.5 湿度:60 CO2:500 噪音:68
运行：python gate_env.py
"""
import json
import os
import queue
import socket
import sqlite3
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

import requests
from PIL import Image, ImageTk

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "tcp": {"host": "192.168.1.10", "port": 8000},
    "camera": {
        "ip": "192.168.1.100", "port": 80, "user": "admin", "pass": "admin123",
        "snapshot_url": "http://{ip}:{port}/snapshot.jpg",
        "ptz_url": "http://{ip}:{port}/ptz_control.cgi?cmd={dir}&user={user}&pwd={pass}",
    },
    "save_interval_sec": 5,
    "shots_dir": "截图",
}

COLOR_BG = "#1e272e"
COLOR_PANEL = "#2f3640"
COLOR_TEXT = "#f5f6fa"
COLOR_GATE_OPEN = "#44bd32"
COLOR_GATE_CLOSE = "#e84118"


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


def db_path():
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "history.db")


def init_db():
    conn = sqlite3.connect(db_path())
    conn.execute(
        "CREATE TABLE IF NOT EXISTS records ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "rtype TEXT NOT NULL,"
        "rtime TEXT NOT NULL,"
        "value TEXT)"
    )
    conn.commit()
    conn.close()


class SensorReader(threading.Thread):
    """从串口服务器 TCP 读取传感器数据。"""

    def __init__(self, cfg, q):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.q = q
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
                        line, _, buf = buf.partition(b"\n")
                        line = line.strip()
                        if line:
                            self.q.put(("data", line.decode("utf-8", "ignore")))
                s.close()
            except Exception as exc:
                self.q.put(("err", str(exc)))
                time.sleep(3)


class GateApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("门闸环境监控系统")
        root.geometry("860x560")
        root.configure(bg=COLOR_BG)
        init_db()
        self.q = queue.Queue()
        self.reader = SensorReader(cfg, self.q)
        self.reader.start()

        cam = cfg["camera"]
        cam_url = "http://{ip}:{port}".format(ip=cam["ip"], port=cam["port"])
        self.snap_url = cam["snapshot_url"].format(ip=cam["ip"], port=cam["port"])
        self.ptz_url = cam["ptz_url"].format(ip=cam["ip"], port=cam["port"],
                                             user=cam["user"], pwd=cam["pass"])

        self.values = {"温度": "--", "湿度": "--", "CO2": "--", "噪音": "--"}
        self.gate_open = False
        self.last_save = 0
        self.last_shot = ""
        self.shots = []

        self._build_ui()
        self._load_shots()
        self._poll_data()
        self._refresh_camera()
        self._save_loop()

    # ---------------------------------------------------------- UI
    def _build_ui(self):
        top = tk.Frame(self.root, bg=COLOR_PANEL, padx=8, pady=6)
        top.pack(fill="x")
        tk.Label(top, text="门闸环境监控系统", fg=COLOR_TEXT, bg=COLOR_PANEL,
                 font=("Microsoft YaHei", 15, "bold")).pack(side="left", padx=10)

        self.gate_btn = tk.Button(top, text="开门", width=8, command=self._toggle_gate,
                                  bg="#44bd32", fg="white")
        self.gate_btn.pack(side="left", padx=6)

        main = tk.Frame(self.root, bg=COLOR_BG)
        main.pack(fill="both", expand=True, padx=8, pady=6)

        # 左：摄像头
        left = tk.Frame(main, bg=COLOR_PANEL, padx=6, pady=6)
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="摄像头实时画面", fg=COLOR_TEXT, bg=COLOR_PANEL).pack()
        self.cam_lbl = tk.Label(left, text="加载中...", bg="#000", fg="#888")
        self.cam_lbl.pack(fill="both", expand=True)
        ctl = tk.Frame(left, bg=COLOR_PANEL)
        ctl.pack(pady=4)
        d = {"上": "up", "下": "down", "左": "left", "右": "right"}
        for t, v in d.items():
            tk.Button(ctl, text=t, width=4,
                      command=lambda x=v: self._ptz(x)).pack(side="left", padx=3)
        tk.Button(left, text="截图", command=self._take_shot,
                  bg="#1e90ff", fg="white").pack(pady=4)

        # 中：传感器 + 闸门
        mid = tk.Frame(main, bg=COLOR_PANEL, padx=10, pady=8)
        mid.pack(side="left", fill="y")
        tk.Label(mid, text="环境数据", fg=COLOR_TEXT, bg=COLOR_PANEL,
                 font=("Microsoft YaHei", 12, "bold")).pack(pady=4)
        self.lbl_sensors = {}
        for k in ("温度", "湿度", "CO2", "噪音"):
            self.lbl_sensors[k] = tk.Label(mid, text="%s: --" % k, fg="#7bed9f",
                                           bg=COLOR_PANEL, font=("Consolas", 13))
            self.lbl_sensors[k].pack(pady=3)
        tk.Label(mid, text="闸门", fg=COLOR_TEXT, bg=COLOR_PANEL,
                 font=("Microsoft YaHei", 12, "bold")).pack(pady=(14, 4))
        self.gate_canvas = tk.Canvas(mid, width=180, height=90, bg=COLOR_PANEL,
                                     highlightthickness=0)
        self.gate_canvas.pack()
        self.gate_rect = self.gate_canvas.create_polygon(30, 20, 150, 20, 110, 70, 30, 70,
                                                         fill=COLOR_GATE_CLOSE, outline="#fff")
        self.gate_state = tk.StringVar(value="闸门：关")
        tk.Label(mid, textvariable=self.gate_state, fg=COLOR_TEXT,
                 bg=COLOR_PANEL).pack(pady=2)

        # 右：截图列表 + 历史
        right = tk.Frame(main, bg=COLOR_PANEL, padx=6, pady=6, width=230)
        right.pack(side="left", fill="y")
        tk.Label(right, text="截图片列表", fg=COLOR_TEXT, bg=COLOR_PANEL).pack()
        self.shot_list = tk.Listbox(right, height=10, bg="#1a1f24", fg=COLOR_TEXT,
                                    selectbackground="#1e90ff")
        self.shot_list.pack(fill="both", expand=True, pady=3)
        tk.Button(right, text="历史记录查询", command=self._open_history,
                  bg="#273c75", fg="white").pack(pady=4)

        self.status = tk.StringVar(value="TCP: 未连接")
        tk.Label(self.root, textvariable=self.status, fg="#7f8c8d", bg=COLOR_BG,
                 font=("Microsoft YaHei", 9)).pack(side="bottom", pady=4)

    # ---------------------------------------------------------- data
    def _poll_data(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "data":
                    self._parse_line(payload)
                elif kind == "err":
                    self.status.set("TCP: %s" % payload)
        except queue.Empty:
            pass
        for k, v in self.values.items():
            self.lbl_sensors[k].config(text="%s: %s" % (k, v))
        self.root.after(100, self._poll_data)

    def _parse_line(self, line):
        try:
            for part in line.split():
                if ":" in part:
                    k, v = part.split(":", 1)
                    if k in self.values:
                        self.values[k] = v
        except Exception:
            pass

    def _save_loop(self):
        now = time.time()
        if now - self.last_save >= self.cfg["save_interval_sec"]:
            self.last_save = now
            summary = "  ".join("%s:%s" % (k, v) for k, v in self.values.items())
            conn = sqlite3.connect(db_path())
            conn.execute(
                "INSERT INTO records(rtype, rtime, value) VALUES(?,?,?)",
                ("数据", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), summary))
            conn.commit()
            conn.close()
        self.root.after(1000, self._save_loop)

    # ---------------------------------------------------------- gate
    def _toggle_gate(self):
        self.gate_open = not self.gate_open
        color = COLOR_GATE_OPEN if self.gate_open else COLOR_GATE_CLOSE
        self.gate_canvas.itemconfig(self.gate_rect, fill=color)
        self.gate_state.set("闸门：%s" % ("开" if self.gate_open else "关"))
        self.gate_btn.config(text="关门" if self.gate_open else "开门",

                             bg=color)
        # 电动推杆实际控制（联动控制器/串口下发指令），此处为演示动画
        # self._send_device("gate", 1 if self.gate_open else 0)

    # ---------------------------------------------------------- camera
    def _refresh_camera(self):
        try:
            r = requests.get(self.snap_url, timeout=3)
            if r.status_code == 200:
                img = Image.open(io_bytes(r.content)).convert("RGB")
                w = self.cam_lbl.winfo_width() or 420
                h = self.cam_lbl.winfo_height() or 260
                img.thumbnail((w, h))
                self.photo = ImageTk.PhotoImage(img)
                self.cam_lbl.config(image=self.photo, text="")
        except Exception:
            pass
        self.root.after(500, self._refresh_camera)

    def _ptz(self, direction):
        try:
            requests.get(self.ptz_url.format(dir=direction), timeout=3)
        except Exception:
            pass

    def _take_shot(self):
        try:
            r = requests.get(self.snap_url, timeout=3)
            if r.status_code != 200:
                return
            d = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                             self.cfg["shots_dir"])
            os.makedirs(d, exist_ok=True)
            fn = os.path.join(d, datetime.now().strftime("%Y%m%d_%H%M%S") + ".jpg")
            with open(fn, "wb") as f:
                f.write(r.content)
            conn = sqlite3.connect(db_path())
            conn.execute(
                "INSERT INTO records(rtype, rtime, value) VALUES(?,?,?)",
                ("截图", datetime.now().strftime("%Y-%m-%d %H:%M:%S"), fn))
            conn.commit()
            conn.close()
            self._load_shots()
        except Exception:
            pass

    def _load_shots(self):
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            self.cfg["shots_dir"])
        self.shot_list.delete(0, "end")
        if os.path.isdir(base):
            for fn in sorted(os.listdir(base), reverse=True):
                self.shot_list.insert("end", fn)

    # ---------------------------------------------------------- history
    def _open_history(self):
        win = tk.Toplevel(self.root)
        win.title("历史记录查询")
        win.geometry("620x420")
        win.configure(bg=COLOR_BG)
        frm = tk.Frame(win, bg=COLOR_BG)
        frm.pack(pady=6)
        tk.Label(frm, text="类型", fg=COLOR_TEXT, bg=COLOR_BG).grid(row=0, column=0)
        self.h_type = ttk.Combobox(frm, values=["全部", "数据", "截图"], width=6)
        self.h_type.current(0)
        self.h_type.grid(row=0, column=1, padx=6)
        tk.Label(frm, text="开始", fg=COLOR_TEXT, bg=COLOR_BG).grid(row=0, column=2)
        self.h_start = tk.Entry(frm, width=18)
        self.h_start.grid(row=0, column=3, padx=6)
        self.h_start.insert(0, "2026-01-01 00:00:00")
        tk.Label(frm, text="结束", fg=COLOR_TEXT, bg=COLOR_BG).grid(row=0, column=4)
        self.h_end = tk.Entry(frm, width=18)
        self.h_end.grid(row=0, column=5, padx=6)
        self.h_end.insert(0, "2027-12-31 23:59:59")
        tk.Button(frm, text="查询", command=self._do_query,
                  bg="#1e90ff", fg="white").grid(row=0, column=6, padx=8)

        cols = ("时间", "类型", "内容")
        self.tree = ttk.Treeview(win, columns=cols, show="headings", height=18)
        for c, w in zip(cols, (150, 60, 380)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)

    def _do_query(self):
        rtype = self.h_type.get()
        start = self.h_start.get().strip()
        end = self.h_end.get().strip()
        sql = "SELECT rtime, rtype, value FROM records WHERE 1=1"
        params = []
        if rtype != "全部":
            sql += " AND rtype=?"
            params.append(rtype)
        if start:
            sql += " AND rtime>=?"
            params.append(start)
        if end:
            sql += " AND rtime<=?"
            params.append(end)
        sql += " ORDER BY rtime DESC"
        conn = sqlite3.connect(db_path())
        rows = conn.execute(sql, params).fetchall()
        conn.close()
        self.tree.delete(*self.tree.get_children())
        for rtime, rtype_, value in rows:
            self.tree.insert("", "end", values=(rtime, rtype_, value))


def io_bytes(data):
    import io
    return io.BytesIO(data)


def main():
    cfg = load_config()
    root = tk.Tk()
    GateApp(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()