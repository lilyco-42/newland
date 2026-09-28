# -*- coding: utf-8 -*-
"""
门禁系统（第9套 模块二 2-7）
UHF 桌面发卡器（波特率 57600）读取 RFID 卡号，控制电动推杆（闸门）与 LED 显示屏。

功能：
  1. 串口轮询 UHF 桌面发卡器，解析到 RFID 卡号后去重 1.5 秒（防重复触发）
  2. RFID1 -> 开门（推杆缩到头），界面显示开门背景，LED 屏显示"欢迎光临"
  3. RFID2 -> 关门（推杆伸出到顶），界面显示关门背景，LED 屏显示"您走好"
  4. RFID3 -> 关门背景，LED 屏显示"未注册"
  5. 接近开关/行程开关辅助：开/关门到位后停止推杆，避免频繁伸缩

说明：
  - UHF 发卡器返回帧格式按实际设备文档解析（默认按 Hex 文本帧取卡号）
  - 电动推杆控制：通过云服务/联动控制器 TCP 指令或串口继电器（见 _push_rod 的占位实现）
运行：python door_system.py
"""
import json
import os
import queue
import threading
import time
import tkinter as tk
from tkinter import font as tkfont

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json")

DEFAULT_CONFIG = {
    "serial": {"port": "COM5", "baud": 57600},
    "rfid_map": {"RFID1卡号": "open", "RFID2卡号": "close", "RFID3卡号": "unknown"},
    "led_text": {"open": "欢迎光临", "close": "您走好", "unknown": "未注册"},
}

COLOR_BG = "#2c3e50"
COLOR_TEXT = "#ecf0f1"
COLOR_OPEN = "#27ae60"
COLOR_CLOSE = "#8e44ad"
COLOR_UNREG = "#95a5a6"


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


class UHFReader(threading.Thread):
    """串口读取 UHF 桌面发卡器卡号事件。"""

    def __init__(self, cfg, q):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.q = q
        self.running = True

    def run(self):
        try:
            import serial
        except ImportError:
            self.q.put(("ERR", "未安装 pyserial：pip install pyserial"))
            return
        while self.running:
            try:
                ser = serial.Serial(self.cfg["serial"]["port"],
                                    self.cfg["serial"]["baud"], timeout=1.5)
                buf = b""
                while self.running:
                    chunk = ser.read(256)
                    if not chunk:
                        continue
                    buf += chunk
                    # 按换行切帧；帧内用 ASCII Hex 或文本取卡号
                    while b"\n" in buf or b"\r" in buf:
                        line, _sep, buf = buf.partition(b"\n")
                        line = line.rstrip(b"\r").strip()
                        if line:
                            card = self._extract_card(line)
                            if card:
                                self.q.put(("card", card))
                ser.close()
            except Exception as exc:
                self.q.put(("ERR", str(exc)))
                time.sleep(3)

    @staticmethod
    def _extract_card(line):
        """从帧中提取卡号。默认：整帧若为可打印文本则作为卡号；
        若为 Hex（如 E2003412……），取前 8 位或按设备协议解析。"""
        try:
            text = line.decode("ascii", "ignore")
        except Exception:
            return None
        text = text.strip()
        if not text:
            return None
        # Hex 帧：全部为 0-9A-F，按 4 字节卡号取前 8 个字符
        if len(text) >= 8 and all(c in "0123456789abcdefABCDEF" for c in text):
            return text[:8].upper()
        return text


class DoorApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("门禁系统")
        root.geometry("480x360")
        root.configure(bg=COLOR_BG)
        self.q = queue.Queue()
        self.reader = UHFReader(cfg, self.q)
        self.reader.start()

        self.state = "close"  # open / close / unknown
        self.last_card = ""
        self.last_time = 0
        self.rod_extended = True   # 推杆伸出=关门

        self._build_ui()
        self._poll()

    def _build_ui(self):
        self.bg = tk.Label(self.root, text="关门", font=("Microsoft YaHei", 48, "bold"),
                           fg="white", bg=COLOR_CLOSE)
        self.bg.pack(fill="both", expand=True)

        self.led = tk.StringVar(value="您走好")
        tk.Label(self.root, textvariable=self.led, font=("Microsoft YaHei", 20, "bold"),
                 fg="#ffff00", bg=COLOR_BG).pack(pady=6)

        self.card_lbl = tk.StringVar(value="等待刷卡...")
        tk.Label(self.root, textvariable=self.card_lbl, fg=COLOR_TEXT, bg=COLOR_BG,
                 font=("Microsoft YaHei", 10)).pack()

        self.rod_lbl = tk.StringVar(value="推杆：伸出（关门到位）")
        tk.Label(self.root, textvariable=self.rod_lbl, fg="#bdc3c7", bg=COLOR_BG,
                 font=("Microsoft YaHei", 9)).pack(pady=2)

        self.status = tk.StringVar(value="串口：未连接")
        tk.Label(self.root, textvariable=self.status, fg="#7f8c8d", bg=COLOR_BG,
                 font=("Microsoft YaHei", 9)).pack()

    def _set_state(self, state):
        self.state = state
        style = {
            "open": (COLOR_OPEN, "开门", "欢迎光临"),
            "close": (COLOR_CLOSE, "关门", "您走好"),
            "unknown": (COLOR_UNREG, "关门", "未注册"),
        }
        bgcolor, bg_text, led_text = style[state]
        self.bg.config(text=bg_text, bg=bgcolor)
        self.led.set(led_text)
        # 推杆控制
        if state == "open":
            self._push_rod("retract")   # 缩回=开门
        else:
            self._push_rod("extend")    # 伸出=关门
        # 行程到位反馈（实际从接近/行程开关读取；此处演示到位状态）
        self.rod_lbl.set("推杆：%s（已到位）" % ("缩回" if state == "open" else "伸出"))

    def _push_rod(self, action):
        """电动推杆控制。实际赛场通过联动控制器/云服务或串口继电器下发指令，
        此处留占位：替换为 netassist TCP 发送指令 或 serial 写控制帧。"""
        # TODO: 按实际设备协议发送控制命令
        # 例如：send_tcp("D:/... ", cmd_frame_by(action))
        pass

    def _on_card(self, card):
        now = time.time()
        if card == self.last_card and now - self.last_time < 1.5:
            return  # 防重复
        self.last_card, self.last_time = card, now
        action = self.cfg["rfid_map"].get(card, "unknown")
        self.card_lbl.set("RFID：%s → %s" % (card, {"open": "开门", "close": "关门", "unknown": "未注册"}[action]))
        self._set_state(action)

    def _poll(self):
        try:
            while True:
                kind, payload = self.q.get_nowait()
                if kind == "card":
                    self._on_card(payload)
                elif kind == "ERR":
                    self.status.set("串口：%s" % payload)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)


def main():
    cfg = load_config()
    root = tk.Tk()
    DoorApp(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()