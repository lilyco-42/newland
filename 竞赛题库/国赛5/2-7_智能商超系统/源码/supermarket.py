# -*- coding: utf-8 -*-
"""
智能商超系统

功能:
  1. 使用超高频RFID设备, 读取三个超高频标签(客人A、B、C)的消费情况。
  2. 存储客人"超高频标签卡号、姓名、消费额"。
  3. 随意读取任意一张超高频标签, 将该客人的消费额显示在界面上,
     并利用TTS语音播报功能播报金额。

使用说明:
  - 默认使用模拟RFID模块方便演示, 接入真实读卡器时实现 RFIDReader 接口。
  - TTS 语音播报: 优先使用 pyttsx3, 其次调用 Windows SAPI。

运行: python supermarket.py
"""
import json
import os
import sys
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox

APP_NAME = "智能商超系统"

if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "customer_data.json")

DEFAULT_CUSTOMERS = [
    {"tag": "E280116060000209A000000001", "name": "客人A", "amount": 24},
    {"tag": "E280116060000209A000000002", "name": "客人B", "amount": 30},
    {"tag": "E280116060000209A000000003", "name": "客人C", "amount": 27},
]


# ------------------------------------------------------------------ #
# TTS 语音播报
# ------------------------------------------------------------------ #
class TTSPlayer(object):
    def __init__(self):
        self.engine = None
        self._init_engine()

    def _init_engine(self):
        try:
            import pyttsx3
            self.engine = pyttsx3.init()
            self.engine.setProperty("rate", 160)
            self.engine.setProperty("volume", 1.0)
        except Exception:
            self.engine = None

    def speak(self, text):
        try:
            if self.engine is not None:
                self.engine.say(text)
                self.engine.runAndWait()
                return True
            import win32com.client
            sp = win32com.client.Dispatch("SAPI.SpVoice")
            sp.Speak(text)
            return True
        except Exception:
            return False


