# -*- coding: utf-8 -*-
"""套3 2-7 RFID售票系统 - Python 3.6 兼容
任务要求：
- UHF读写器+RFID标签
- 10个4D座席（座位号1-10）
- 绑定RFID与座位号
- 退票功能
- 检票自动对号入座
- 统计已售/已就座数量
"""
import os
import sys
import time
import random
import threading
import collections

try:
    import requests
except ImportError:
    requests = None

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

try:
    import tkinter as tk
    from tkinter import messagebox, filedialog
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

CLOUD_BASE = "http://api.nlecloud.com"
CLOUD_USER = "13329262958"
CLOUD_PASS = "qwe123456789"


class CloudClient:
    def __init__(self):
        self.token = ""
    def login(self):
        if not requests: return False
        try:
            r = requests.post("%s/Users/Login" % CLOUD_BASE,
                json={"Account": CLOUD_USER, "Password": CLOUD_PASS, "IsRememberMe": True}, timeout=5)
            data = r.json()
            if data["Status"] == 0:
                self.token = data["ResultObj"]["AccessToken"]
                return True
        except: pass
        return False
    def get_sensor_data(self, device_id, api_tag):
        if not self.token or not requests: return None
        try:
            r = requests.get("%s/Devices/%s/Datas" % (CLOUD_BASE, device_id),
                headers={"AccessToken": self.token},
                params={"ApiTags": api_tag}, timeout=5)
            data = r.json()
            if data["Status"] == 0 and data["ResultObj"]:
                for item in data["ResultObj"].get("PageSet", []):
                    if item.get("ApiTag", "").lower() == api_tag.lower():
                        return item.get("Value", "")
        except: pass
        return None


