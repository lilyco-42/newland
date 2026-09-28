# -*- coding: utf-8 -*-
"""套6 2-6 监控管理系统 - Python 3.6 兼容
任务要求：
- 摄像头实时画面显示
- 4方向云台控制（上/下/左/右）
- 打开/停止监控
"""
import os, sys, time, threading
try:
    import tkinter as tk
    from PIL import Image, ImageTk
    HAS_GUI = True
except ImportError:
    HAS_GUI = False

class SurveillanceSystem:
    """监控管理系统"""
    def __init__(self):
        self.running = False
        self.root = None
        self.cap = None

    def build_gui(self):
        self.root = tk.Tk()
        self.root.title("监控管理系统")
        self.root.geometry("700x550")
        tk.Label(self.root, text="监控管理系统", font=("微软雅黑", 16, "bold")).pack(pady=10)
        # 视频画面区
        self.video_label = tk.Label(self.root, text="[监控画面]", bg="black", fg="white",
                                     font=("微软雅黑", 14), width=50, height=15)
        self.video_label.pack(pady=10)
        # 云台控制
        ctrl = tk.Frame(self.root)
        ctrl.pack(pady=5)
        tk.Button(ctrl, text="▲ 上", command=lambda: self.ptz("up"),
                  font=("微软雅黑", 10), width=6).grid(row=0, column=1, padx=3)
        tk.Button(ctrl, text="◀ 左", command=lambda: self.ptz("left"),
                  font=("微软雅黑", 10), width=6).grid(row=1, column=0, padx=3)
        tk.Button(ctrl, text="■ 停", command=lambda: self.ptz("stop"),
                  font=("微软雅黑", 10), width=6).grid(row=1, column=1, padx=3)
        tk.Button(ctrl, text="▶ 右", command=lambda: self.ptz("right"),
                  font=("微软雅黑", 10), width=6).grid(row=1, column=2, padx=3)
        tk.Button(ctrl, text="▼ 下", command=lambda: self.ptz("down"),
                  font=("微软雅黑", 10), width=6).grid(row=2, column=1, padx=3)
        # 按钮
        btn = tk.Frame(self.root)
        btn.pack(pady=10)
        tk.Button(btn, text="开启监控", command=self.start_monitor,
                  font=("微软雅黑", 10), bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(btn, text="停止监控", command=self.stop_monitor,
                  font=("微软雅黑", 10), bg="#f44336", fg="white").pack(side=tk.LEFT, padx=5)

    def ptz(self, direction):
        print("[PTZ] %s" % direction)

    def start_monitor(self):
        if not self.running:
            self.running = True
            try:
                import cv2
                self.cap = cv2.VideoCapture(0)
                threading.Thread(target=self.capture_loop, daemon=True).start()
            except:
                self.video_label.config(text="摄像头未连接\n(监控画面)")

    def capture_loop(self):
        import cv2
        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if ret:
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                img = Image.fromarray(frame)
                img = img.resize((500, 350))
                imgtk = ImageTk.PhotoImage(image=img)
                self.video_label.config(image=imgtk, text="")
                self.video_label.image = imgtk
            time.sleep(0.03)

    def stop_monitor(self):
        self.running = False
        if self.cap:
            self.cap.release()
            self.cap = None
        if self.video_label:
            self.video_label.config(image="", text="[监控画面]")

    def run(self):
        if HAS_GUI:
            self.build_gui()
            self.root.mainloop()
        else:
            print("监控管理系统（命令行模式）")

if __name__ == "__main__":
    SurveillanceSystem().run()