# ------------------------------------------------------------------ #
# 客户数据
# ------------------------------------------------------------------ #
class CustomerStore(object):
    def __init__(self, path=DATA_FILE):
        self.path = path
        self.customers = {}
        self._load()
        self._seed_defaults()

    def _load(self):
        try:
            if os.path.exists(self.path):
                with open(self.path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if isinstance(data, list):
                    self.customers = {r["tag"]: r for r in data if "tag" in r}
                elif isinstance(data, dict):
                    self.customers = data
        except Exception:
            pass

    def _seed_defaults(self):
        changed = False
        for row in DEFAULT_CUSTOMERS:
            if row["tag"] not in self.customers:
                self.customers[row["tag"]] = dict(row)
                changed = True
        if changed:
            self.save()

    def save(self):
        try:
            with open(self.path, "w", encoding="utf-8") as f:
                json.dump(list(self.customers.values()), f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get(self, tag):
        return self.customers.get(tag)

    def all_customers(self):
        return list(self.customers.values())


# ------------------------------------------------------------------ #
# RFID 读取器
# ------------------------------------------------------------------ #
class SimulatedRFID(object):
    """模拟RFID: 循环轮询各客户标签。"""

    def __init__(self, store):
        self.store = store
        self._idx = -1

    def read_tag(self):
        time.sleep(0.3)
        self._idx += 1
        tags = list(self.store.customers.keys())
        return tags[self._idx % len(tags)] if tags else None


class SerialRFID(object):
    """串口超高频RFID读取器。

    接入真实设备时请按厂商SDK实现 read_tag():
      - 使用 pyserial 打开串口
      - 按协议发送读取命令
      - 解析返回数据, 返回标签EPC(十六进制字符串)
    """

    def __init__(self, port="COM3", baud=115200):
        self.port = port
        self.baud = baud

    def read_tag(self):
        # import serial
        # ser = serial.Serial(self.port, self.baud, timeout=0.5)
        # cmd = bytes([0x02, 0x00, ...])  # 厂商协议帧
        # ser.write(cmd)
        # resp = ser.read(256)
        # epc = resp[4:12].hex().upper()
        # return epc
        return None


# ------------------------------------------------------------------ #
# 主程序
# ------------------------------------------------------------------ #
class SupermarketApp:
    def __init__(self, root):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("660x500")
        self.root.configure(bg="#F5F5F5")

        self.store = CustomerStore()
        self.tts = TTSPlayer()
        self.reader = SimulatedRFID(self.store)
        self.running = False
        self.last_tag = None

        self._build_ui()
        self._refresh_list()

    # ------------------------------------------------------------------ #
    # 界面
    # ------------------------------------------------------------------ #
    def _build_ui(self):
        # 标题
        tk.Label(self.root, text="智能商超系统 - 超高频RFID消费结算",
                 font=("Microsoft YaHei", 16, "bold"), bg="#4A148C",
                 fg="#FFFFFF", pady=10).pack(fill="x")

        main = tk.Frame(self.root)
        main.pack(fill="both", expand=True, padx=10, pady=6)

        # 左侧: 客户表
        left = tk.LabelFrame(main, text="客人消费信息", font=("Microsoft YaHei", 11))
        left.pack(side="left", fill="both", expand=True, padx=4)

        self.tree = ttk.Treeview(left, columns=("tag", "name", "amount"),
                                 show="headings", height=10)
        self.tree.heading("tag", text="标签卡号")
        self.tree.heading("name", text="姓名")
        self.tree.heading("amount", text="消费额(元)")
        self.tree.column("tag", width=240)
        self.tree.column("name", width=80, anchor="center")
        self.tree.column("amount", width=100, anchor="center")
        self.tree.pack(fill="both", expand=True, padx=6, pady=6)
        self.tree.tag_configure("sel", background="#E8F5E9")

        # 右侧: 读卡结果
        right = tk.Frame(main)
        right.pack(side="right", fill="y", padx=8)

        tk.Label(right, text="读取结果", font=("Microsoft YaHei", 13, "bold"),
                 fg="#4A148C").pack(pady=4)

        card = tk.Frame(right, bg="#FFFFFF", relief="ridge", bd=1)
        card.pack(fill="x", pady=6)

        def rlbl(t):
            tk.Label(card, text=t, font=("Microsoft YaHei", 12), bg="#FFFFFF", anchor="w").pack(fill="x", padx=8, pady=2)

        rlbl("标签卡号:")
        self.lb_tag = tk.Label(card, text="--", font=("Consolas", 11), fg="#1565C0", bg="#FFFFFF", anchor="w")
        self.lb_tag.pack(fill="x", padx=8)

        rlbl("姓名:")
        self.lb_name = tk.Label(card, text="--", font=("Microsoft YaHei", 16, "bold"),
                                fg="#4A148C", bg="#FFFFFF", anchor="w")
        self.lb_name.pack(fill="x", padx=8)

        rlbl("消费额:")
        self.lb_amount = tk.Label(card, text="--", font=("Microsoft YaHei", 24, "bold"),
                                  fg="#E65100", bg="#FFFFFF", anchor="w")
        self.lb_amount.pack(fill="x", padx=8)

        self.lb_hint = tk.Label(right, text="请将超高频标签靠近读卡器",
                                font=("Microsoft YaHei", 10), fg="#888")
        self.lb_hint.pack(pady=8)

        # 控制区
        ctrl = tk.Frame(self.root)
        ctrl.pack(fill="x", padx=10, pady=8)

        self.btn_start = tk.Button(ctrl, text="开始读取", bg="#4CAF50", fg="#FFFFFF",
                                   font=("Microsoft YaHei", 12, "bold"), relief=tk.FLAT,
                                   command=self.start_read)
        self.btn_start.pack(side="left", fill="x", expand=True, padx=3)

        self.btn_stop = tk.Button(ctrl, text="停止读取", bg="#F44336", fg="#FFFFFF",
                                  font=("Microsoft YaHei", 12, "bold"), relief=tk.FLAT,
                                  command=self.stop_read, state=tk.DISABLED)
        self.btn_stop.pack(side="left", fill="x", expand=True, padx=3)

        tk.Button(ctrl, text="测试语音", bg="#FF9800", fg="#FFFFFF",
                  font=("Microsoft YaHei", 12), relief=tk.FLAT,
                  command=self.test_tts).pack(side="left", fill="x", expand=True, padx=3)

        self.var_status = tk.StringVar(value="状态: 未开始读取")
        tk.Label(self.root, textvariable=self.var_status, font=("Microsoft YaHei", 10),
                 fg="#888").pack()

    def _refresh_list(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.store.all_customers():
            self.tree.insert("", tk.END, iid=row["tag"],
                             values=(row["tag"], row["name"], row["amount"]))

    # ------------------------------------------------------------------ #
    # 读取控制
    # ------------------------------------------------------------------ #
    def start_read(self):
        if self.running:
            return
        self.running = True
        self.btn_start.config(state=tk.DISABLED)
        self.btn_stop.config(state=tk.NORMAL)
        self.var_status.set("状态: 正在读取标签...")
        threading.Thread(target=self._read_loop, daemon=True).start()

    def stop_read(self):
        self.running = False
        self.btn_start.config(state=tk.NORMAL)
        self.btn_stop.config(state=tk.DISABLED)
        self.var_status.set("状态: 已停止")

    def _read_loop(self):
        while self.running:
            try:
                tag = self.reader.read_tag()
                if tag:
                    if tag != self.last_tag:
                        self.last_tag = tag
                        self.root.after(0, lambda t=tag: self._on_tag(t))
                time.sleep(0.1)
            except Exception:
                time.sleep(0.3)

    def _on_tag(self, tag):
        customer = self.store.get(tag)
        self.lb_tag.config(text=tag)
        if customer is None:
            self.lb_name.config(text="未登记客户")
            self.lb_amount.config(text="--")
            self.lb_hint.config(text="未知标签", fg="#F44336")
            self._highlight(tag, False)
            return
        amount = customer["amount"]
        self.lb_name.config(text=customer["name"])
        self.lb_amount.config(text="%.2f 元" % float(amount))
        self.lb_hint.config(text="识别成功", fg="#4CAF50")
        self._highlight(tag, True)
        # TTS 播报
        speech = "%s消费 %.2f 元" % (customer["name"], float(amount))
        threading.Thread(target=self.tts.speak, args=(speech,), daemon=True).start()

    def _highlight(self, tag, found):
        for item in self.tree.get_children():
            self.tree.item(item, tags=())
        if found:
            self.tree.item(tag, tags=("sel",))
            self.tree.selection_set(tag)
            self.tree.see(tag)

    def test_tts(self):
        threading.Thread(target=lambda: self.tts.speak("欢迎光临智能商超系统"), daemon=True).start()


def main():
    root = tk.Tk()
    try:
        app = SupermarketApp(root)
    except Exception as exc:
        messagebox.showerror(APP_NAME, "程序启动失败: %s" % exc)
        return
    root.mainloop()


if __name__ == "__main__":
    main()