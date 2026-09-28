# -*- coding: utf-8 -*-
"""
门禁系统功能开发（第2套 模块二 2-7）
UHF 射频读写器实时读取 RFID 卡信息（经云服务系统获取），
通过云服务系统控制多层警示灯红灯（接入联动控制器）。

功能：
  1. 红灯开关：点击界面上红灯开关，触发工位多层警示灯红灯亮/灭
     （红灯亮起时界面红灯动图 + 工位警告声）
  2. 程序启动后每次读取超高频卡：界面显示 RFID 和刷卡时间，
     同时显示刷卡人员图像（图像 5 秒后消失）
  3. 刷卡记录按读卡时间倒序展示在“刷卡记录”列表中
     （读卡时间或 RFID 变化时才新增）
  4. 导出Excel：刷卡记录按刷卡时间倒序导出（时间、卡号两列）

运行：python access_control.py
打包：pyinstaller -F -w -n 门禁系统 access_control.py
"""
import json
import os
import queue
import threading
import time
import tkinter as tk
from datetime import datetime
from tkinter import ttk

# 确保脚本所在目录在 sys.path 中（PyInstaller / 直接运行均安全）
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import nle_cloud

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "cloud": {
        "base_url": "http://192.168.0.138:8080/",
        "username": "13329262958",
        "password": "qwe123456789",
        "rfid_tag": "RFID",
        "red_light_device_id": 0,
        "red_light_tag": "kk_alarm",
        "poll_sec": 0.8,
    },
    "images_dir": "images",
    "export_dir": "导出",
}

COLOR_BG = "#1e272e"
COLOR_PANEL = "#2f3640"
COLOR_TEXT = "#f5f6fa"
COLOR_RED_ON = "#e84118"
COLOR_RED_OFF = "#576574"


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


def is_valid_card(value):
    """判断云端 RFID 值是否为有效卡号（空/0/Off 视为无卡）。"""
    if value is None:
        return False
    s = str(value).strip()
    return bool(s) and s.lower() not in ("0", "off", "none", "null")


