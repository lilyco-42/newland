# -*- coding: utf-8 -*-
"""智能停车场管理系统 - Python 3.6 兼容版"""
import tkinter as tk
from tkinter import ttk, messagebox
import time
import datetime
import json
import threading

try:
    import urllib.request
except ImportError:
    pass

# NLECloud API 配置
API_URL = "http://api.nlecloud.com"
API_TOKEN = "your_token_here"

# 停车场配置
TOTAL_SPACES = 50
FEE_FIRST_HOUR = 5.0
FEE_PER_HOUR = 3.0


class ParkingSpace:
    def __init__(self, space_id):
        self.space_id = space_id
        self.occupied = False
        self.plate = ""
        self.entry_time = None

    def entry(self, plate):
        self.occupied = True
        self.plate = plate
        self.entry_time = datetime.datetime.now()

    def exit_car(self):
        fee = self.calc_fee()
        self.occupied = False
        plate = self.plate
        self.plate = ""
        self.entry_time = None
        return plate, fee

    def calc_fee(self):
        if not self.entry_time:
            return 0.0
        now = datetime.datetime.now()
        delta = (now - self.entry_time).total_seconds() / 3600.0
        if delta <= 1:
            return FEE_FIRST_HOUR
        return FEE_FIRST_HOUR + (int(delta) - 1) * FEE_PER_HOUR


class ParkingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("智能停车场管理系统")
        self.root.geometry("1000x700")
        self.root.configure(bg="#1a1a2e")

        self.spaces = []
        for i in range(TOTAL_SPACES):
            zone = "A" if i < 25 else "B"
            num = i + 1 if i < 25 else i - 24
            sid = "%s-%02d" % (zone, num)
            self.spaces.append(ParkingSpace(sid))

        self.space_buttons = []
        self.records = []
        self._build_ui()
        self._update_clock()

    def _build_ui(self):
        # 顶部标题
        header = tk.Frame(self.root, bg="#0f3460", height=50)
        header.pack(fill="x")
        tk.Label(header, text="智能停车场管理系统", font=("微软雅黑", 20, "bold"),
                 fg="#e94560", bg="#0f3460").pack(side="left", padx=20)
        self.clock_label = tk.Label(header, text="", font=("微软雅黑", 12), fg="#aaa", bg="#0f3460")
        self.clock_label.pack(side="right", padx=20)

        # 统计栏
        stats_frame = tk.Frame(self.root, bg="#1a1a2e")
        stats_frame.pack(fill="x", padx=10, pady=5)
        self.stat_total = self._make_stat(stats_frame, "总车位", str(TOTAL_SPACES), "#aaa")
        self.stat_empty = self._make_stat(stats_frame, "空闲", str(TOTAL_SPACES), "#2d6a4f")
        self.stat_occupied = self._make_stat(stats_frame, "已占用", "0", "#e94560")
        self.stat_income = self._make_stat(stats_frame, "今日收入", "¥0.00", "#ffd700")
        self._update_stats()

        # 主体区域
        main_frame = tk.Frame(self.root, bg="#1a1a2e")
        main_frame.pack(fill="both", expand=True, padx=10, pady=5)

        # 左侧 - 车位网格
        left = tk.Frame(main_frame, bg="#16213e", bd=1, relief="solid")
        left.pack(side="left", fill="both", expand=True, padx=(0, 5))
        tk.Label(left, text="车位状态", font=("微软雅黑", 14, "bold"),
                 fg="#e94560", bg="#16213e").pack(pady=5)
        grid_frame = tk.Frame(left, bg="#16213e")
        grid_frame.pack(fill="both", expand=True, padx=10, pady=5)
        self.space_buttons = []
        for i in range(TOTAL_SPACES):
            row = i // 5
            col = i % 5
            btn = tk.Button(grid_frame, text=self.spaces[i].space_id, font=("微软雅黑", 9),
                            width=8, height=2, bg="#1b4332", fg="#95d5b2",
                            relief="flat", command=lambda idx=i: self._on_space_click(idx))
            btn.grid(row=row, column=col, padx=3, pady=3, sticky="nsew")
            self.space_buttons.append(btn)
        for c in range(5):
            grid_frame.columnconfigure(c, weight=1)

        # 右侧 - 操作面板
        right = tk.Frame(main_frame, bg="#16213e", bd=1, relief="solid", width=280)
        right.pack(side="right", fill="y", padx=(5, 0))
        right.pack_propagate(False)

        # 入场
        tk.Label(right, text="车辆入场", font=("微软雅黑", 13, "bold"),
                 fg="#e94560", bg="#16213e").pack(pady=(10, 5))
        tk.Label(right, text="车牌号:", font=("微软雅黑", 10), fg="#aaa", bg="#16213e").pack(anchor="w", padx=15)
        self.entry_plate = tk.Entry(right, font=("微软雅黑", 11), bg="#1a1a2e", fg="#eee", insertbackground="#eee")
        self.entry_plate.pack(fill="x", padx=15, pady=(0, 5))
        tk.Label(right, text="车位号:", font=("微软雅黑", 10), fg="#aaa", bg="#16213e").pack(anchor="w", padx=15)
        self.entry_space = ttk.Combobox(right, font=("微软雅黑", 10), state="readonly")
        self.entry_space.pack(fill="x", padx=15, pady=(0, 5))
        tk.Button(right, text="确认入场", font=("微软雅黑", 11, "bold"), bg="#2d6a4f", fg="white",
                  command=self._car_entry).pack(fill="x", padx=15, pady=5)

        ttk.Separator(right).pack(fill="x", padx=15, pady=10)

        # 出场
        tk.Label(right, text="车辆出场", font=("微软雅黑", 13, "bold"),
                 fg="#e94560", bg="#16213e").pack(pady=(0, 5))
        tk.Label(right, text="车牌号:", font=("微软雅黑", 10), fg="#aaa", bg="#16213e").pack(anchor="w", padx=15)
        self.exit_plate = tk.Entry(right, font=("微软雅黑", 11), bg="#1a1a2e", fg="#eee", insertbackground="#eee")
        self.exit_plate.pack(fill="x", padx=15, pady=(0, 5))
        self.fee_label = tk.Label(right, text="费用: ¥0.00", font=("微软雅黑", 14, "bold"),
                                  fg="#ffd700", bg="#0f3460", width=20, height=2)
        self.fee_label.pack(padx=15, pady=5)
        tk.Button(right, text="确认出场", font=("微软雅黑", 11, "bold"), bg="#e94560", fg="white",
                  command=self._car_exit).pack(fill="x", padx=15, pady=5)

        # 记录
        ttk.Separator(right).pack(fill="x", padx=15, pady=10)
        tk.Label(right, text="最近记录", font=("微软雅黑", 12, "bold"),
                 fg="#e94560", bg="#16213e").pack(pady=(0, 5))
        self.record_text = tk.Text(right, height=6, font=("Consolas", 9), bg="#1a1a2e", fg="#aaa",
                                   state="disabled", relief="flat")
        self.record_text.pack(fill="x", padx=15, pady=(0, 10))

    def _make_stat(self, parent, label, value, color):
        frame = tk.Frame(parent, bg="#0f3460", padx=15, pady=8)
        frame.pack(side="left", fill="x", expand=True, padx=5)
        tk.Label(frame, text=value, font=("微软雅黑", 18, "bold"), fg=color, bg="#0f3460",
                 name="val_" + label).pack()
        tk.Label(frame, text=label, font=("微软雅黑", 9), fg="#aaa", bg="#0f3460").pack()
        return frame

    def _update_stats(self):
        empty = sum(1 for s in self.spaces if not s.occupied)
        occupied = TOTAL_SPACES - empty
        for widget in self.stat_total.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("text") != "总车位":
                widget.configure(text=str(TOTAL_SPACES))
        for widget in self.stat_empty.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("text") not in ("空闲", ""):
                try: widget.configure(text=str(empty))
                except: pass
        for widget in self.stat_occupied.winfo_children():
            if isinstance(widget, tk.Label) and widget.cget("text") not in ("已占用", ""):
                try: widget.configure(text=str(occupied))
                except: pass
        self._refresh_space_list()
        self._refresh_grid()

    def _refresh_space_list(self):
        free_spaces = [s.space_id for s in self.spaces if not s.occupied]
        self.entry_space["values"] = free_spaces

    def _refresh_grid(self):
        for i, s in enumerate(self.spaces):
            btn = self.space_buttons[i]
            if s.occupied:
                btn.configure(bg="#641220", fg="#ffb3c1")
            else:
                btn.configure(bg="#1b4332", fg="#95d5b2")

    def _on_space_click(self, idx):
        s = self.spaces[idx]
        if s.occupied:
            delta = (datetime.datetime.now() - s.entry_time).total_seconds() / 3600
            info = "车位: %s\n车牌: %s\n入场: %s\n在场: %.1f小时" % (
                s.space_id, s.plate, s.entry_time.strftime("%H:%M:%S"), delta)
            messagebox.showinfo("车位详情", info)
        else:
            messagebox.showinfo("车位详情", "车位 %s 当前空闲" % s.space_id)

    def _car_entry(self):
        plate = self.entry_plate.get().strip()
        space_id = self.entry_space.get()
        if not plate:
            messagebox.showwarning("提示", "请输入车牌号")
            return
        if not space_id:
            messagebox.showwarning("提示", "请选择车位")
            return
        for s in self.spaces:
            if s.space_id == space_id:
                s.entry(plate)
                self._add_record(plate, space_id, "入场")
                self._update_stats()
                self._upload_data("entry", plate, space_id)
                self.entry_plate.delete(0, "end")
                messagebox.showinfo("成功", "车辆 %s 已停入车位 %s" % (plate, space_id))
                return

    def _car_exit(self):
        plate = self.exit_plate.get().strip()
        if not plate:
            messagebox.showwarning("提示", "请输入车牌号")
            return
        for s in self.spaces:
            if s.occupied and s.plate == plate:
                car_plate, fee = s.exit_car()
                self.fee_label.configure(text="费用: ¥%.2f" % fee)
                self._add_record(car_plate, s.space_id, "出场 %.2f元" % fee)
                self._update_stats()
                self._upload_data("exit", car_plate, s.space_id, fee)
                self.exit_plate.delete(0, "end")
                messagebox.showinfo("出场", "车牌: %s\n费用: ¥%.2f" % (car_plate, fee))
                return
        messagebox.showwarning("提示", "未找到该车牌的在场车辆")

    def _add_record(self, plate, space_id, action):
        ts = datetime.datetime.now().strftime("%H:%M:%S")
        record = "%s | %s | %s | %s" % (ts, plate, space_id, action)
        self.records.insert(0, record)
        if len(self.records) > 20:
            self.records = self.records[:20]
        self.record_text.configure(state="normal")
        self.record_text.delete("1.0", "end")
        self.record_text.insert("1.0", "\n".join(self.records))
        self.record_text.configure(state="disabled")

    def _upload_data(self, action, plate, space_id, fee=0):
        def _do():
            try:
                data = json.dumps({
                    "action": action, "plate": plate,
                    "space": space_id, "fee": fee,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                }).encode("utf-8")
                req = urllib.request.Request(
                    "%s/v4/datas" % API_URL,
                    data=data,
                    headers={"Content-Type": "application/json", "Authorization": "Bearer %s" % API_TOKEN}
                )
                urllib.request.urlopen(req, timeout=5)
            except Exception:
                pass
        threading.Thread(target=_do, daemon=True).start()

    def _update_clock(self):
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.clock_label.configure(text=now)
        self.root.after(1000, self._update_clock)


if __name__ == "__main__":
    root = tk.Tk()
    app = ParkingApp(root)
    root.mainloop()