class TicketSystem:
    """RFID售票系统"""
    TOTAL_SEATS = 10

    def __init__(self):
        self.cloud = CloudClient()
        self.seats = {}  # seat_no -> {"rfid": ..., "status": "sold"/"occupied"/"empty"}
        self.excel_data = []
        self.running = False
        self.root = None
        for i in range(1, self.TOTAL_SEATS + 1):
            self.seats[i] = {"rfid": "", "status": "empty"}

    def sell_ticket(self, seat_no, rfid):
        """售票绑定"""
        if seat_no < 1 or seat_no > self.TOTAL_SEATS:
            return False
        if self.seats[seat_no]["status"] != "empty":
            return False
        self.seats[seat_no]["rfid"] = rfid
        self.seats[seat_no]["status"] = "sold"
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.excel_data.append((now, "售票", seat_no, rfid))
        print("[SELL] 座位%d -> %s" % (seat_no, rfid))
        return True

    def refund_ticket(self, seat_no):
        """退票"""
        if seat_no < 1 or seat_no > self.TOTAL_SEATS:
            return False
        if self.seats[seat_no]["status"] == "empty":
            return False
        rfid = self.seats[seat_no]["rfid"]
        self.seats[seat_no] = {"rfid": "", "status": "empty"}
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        self.excel_data.append((now, "退票", seat_no, rfid))
        print("[REFUND] 座位%d" % seat_no)
        return True

    def check_ticket(self, rfid):
        """检票对号入座"""
        for seat_no, info in self.seats.items():
            if info["rfid"] == rfid and info["status"] == "sold":
                info["status"] = "occupied"
                now = time.strftime("%Y-%m-%d %H:%M:%S")
                self.excel_data.append((now, "检票入座", seat_no, rfid))
                print("[CHECK] %s -> 座位%d" % (rfid, seat_no))
                return seat_no
        return None

    def get_stats(self):
        sold = sum(1 for s in self.seats.values() if s["status"] in ("sold", "occupied"))
        occupied = sum(1 for s in self.seats.values() if s["status"] == "occupied")
        return sold, occupied, self.TOTAL_SEATS - sold

    def export_excel(self):
        if not Workbook: return
        filepath = filedialog.asksaveasfilename(
            defaultextension=".xlsx", filetypes=[("Excel", "*.xlsx")], title="导出售票记录")
        if not filepath: return
        wb = Workbook()
        ws = wb.active
        ws.title = "售票记录"
        ws.append(["时间", "操作", "座位号", "RFID"])
        for row in self.excel_data[-50:]:
            ws.append(list(row))
        wb.save(filepath)
        print("[OK] 导出 -> %s" % filepath)

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("RFID售票系统")
        self.root.geometry("700x550")

        tk.Label(self.root, text="4D动感影院售票系统",
                 font=("微软雅黑", 16, "bold")).pack(pady=10)

        # 统计
        stat_frame = tk.Frame(self.root, bd=1, relief=tk.GROOVE, padx=10, pady=5)
        stat_frame.pack(pady=5, fill=tk.X, padx=20)
        self.sold_label = tk.Label(stat_frame, text="已售: 0", font=("微软雅黑", 11))
        self.sold_label.pack(side=tk.LEFT, padx=15)
        self.occupied_label = tk.Label(stat_frame, text="已就座: 0", font=("微软雅黑", 11))
        self.occupied_label.pack(side=tk.LEFT, padx=15)
        self.empty_label = tk.Label(stat_frame, text="空闲: 10", font=("微软雅黑", 11), fg="green")
        self.empty_label.pack(side=tk.LEFT, padx=15)

        # 座位布局
        tk.Label(self.root, text="座位状态:", font=("微软雅黑", 10)).pack(anchor=tk.W, padx=20)
        seat_frame = tk.Frame(self.root)
        seat_frame.pack(pady=5, padx=20)
        self.seat_labels = {}
        for i in range(1, self.TOTAL_SEATS + 1):
            color = "gray"
            lbl = tk.Label(seat_frame, text="%d号" % i, bg=color, fg="white",
                          font=("微软雅黑", 9), width=6, height=2, relief=tk.RAISED)
            lbl.grid(row=(i-1)//5, column=(i-1)%5, padx=3, pady=3)
            self.seat_labels[i] = lbl

        # 操作区
        op_frame = tk.Frame(self.root, bd=1, relief=tk.GROOVE, padx=10, pady=5)
        op_frame.pack(pady=10, fill=tk.X, padx=20)

        # 售票
        tk.Label(op_frame, text="售票:", font=("微软雅黑", 10)).grid(row=0, column=0, sticky=tk.E)
        self.sell_seat = tk.Entry(op_frame, width=5)
        self.sell_seat.grid(row=0, column=1, padx=3)
        tk.Label(op_frame, text="RFID:", font=("微软雅黑", 10)).grid(row=0, column=2)
        self.sell_rfid = tk.Entry(op_frame, width=15)
        self.sell_rfid.grid(row=0, column=3, padx=3)
        tk.Button(op_frame, text="售票", command=self.do_sell,
                  font=("微软雅黑", 9), bg="#4CAF50", fg="white").grid(row=0, column=4, padx=5)

        # 退票
        tk.Label(op_frame, text="退票座位:", font=("微软雅黑", 10)).grid(row=1, column=0, sticky=tk.E, pady=3)
        self.refund_seat = tk.Entry(op_frame, width=5)
        self.refund_seat.grid(row=1, column=1, padx=3)
        tk.Button(op_frame, text="退票", command=self.do_refund,
                  font=("微软雅黑", 9), bg="#f44336", fg="white").grid(row=1, column=4, padx=5)

        # 检票
        tk.Label(op_frame, text="检票RFID:", font=("微软雅黑", 10)).grid(row=2, column=0, sticky=tk.E, pady=3)
        self.check_rfid = tk.Entry(op_frame, width=15)
        self.check_rfid.grid(row=2, column=1, columnspan=2, padx=3)
        tk.Button(op_frame, text="检票入座", command=self.do_check,
                  font=("微软雅黑", 9), bg="#2196F3", fg="white").grid(row=2, column=4, padx=5)

        # 按钮
        btn_frame = tk.Frame(self.root)
        btn_frame.pack(pady=5)
        tk.Button(btn_frame, text="模拟RFID读卡", command=self.simulate_read,
                  font=("微软雅黑", 10), bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="导出Excel", command=self.export_excel,
                  font=("微软雅黑", 10)).pack(side=tk.LEFT, padx=5)

    def refresh_seats(self):
        sold, occupied, empty = self.get_stats()
        self.sold_label.config(text="已售: %d" % (sold))
        self.occupied_label.config(text="已就座: %d" % occupied)
        self.empty_label.config(text="空闲: %d" % empty)
        for i in range(1, self.TOTAL_SEATS + 1):
            s = self.seats[i]["status"]
            if s == "empty":
                self.seat_labels[i].config(bg="gray", text="%d号" % i)
            elif s == "sold":
                self.seat_labels[i].config(bg="orange", text="%d已售" % i)
            elif s == "occupied":
                self.seat_labels[i].config(bg="green", text="%d已坐" % i)

    def do_sell(self):
        try:
            seat = int(self.sell_seat.get())
            rfid = self.sell_rfid.get().strip()
            if rfid and self.sell_ticket(seat, rfid):
                self.refresh_seats()
            else:
                messagebox.showwarning("提示", "售票失败")
        except: pass

    def do_refund(self):
        try:
            seat = int(self.refund_seat.get())
            if self.refund_ticket(seat):
                self.refresh_seats()
            else:
                messagebox.showwarning("提示", "退票失败")
        except: pass

    def do_check(self):
        rfid = self.check_rfid.get().strip()
        seat = self.check_ticket(rfid)
        if seat:
            self.refresh_seats()
            messagebox.showinfo("检票", "请就座%d号" % seat)
        else:
            messagebox.showwarning("提示", "未找到有效票")

    def simulate_read(self):
        rfid = "RFID_%04d" % random.randint(1000, 9999)
        self.check_rfid.delete(0, tk.END)
        self.check_rfid.insert(0, rfid)

    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            print("RFID售票系统（命令行模式）")
            while True:
                try:
                    cmd = input("sell=售票 refund=退票 check=检票: ").strip()
                    if cmd == "sell":
                        s = int(input("座位号: "))
                        r = input("RFID: ")
                        self.sell_ticket(s, r)
                    elif cmd == "refund":
                        s = int(input("座位号: "))
                        self.refund_ticket(s)
                    elif cmd == "check":
                        r = input("RFID: ")
                        self.check_ticket(r)
                except (KeyboardInterrupt, EOFError):
                    break


if __name__ == "__main__":
    app = TicketSystem()
    app.run()
