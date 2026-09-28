# -*- coding: utf-8 -*-
"""套10 2-7 商品管理功能 - Python 3.6 兼容
任务要求：
- UHF超高频读写器
- 商品入库(RFID+名称+价格)
- 查询(名称+时间段)
- 重复RFID红色提示+报警灯
- 持久化保存+倒序展示
"""
import os, sys, time, json, random, threading
try:
    import requests
except ImportError:
    requests = None
try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

CLOUD_BASE = "http://api.nlecloud.com"
CLOUD_USER = "13329262958"
CLOUD_PASS = "qwe123456789"
DATA_FILE = "products.json"

class CloudClient:
    def __init__(self):
        self.token = ""
    def login(self):
        if not requests: return False
        try:
            r = requests.post("%s/Users/Login" % CLOUD_BASE,
                json={"Account": CLOUD_USER, "Password": CLOUD_PASS, "IsRememberMe": True}, timeout=5)
            if r.json()["Status"] == 0:
                self.token = r.json()["ResultObj"]["AccessToken"]; return True
        except: pass
        return False
    def send_command(self, device_id, api_tag, value):
        if not self.token or not requests: return
        try:
            requests.post("%s/Cmds" % CLOUD_BASE, headers={"AccessToken": self.token},
                params={"deviceId": device_id, "apiTag": api_tag}, json=value, timeout=5)
        except: pass