class CloudPoller(threading.Thread):
    """轮询云服务系统获取最新 RFID 卡号。"""

    def __init__(self, cfg, client, q):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.client = client
        self.q = q
        self.running = True
        self.last = None

    def run(self):
        while self.running:
            try:
                values = self.client.fetch_sensor([self.cfg["cloud"]["rfid_tag"]])
                card = nle_cloud._get(values, self.cfg["cloud"]["rfid_tag"])
                if is_valid_card(card) and str(card) != self.last:
                    self.last = str(card)
                    self.q.put(("card", str(card),
                                datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
            except Exception as exc:
                self.q.put(("ERR", str(exc)))
            time.sleep(self.cfg["cloud"]["poll_sec"])


class AccessApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("门禁系统")
        root.geometry("760x560")
        root.configure(bg=COLOR_BG)

        c = cfg["cloud"]
        self.client = nle_cloud.create_client(
            "cloud", c["base_url"], c["username"], c["password"])
        self.client.login()

        self.q = queue.Queue()
        self.poller = CloudPoller(cfg, self.client, self.q)
        self.poller.start()

        self.red_on = False
        self.blink = False
        self.records = []        # [(time, card), ...]
        self.current_shot = None
        self._shot_after = None

        self._build_ui()
        self._poll()
        self._animate()

    # ---------------------------------------------------------- UI
    def _build_ui(self):
        top = tk.Frame(self.root, bg=COLOR_PANEL, padx=10, pady=8)
        top.pack(fill="x", padx=8, pady=8)
        tk.Label(top, text="门禁系统", fg=COLOR_TEXT, bg=COLOR_PANEL,
                 font=("Microsoft YaHei", 15, "bold")).pack(side="left", padx=10)

        self.red_cv = tk.Canvas(top, width=72, height=72, bg=COLOR_PANEL,
                                highlightthickness=0)
        self.red_cv.pack(side="left", padx=10)
        self.red_lamp = self.red_cv.create_oval(12, 12, 60, 60, fill=COLOR_RED_OFF,
                                                outline="#fff")
        self.red_btn = tk.Button(top, text="红灯开", width=8, command=self._toggle_red,
                                 bg="#e84118", fg="white")
        self.red_btn.pack(side="left", padx=10)

        row = tk.Frame(self.root, bg=COLOR_PANEL, padx=10, pady=8)
        row.pack(fill="x", padx=8)
        tk.Label(row, text="当前刷卡", fg=COLOR_TEXT, bg=COLOR_PANEL,
                 font=("Microsoft YaHei", 12)).pack(side="left", padx=4)
        self.lbl_rfid = tk.Label(row, text="--", fg="#00d8d6", bg=COLOR_PANEL,
                                 font=("Consolas", 16, "bold"))
        self.lbl_rfid.pack(side="left", padx=8)
        self.lbl_time = tk.Label(row, text="--", fg="#7f8c8d", bg=COLOR_PANEL)
        self.lbl_time.pack(side="left", padx=8)

        self.photo_lbl = tk.Label(self.root, bg="#0f1420", text="刷卡人员图像",
                                  fg="#4a5568", width=40, height=6)
        self.photo_lbl.pack(fill="x", padx=8, pady=4)

        list_frm = tk.Frame(self.root, bg=COLOR_PANEL)
        list_frm.pack(fill="both", expand=True, padx=8, pady=6)
        head = tk.Frame(list_frm, bg=COLOR_PANEL)
        head.pack(fill="x")
        tk.Label(head, text="刷卡记录", fg=COLOR_TEXT, bg=COLOR_PANEL,
                 font=("Microsoft YaHei", 11)).pack(side="left")
        tk.Button(head, text="导出Excel", command=self._export,
                  bg="#1e90ff", fg="white").pack(side="right")
        cols = ("刷卡时间", "卡号")
        self.tree = ttk.Treeview(list_frm, columns=cols, show="headings", height=12)
        for c, w in zip(cols, (170, 200)):
            self.tree.heading(c, text=c)
            self.tree.column(c, width=w)
        self.tree.pack(fill="both", expand=True)

        self.status = tk.StringVar(value="云服务：连接中...")
        tk.Label(self.root, textvariable=self.status, fg="#7f8c8d", bg=COLOR_BG,
                 font=("Microsoft YaHei", 9)).pack(side="bottom", pady=4)

    # ---------------------------------------------------------- logic
    def _toggle_red(self):
        self.red_on = not self.red_on
        self._send_red()
        self.red_btn.config(text="红灯关" if self.red_on else "红灯开")
        if self.red_on:
            self._beep()

    def _send_red(self):
        c = self.cfg["cloud"]
        try:
            self.client.send_command(c["red_light_device_id"],
                                     c["red_light_tag"], 1 if self.red_on else 0)
        except Exception as exc:
            self.status.set("云服务：%s" % exc)

    def _beep(self):
        """红灯亮起时工位发出警告声（红色警示灯自带 + 本地蜂鸣辅助）。"""
        try:
            import winsound
            for _ in range(2):
                winsound.Beep(1200, 200)
                time.sleep(0.05)
        except Exception:
            pass

    def _on_card(self, card, ts):
        self.lbl_rfid.config(text=card)
        self.lbl_time.config(text=ts)
        self.records.insert(0, (ts, card))
        self._refresh_list()
        self._show_person(card)

    def _show_person(self, card):
        base = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            self.cfg["images_dir"])
        # 优先用同名图片，否则默认图
        path = os.path.join(base, "%s.jpg" % card)
        if not os.path.exists(path):
            path = os.path.join(base, "default.jpg")
        try:
            from PIL import Image, ImageTk
            img = Image.open(path).convert("RGB")
            img.thumbnail((320, 160))
            self.photo = ImageTk.PhotoImage(img)
            self.photo_lbl.config(image=self.photo, text="")
            self.current_shot = card
        except Exception:
            self.photo_lbl.config(text="暂无人员图像", image="")
            self.current_shot = None
        # 5 秒后图像消失
        if self._shot_after:
            self.root.after_cancel(self._shot_after)
        self._shot_after = self.root.after(5000, self._hide_person)

    def _hide_person(self):
        if self.photo_lbl.cget("image"):
            self.photo_lbl.config(image="", text="刷卡人员图像")
            self.current_shot = None

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for ts, card in self.records:          # 已按时间倒序
            self.tree.insert("", "end", values=(ts, card))

    def _export(self):
        if not self.records:
            return
        d = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                         self.cfg["export_dir"])
        os.makedirs(d, exist_ok=True)
        path = os.path.join(d, "刷卡记录_%s.xlsx" % datetime.now().strftime("%Y%m%d_%H%M%S"))
        try:
            from openpyxl import Workbook
            wb = Workbook()
            ws = wb.active
            ws.title = "刷卡记录"
            ws.append(["时间", "卡号"])
            for ts, card in self.records:      # 时间倒序
                ws.append([ts, card])
            wb.save(path)
            self.status.set("已导出：%s" % path)
        except ImportError:
            import csv
            path = path.replace(".xlsx", ".csv")
            with open(path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["时间", "卡号"])
                for ts, card in self.records:
                    w.writerow([ts, card])
            self.status.set("已导出（csv）：%s" % path)

    # ---------------------------------------------------------- loop
    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if item[0] == "card":
                    self._on_card(item[1], item[2])
                elif item[0] == "ERR":
                    self.status.set("云服务：%s" % item[1])
        except queue.Empty:
            pass
        self.root.after(150, self._poll)

    def _animate(self):
        fill = COLOR_RED_ON if (self.red_on and self.blink) else COLOR_RED_OFF
        self.red_cv.itemconfig(self.red_lamp, fill=fill)
        self.blink = not self.blink
        self.root.after(400, self._animate)


def main():
    cfg = load_config()
    root = tk.Tk()
    AccessApp(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()