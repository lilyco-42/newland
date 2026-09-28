# -*- coding: utf-8 -*-
"""
气象系统（第9套 模块二 2-6）
将温度、湿度、光照、CO2、噪音 5 个传感器实时监测数据以 10 秒一次的频率显示在 LED 屏幕中。
LED 屏显示内容：温度 xx，湿度 xx，光照 xx，CO2 xx，噪音 xx。

数据来源：串口服务器 TCP 模式（默认）或串口（可选）
若配置了 LED 屏串口(serial.enabled=True)，每隔 interval_sec 秒把数据帧发送到串口（协议按实际 LED 屏调整）。

运行：python weather_led.py
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
    "source": "tcp",
    "tcp": {"host": "192.168.1.10", "port": 8000},
    "serial": {"port": "", "baud": 115200, "enabled": False},
    "interval_sec": 10,
}

COLOR_BG = "#000000"
COLOR_TEXT = "#00ff00"


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
    """TCP/串口读取传感器数据。"""

    def __init__(self, cfg, q):
        super().__init__(daemon=True)
        self.cfg = cfg
        self.q = q
        self.running = True

    def run(self):
        while self.running:
            try:
                if self.cfg["source"] == "tcp":
                    self._read_tcp()
                elif self.cfg["serial"]["port"]:
                    self._read_serial()
                else:
                    time.sleep(3)
            except Exception as exc:
                self.q.put(("ERR", str(exc)))
                time.sleep(3)

    def _read_tcp(self):
        s = socket.create_connection((self.cfg["tcp"]["host"], self.cfg["tcp"]["port"]), timeout=5)
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
                    self.q.put(line.decode("utf-8", "ignore"))
        s.close()

    def _read_serial(self):
        import serial
        ser = serial.Serial(self.cfg["serial"]["port"], self.cfg["serial"]["baud"], timeout=2)
        buf = b""
        while self.running:
            chunk = ser.read(256)
            if not chunk:
                continue
            buf += chunk
            while b"\n" in buf:
                line, _, buf = buf.partition(b"\n")
                if line:
                    self.q.put(line.decode("utf-8", "ignore"))
        ser.close()


class WeatherApp:
    def __init__(self, root, cfg):
        self.root = root
        self.cfg = cfg
        root.title("\u6c14\u8c61\u7cfb\u7edf")
        root.geometry("720x260")
        root.configure(bg=COLOR_BG)
        self.q = queue.Queue()
        self.reader = SensorReader(cfg, self.q)
        self.reader.start()

        self.values = {"\u6e29\u5ea6": "--", "\u6e7f\u5ea6": "--",
                       "\u5149\u7167": "--", "CO2": "--", "\u566a\u97f3": "--"}
        self.lbl = tk.Label(root, text="", fg=COLOR_TEXT, bg=COLOR_BG,
                            font=("Consolas", 26, "bold"))
        self.lbl.pack(expand=True)
        self.status = tk.StringVar(value="TCP: \u672a\u8fde\u63a5")
        tk.Label(root, textvariable=self.status, fg="#556b2f", bg=COLOR_BG,
                 font=("Microsoft YaHei", 10)).pack()
        self._poll()
        self._refresh_display()

    def _parse_line(self, line):
        try:
            for part in line.split():
                if ":" in part:
                    k, v = part.split(":", 1)
                    if k in self.values:
                        self.values[k] = v
        except Exception:
            pass

    def _poll(self):
        try:
            while True:
                item = self.q.get_nowait()
                if isinstance(item, tuple):
                    self.status.set("TCP: %s" % item[1])
                elif isinstance(item, str):
                    self._parse_line(item)
        except queue.Empty:
            pass
        self.root.after(100, self._poll)

    def _refresh_display(self):
        text = ("\u6e29\u5ea6 %s\uff0c\u6e7f\u5ea6 %s\uff0c\u5149\u7167 %s\uff0cCO2 %s\uff0c\u566a\u97f3 %s"
                % (self.values["\u6e29\u5ea6"], self.values["\u6e7f\u5ea6"],
                   self.values["\u5149\u7167"], self.values["CO2"], self.values["\u566a\u97f3"]))
        self.lbl.config(text=text)
        self._send_to_led(text)
        self.root.after(int(self.cfg["interval_sec"] * 1000), self._refresh_display)

    def _send_to_led(self, text):
        """把数据显示到 LED 屏幕（若配置串口）。协议按实际 LED 屏调整。"""
        if not self.cfg["serial"]["enabled"]:
            return
        try:
            import serial
            ser = serial.Serial(self.cfg["serial"]["port"], self.cfg["serial"]["baud"], timeout=2)
            ser.write(text.encode("utf-8"))
            ser.close()
        except Exception:
            pass


def main():
    cfg = load_config()
    root = tk.Tk()
    WeatherApp(root, cfg)
    root.mainloop()


if __name__ == "__main__":
    main()