class ProductManager:
    def __init__(self):
        self.cloud = CloudClient()
        self.products = []  # [{rfid, name, price, time}]
        self.running = False; self.root = None
        self.load_data()

    def load_data(self):
        if os.path.exists(DATA_FILE):
            try:
                with open(DATA_FILE, "r", encoding="utf-8") as f:
                    self.products = json.load(f)
            except: self.products = []

    def save_data(self):
        try:
            with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(self.products, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print("[ERR] save: %s" % e)

    def add_product(self, rfid, name, price):
        # 检查重复RFID
        for p in self.products:
            if p["rfid"] == rfid:
                self.cloud.send_command(1, "m_multi_red", {"value": "1"})
                time.sleep(1)
                self.cloud.send_command(1, "m_multi_red", {"value": "0"})
                return False, "RFID已存在"
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.products.append({"rfid": rfid, "name": name, "price": price, "time": now})
        self.save_data()
        return True, "入库成功"

    def query_products(self, name_filter="", date_start="", date_end=""):
        result = []
        for p in self.products:
            if name_filter and name_filter not in p["name"]:
                continue
            if date_start and p["time"] < date_start:
                continue
            if date_end and p["time"] > date_end:
                continue
            result.append(p)
        return list(reversed(result))

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("商品管理功能"); self.root.geometry("700x550")
        tk.Label(self.root, text="商品管理系统", font=("微软雅黑", 16, "bold")).pack(pady=10)
        # 入库
        ef = tk.Frame(self.root, bd=1, relief=tk.GROOVE, padx=10, pady=5)
        ef.pack(pady=5, fill=tk.X, padx=20)
        tk.Label(ef, text="商品入库", font=("微软雅黑", 11, "bold")).grid(row=0, column=0, columnspan=6)
        tk.Label(ef, text="RFID:", font=("微软雅黑", 9)).grid(row=1, column=0)
        self.rfid_entry = tk.Entry(ef, width=15); self.rfid_entry.grid(row=1, column=1, padx=3)
        tk.Label(ef, text="名称:", font=("微软雅黑", 9)).grid(row=1, column=2)
        self.name_entry = tk.Entry(ef, width=12); self.name_entry.grid(row=1, column=3, padx=3)
        tk.Label(ef, text="价格:", font=("微软雅黑", 9)).grid(row=1, column=4)
        self.price_entry = tk.Entry(ef, width=8); self.price_entry.grid(row=1, column=5, padx=3)
        tk.Button(ef, text="入库", command=self.do_add, font=("微软雅黑", 9), bg="#4CAF50", fg="white").grid(row=1, column=6, padx=5)
        # 查询
        qf = tk.Frame(self.root, bd=1, relief=tk.GROOVE, padx=10, pady=5)
        qf.pack(pady=5, fill=tk.X, padx=20)
        tk.Label(qf, text="查询", font=("微软雅黑", 11, "bold")).grid(row=0, column=0, columnspan=6)
        tk.Label(qf, text="名称:", font=("微软雅黑", 9)).grid(row=1, column=0)
        self.q_name = tk.Entry(qf, width=12); self.q_name.grid(row=1, column=1, padx=3)
        tk.Label(qf, text="起始日期:", font=("微软雅黑", 9)).grid(row=1, column=2)
        self.q_start = tk.Entry(qf, width=12); self.q_start.grid(row=1, column=3, padx=3)
        tk.Label(qf, text="结束日期:", font=("微软雅黑", 9)).grid(row=1, column=4)
        self.q_end = tk.Entry(qf, width=12); self.q_end.grid(row=1, column=5, padx=3)
        tk.Button(qf, text="查询", command=self.do_query, font=("微软雅黑", 9), bg="#2196F3", fg="white").grid(row=1, column=6, padx=5)
        # 列表
        tk.Label(self.root, text="商品列表(倒序):", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        cols_frame = tk.Frame(self.root); cols_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=3)
        headers = ("RFID", "名称", "价格", "入库时间")
        widths = (16, 12, 8, 18)
        for j, (h, w) in enumerate(zip(headers, widths)):
            tk.Label(cols_frame, text=h, font=("微软雅黑", 9, "bold"), width=w, bd=1, relief=tk.SUNKEN).grid(row=0, column=j)
        self.rows = []
        for i in range(10):
            row = [tk.Label(cols_frame, text="", font=("Consolas", 8), width=w, bd=1, relief=tk.SUNKEN) for w in widths]
            for j, lbl in enumerate(row): lbl.grid(row=i+1, column=j)
            self.rows.append(row)
        # 提示
        self.msg_label = tk.Label(self.root, text="", font=("微软雅黑", 9))
        self.msg_label.pack(pady=3)
        bf = tk.Frame(self.root); bf.pack(pady=5)
        tk.Button(bf, text="刷新", command=self.refresh_list, font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)
        tk.Button(bf, text="启动监听", command=self.start, font=("微软雅黑", 10), bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)

    def do_add(self):
        rfid = self.rfid_entry.get().strip()
        name = self.name_entry.get().strip()
        price = self.price_entry.get().strip()
        if not rfid or not name or not price:
            messagebox.showwarning("提示", "请填写完整"); return
        ok, msg = self.add_product(rfid, name, float(price))
        if ok:
            self.msg_label.config(text="入库成功", fg="green")
        else:
            self.msg_label.config(text="重复RFID！%s" % msg, fg="red")
        self.refresh_list()

    def do_query(self):
        name = self.q_name.get().strip()
        start = self.q_start.get().strip()
        end = self.q_end.get().strip()
        results = self.query_products(name, start, end)
        self.refresh_list(results)

    def refresh_list(self, data=None):
        if data is None:
            data = list(reversed(self.products))
        for i, row in enumerate(self.rows):
            if i < len(data):
                p = data[i]
                vals = [p["rfid"], p["name"], str(p["price"]), p["time"]]
                for j, lbl in enumerate(row): lbl.config(text=vals[j])
            else:
                for lbl in row: lbl.config(text="")

    def monitor_loop(self):
        while self.running:
            val = self.cloud.get_sensor_data(1, "m_rfid") if hasattr(self.cloud, 'get_sensor_data') else None
            if val:
                self.rfid_entry.delete(0, tk.END)
                self.rfid_entry.insert(0, val)
                if self.root: self.root.after(0, self.refresh_list)
            time.sleep(1)

    def start(self):
        if not self.running:
            self.running = True; self.cloud.login()
            threading.Thread(target=self.monitor_loop, daemon=True).start()

    def run(self):
        if HAS_GUI: self.build_gui(); self.root.mainloop()
        else:
            self.running = True
            while self.running:
                try:
                    cmd = input("add/query/quit: ").strip()
                    if cmd == "add":
                        r = input("RFID: "); n = input("名称: "); p = float(input("价格: "))
                        ok, msg = self.add_product(r, n, p); print(msg)
                    elif cmd == "quit": break
                except (KeyboardInterrupt, EOFError): break

if __name__ == "__main__":
    ProductManager().run()
