# -*- coding: utf-8 -*-
"""
商品管理系统（第10套 模块二 2-7）
功能：
  1. 录入 / 查询商品信息（名称、RFID、价格、数量），数据持久化(sqlite)，按入库时间倒序
  2. 超高频读写器读取 RFID 自动赋值到录入框
  3. 重复 RFID（已存在）→ 红色提示并阻止录入，同时点亮报警灯（经串口服务器 TCP 下发）
  4. 支撑功能：删除选中记录、一键清空报警灯

UHF 帧解析为占位实现（按实际超高频读写器协议调整）。
运行：python product_manage.py
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

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "device_tcp": {"host": "192.168.1.10", "port": 9000},
    "uhf": {"mode": "serial", "port": "COM4", "baud": 115200},
    "alarm_frame": "AA 55 01 00 00 01",
}

COLOR_BG = "#22303c"
COLOR_PANEL = "#2c3e50"
COLOR_TEXT = "#ecf0f1"
COLOR_DUP = "#e74c3c"
COLOR_OK = "#2ecc71"


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
    return os.path.join(os.path.dirname(os.path.abspath(__file__)), "products.db")


def init_db():
    conn = sqlite3.connect(db_path())
    conn.execute(
        "CREATE TABLE IF NOT EXISTS products ("
        "id INTEGER PRIMARY KEY AUTOINCREMENT,"
        "name TEXT NOT NULL,"
        "rfid TEXT NOT NULL UNIQUE,"
        "price REAL,"
        "qty INTEGER,"
        "created TEXT)")
    conn.commit()
    conn.close()


class UHFReader(threading.Thread):
    """超高频读写器读取 RFID 卡号。"""

    def __init__(self, cfg, q):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.q = q
        self.running = True

    def run(self):
        try:
            import serial
        except ImportError:
            return
        while self.running:
            try:
                ser = serial.Serial(self.cfg["uhf"]["port"],
                                    self.cfg["uhf"]["baud"], timeout=1)
                buf = b""
                while self.running:
                    chunk = ser.read(256)
                    if not chunk:
                        continue
                    buf += chunk
                    while b"\n" in buf or b"\r" in buf:
                        line, _, buf = buf.partition(b"\n")
                        line = line.rstrip(b"\r").strip()
                        if len(line) >= 12:  # EPC 通常 12 位以上十六进制
                            self.q.put(line.decode("ascii", "ignore").strip())
                ser.close()
            except Exception:
                time.sleep(3)


class ProductApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("商品管理系统")
        root.geometry("720x520")
        root.configure(bg=COLOR_BG)
        init_db()
        self.q = queue.Queue()
        self.reader = UHFReader(cfg, self.q)
        self.reader.start()

        self._build_ui()
        self._poll_uhf()
        self._refresh_list()

    # ---------------------------------------------------------- UI
    def _build_ui(self):
        frm = tk.Frame(self.root, bg=COLOR_PANEL, padx=10, pady=8)
        frm.pack(fill="x", padx=8, pady=8)
        tk.Label(frm, text="商品录入", fg=COLOR_TEXT, bg=COLOR_PANEL,
                 font=("Microsoft YaHei", 13, "bold")).grid(row=0, column=0, columnspan=6)

        entries = {}
        fields = [("名称", "name"), ("RFID", "rfid"), ("价格", "price"), ("数量", "qty")]
        for i, (label, key) in enumerate(fields):
            tk.Label(frm, text=label, fg=COLOR_TEXT, bg=COLOR_PANEL).grid(row=1, column=i * 2)
            e = tk.Entry(frm, width=12)
            e.grid(row=1, column=i * 2 + 1, padx=4)
            entries[key] = e
        self.ent = entries

        tk.Button(frm, text="读卡赋值", command=self._poll_uhf_once,
                  bg="#16a085", fg="white").grid(row=2, column=0, columnspan=2, pady=6)
        tk.Button(frm, text="添加商品", command=self._add_product,
                  bg="#1e90ff", fg="white").grid(row=2, column=2, columnspan=2)
        tk.Button(frm, text="删除选中", command=self._delete_selected,
                  bg="#e74c3c", fg="white").grid(row=2, column=4, columnspan=2)
        tk.Button(frm, text="关报警灯", command=self._alarm_off,
                  bg="#f39c12", fg="white").grid(row=3, column=0, columnspan=2, pady=4)

        self.msg = tk.Label(self.root, text="", fg=COLOR_OK, bg=COLOR_BG,
                            font=("Microsoft YaHei", 11))
        self.msg.pack()

        qfrm = tk.Frame(self.root, bg=COLOR_BG)
        qfrm.pack(pady=4)
        tk.Label(qfrm, text="查询：", fg=COLOR_TEXT, bg=COLOR_BG).pack(side="left")
        self.search = tk.Entry(qfrm, width=30)
        self.search.pack(side="left")
        self.search.bind("<Return>", lambda e: self._refresh_list())
        tk.Button(qfrm, text="搜索", command=self._refresh_list,
                  bg="#34495e", fg="white").pack(side="left", padx=6)
        tk.Button(qfrm, text="全部", command=lambda: (self.search.delete(0, "end"),
                                                     self._refresh_list()),
                  bg="#34495e", fg="white").pack(side="left")

        cols = ("RFID", "名称", "价格", "数量", "入库时间")
        self.tree = ttk.Treeview(self.root, columns=cols, show="headings", height=14)
        for c, w in zip(cols, (140, 120, 80, 70, 170)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True, padx=8, pady=6)

    # ---------------------------------------------------------- logic
    def _poll_uhf(self):
        try:
            while True:
                card = self.q.get_nowait()
                self.ent["rfid"].delete(0, "end")
                self.ent["rfid"].insert(0, card)
                self.msg.config(text="已读取 RFID：%s" % card, fg=COLOR_OK)
        except queue.Empty:
            pass
        self.root.after(150, self._poll_uhf)

    def _poll_uhf_once(self):
        try:
            card = self.q.get_nowait()
            self.ent["rfid"].delete(0, "end")
            self.ent["rfid"].insert(0, card)
        except queue.Empty:
            self.msg.config(text="暂无读卡数据，请将标签靠近读写器", fg="#f1c40f")

    def _add_product(self):
        name = self.ent["name"].get().strip()
        rfid = self.ent["rfid"].get().strip()
        price = self.ent["price"].get().strip()
        qty = self.ent["qty"].get().strip()
        if not name or not rfid:
            self.msg.config(text="名称和 RFID 不能为空", fg=COLOR_DUP)
            return
        try:
            price = float(price) if price else 0.0
            qty = int(qty) if qty else 1
        except ValueError:
            self.msg.config(text="价格/数量格式错误", fg=COLOR_DUP)
            return
        conn = sqlite3.connect(db_path())
        exists = conn.execute("SELECT name FROM products WHERE rfid=?", (rfid,)).fetchone()
        if exists:
            conn.close()
            self.msg.config(text="重复 RFID！该商品已存在（%s），已阻止录入并点亮报警灯"
                            % exists[0], fg=COLOR_DUP)
            self._alarm_on()
            self.root.after(2000, lambda: self.msg.config(text="", fg=COLOR_OK))
            return
        conn.execute(
            "INSERT INTO products(name, rfid, price, qty, created) VALUES(?,?,?,?,?)",
            (name, rfid, price, qty, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
        self.msg.config(text="商品添加成功：%s" % name, fg=COLOR_OK)
        for k in self.ent:
            self.ent[k].delete(0, "end")
        self._refresh_list()

    def _delete_selected(self):
        sel = self.tree.selection()
        if not sel:
            return
        rfid = self.tree.item(sel[0], "values")[0]
        conn = sqlite3.connect(db_path())
        conn.execute("DELETE FROM products WHERE rfid=?", (rfid,))
        conn.commit()
        conn.close()
        self._refresh_list()

    def _refresh_list(self):
        kw = self.search.get().strip()
        conn = sqlite3.connect(db_path())
        if kw:
            rows = conn.execute(
                "SELECT rfid, name, price, qty, created FROM products "
                "WHERE name LIKE ? OR rfid LIKE ? ORDER BY created DESC",
                ("%" + kw + "%", "%" + kw + "%")).fetchall()
        else:
            rows = conn.execute(
                "SELECT rfid, name, price, qty, created FROM products "
                "ORDER BY created DESC").fetchall()
        conn.close()
        self.tree.delete(*self.tree.get_children())
        for r in rows:
            self.tree.insert("", "end", values=(r[0], r[1], r[2], r[3], r[4]))

    # ---------------------------------------------------------- device
    def _send_frame(self, mode):
        """通过串口服务器 TCP 控制报警灯等设备。mode: 'on'/'off'"""
        try:
            s = socket.create_connection(
                (self.cfg["device_tcp"]["host"], self.cfg["device_tcp"]["port"]),
                timeout=3)
            frame = self.cfg["alarm_frame"] if mode == "on" else "AA 55 01 00 00 00"
            s.sendall(bytes.fromhex(frame.replace(" ", "")))
            s.close()
        except Exception:
            pass

    def _alarm_on(self):
        self._send_frame("on")

    def _alarm_off(self):
        self._send_frame("off")
        self.msg.config(text="报警灯已关闭", fg=COLOR_OK)


def main():
    cfg = load_config()
    root = tk.Tk()
    ProductApp(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()