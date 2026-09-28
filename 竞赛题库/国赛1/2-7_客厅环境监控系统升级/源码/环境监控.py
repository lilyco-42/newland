# -*- coding: utf-8 -*-
"""
环境监控(客厅环境监控系统升级) 主程序
=======================================
功能:
    1. 登录云服务系统(或演示模式), 读取温湿度(四输入)/光照(zigbee)/
       人体红外(zigbee)数据并同步刷新显示。
    2. 人体红外: 有人→"有人", 否则→"无人"。
    3. 有人自动开启风扇后电视显示彩色画面; 无人时点击风扇图片
       手动关闭风扇后电视同步显示黑屏。
    4. 光照<100 显示关灯背景 u0.jpg, 否则显示开灯背景 u1.jpg。
    5. 温度>=27℃ 开启风扇, 否则关闭(温度规则最高优先)。
    6. 执行器开关图片与实训工位设备状态同步(send_command 下发)。
    7. 演示模式(mode=demo): 内置模拟温湿度/光照/人体红外, 便于无硬件验证。

运行环境: Python 3.11 + tkinter + requests + Pillow
运行方法: python room.py
"""

import os
import random
import sys
import tkinter as tk
from tkinter import ttk
from datetime import datetime

# 禁止生成 __pycache__
sys.dont_write_bytecode = True

from PIL import Image, ImageTk

import make_images
import nle_cloud
from nle_cloud import create_client, normalize_number

# 兼容 PyInstaller 打包: 资源(images)从 _MEIPASS 读, 配置(KRoom.txt)放 exe 旁边
if getattr(sys, 'frozen', False):
    HERE = os.path.dirname(sys.executable)        # exe 所在目录(可写配置)
    RES_DIR = sys._MEIPASS                        # 打包资源目录(images)
else:
    HERE = os.path.dirname(os.path.abspath(__file__))
    RES_DIR = HERE
CFG_PATH = os.path.join(HERE, "KRoom.txt")
IMG_DIR = os.path.join(RES_DIR, "images")

# ============================ 参数配置(KRoom.txt) ============================

DEFAULT_CFG = {
    "server_url": "https://api.nlecloud.com",
    "username": "13011111101",
    "password": "123456",
    "mode": "cloud",
    "tag_temp": "m_temp",
    "tag_hum": "m_hum",
    "tag_light": "m_light",
    "tag_body": "m_body",
    "tag_fan": "m_fan",
    "tag_light_on": "m_steady_white",
    "refresh_second": "3",
    "light_threshold": "100",
    "temp_threshold": "27",
}

DEFAULT_KV_TEXT = u"""\
# ===== 客厅环境监控升级 程序参数配置文件 =====
# 格式: 键 = 值, 每行一项; 以 # 开头的行是注释。
# 修改后重新启动程序生效。

# ===== 云服务系统参数 =====
server_url = https://api.nlecloud.com
username = 13011111101
password = 123456
# 运行模式: cloud=真实云服务, demo=模拟演示(无硬件验证用)
mode = cloud

# ===== 传感器标识(ApiTag) =====
tag_temp = m_temp
tag_hum = m_hum
tag_light = m_light
tag_body = m_body

# ===== 执行器标识(ApiTag) =====
tag_fan = m_fan
tag_light_on = m_steady_white

# ===== 控制参数 =====
# 数据自动刷新间隔(秒)
refresh_second = 3
# 光照阈值: 光照度小于该值判为"关灯"(显示 u0.jpg), 否则"开灯"(u1.jpg)
light_threshold = 100
# 温度阈值: 温度大于等于该值时强制开启风扇
temp_threshold = 27
"""


def parse_kv(path):
    """解析 键 = 值 配置文件, 返回 dict。"""
    cfg = {}
    with open(path, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            if "=" in line:
                key, value = line.split("=", 1)
                cfg[key.strip()] = value.strip()
    return cfg


def load_cfg():
    """读取 KRoom.txt, 缺失时用默认值并重新生成。"""
    cfg = dict(DEFAULT_CFG)
    if os.path.isfile(CFG_PATH):
        try:
            parsed = parse_kv(CFG_PATH)
            cfg.update({k: v for k, v in parsed.items() if v})
        except Exception:
            pass
    else:
        regen_cfg()
    return cfg


def regen_cfg():
    """重新生成 KRoom.txt 默认配置文件。"""
    with open(CFG_PATH, "w", encoding="utf-8") as f:
        f.write(DEFAULT_KV_TEXT)


def cfg_flt(cfg, key, default):
    try:
        return float(str(cfg.get(key, default)))
    except (TypeError, ValueError):
        return default


# ==================== 演示模式模拟客户端 ====================


class DemoClient(object):
    """演示模式模拟客户端: 温湿度/光照/人体红外 内置模拟数据。"""

    def __init__(self):
        self.tick = 0
        self.temp = 26.5
        self.hum = 60.0
        self.light = 90.0
        self.body = False

    def login(self, username=None, password=None):
        return True, "演示模式登录成功(模拟数据)"

    def fetch_sensor(self, tags, device_ids=None):
        """模拟: 温度25~28波动, 湿度55~65, 光照围绕100切换, 人体随机。"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.tick += 1
        self.temp = max(25.0, min(28.0, self.temp + random.uniform(-0.6, 0.6)))
        self.hum = max(55.0, min(65.0, self.hum + random.uniform(-1.6, 1.6)))
        self.light = max(40.0, min(170.0, self.light + random.uniform(-18, 18)))
        if self.tick % 4 == 0:  # 周期性让光照跨越阈值, 方便演示关/开灯背景切换
            self.light = random.choice([random.uniform(55, 95), random.uniform(105, 150)])
        if self.tick % 3 == 0:  # 周期性随机切换人体状态
            self.body = random.random() < 0.5
        out = {}
        for tag in tags:
            t = str(tag).lower()
            if "temp" in t:
                v = self.temp
            elif "hum" in t:
                v = self.hum
            elif "light" in t:
                v = self.light
            elif "body" in t:
                v = 1 if self.body else 0
            else:
                v = random.uniform(0, 50)
            out[tag] = {"value": round(v, 1), "time": now,
                        "device": "模拟设备", "device_id": 1}
        return out

    def query_devices(self):
        return [{"DeviceID": 1, "Name": "模拟网关", "Tag": "sim_gw"}]

    def send_command(self, device_id, api_tag, value):
        return True, "演示模式下发成功"


# ==================== 主程序 ====================

LIGHT_BG = "#eef2f6"
PANEL_BG = "#ffffff"
ACCENT = "#1f6fb2"


class RoomApp(object):
    """环境监控主界面。"""

    def __init__(self, root):
        self.root = root
        self.cfg = load_cfg()
        self.interval = int(cfg_flt(self.cfg, "refresh_second", 3))
        if self.interval < 1:
            self.interval = 1
        self.light_threshold = cfg_flt(self.cfg, "light_threshold", 100)
        self.temp_threshold = cfg_flt(self.cfg, "temp_threshold", 27)

        # 传感器/执行器 ApiTag(可从 KRoom.txt 配置)
        self.tag_temp = self.cfg.get("tag_temp", "m_temp")
        self.tag_hum = self.cfg.get("tag_hum", "m_hum")
        self.tag_light = self.cfg.get("tag_light", "m_light")
        self.tag_body = self.cfg.get("tag_body", "m_body")
        self.tag_fan = self.cfg.get("tag_fan", "m_fan")
        self.tag_light_on = self.cfg.get("tag_light_on", "m_steady_white")

        # 运行状态
        self.client = None
        self.logged = False
        self.device_id = None
        self.temp = None
        self.hum = None
        self.light = None
        self.body_on = False
        self.fan_on = False
        self.manual_off = False
        self.last_ok = False
        self._after_id = None
        self._anim_id = None
        self.angle = 0

        # 登录参数(从配置读取, 首次启动默认 demo 便于演示)
        self.mode_var = tk.StringVar(value=self.cfg.get("mode", "demo"))
        self.server_var = tk.StringVar(value=self.cfg.get("server_url", ""))
        self.user_var = tk.StringVar(value=self.cfg.get("username", ""))
        self.pass_var = tk.StringVar(value=self.cfg.get("password", ""))

        # 确保图片素材存在(make_images 自动生成)
        make_images.ensure_images()

        self._load_images()
        self._build_ui()
        self._create_client_and_login(show_error=False)
        self._refresh_now()
        self._schedule()
        self._animate()

    # ---------------------------------------------------------------- #
    # 图片加载与风扇动画帧
    # ---------------------------------------------------------------- #
    def _load_images(self):
        """加载背景/电视/风扇图片, 并预生成风扇旋转动画帧。"""
        self.WIN_W, self.WIN_H = 1280, 720
        def load(name, size=None):
            p = os.path.join(IMG_DIR, name)
            im = Image.open(p)
            if size:
                im = im.resize(size, Image.LANCZOS)
            return ImageTk.PhotoImage(im)

        # 背景图按窗口尺寸铺满
        self.bg_dark = load("u0.jpg", (self.WIN_W, self.WIN_H))
        self.bg_light = load("u1.jpg", (self.WIN_W, self.WIN_H))
        self.tv_on_img = load("tv_on.png", (260, 165))
        self.tv_off_img = load("tv_off.png", (260, 165))
        # 风扇: 5 帧动画(素材自带), 关闭时显示第 1 帧; 把白底转透明
        def load_fan(i):
            p = os.path.join(IMG_DIR, "fan_%d.png" % i)
            im = Image.open(p).convert("RGBA").resize((110, 110), Image.LANCZOS)
            data = im.getdata()
            new = []
            for r, g, b, a in data:
                # 接近白色的像素变透明
                if r > 235 and g > 235 and b > 235:
                    new.append((255, 255, 255, 0))
                else:
                    new.append((r, g, b, a))
            im.putdata(new)
            return ImageTk.PhotoImage(im)
        self.fan_frames = [load_fan(i) for i in range(1, 6)]
        self.fan_stop_img = self.fan_frames[0]
        # 底部卡片小图标
        self.card_icons = {
            "temp": load("icon_temp.png", (36, 36)),
            "hum":  load("icon_hum.png", (36, 36)),
            "body": load("icon_body.png", (36, 36)),
            "light": load("icon_light.png", (36, 36)),
        }

    # ---------------------------------------------------------------- #
    # 界面搭建
    # ---------------------------------------------------------------- #
    def _build_ui(self):
        self.root.title("环境监控")
        self.root.geometry("%dx%d" % (self.WIN_W, self.WIN_H))
        self.root.configure(bg="#000000")
        self.root.resizable(False, False)

        # 全屏 Canvas 铺满整个窗口
        self.canvas = tk.Canvas(self.root, width=self.WIN_W, height=self.WIN_H,
                                highlightthickness=0, bd=0, bg="#000000")
        self.canvas.pack(fill="both", expand=True)
        self.root.geometry("%dx%d+%d+%d" % (self.WIN_W, self.WIN_H + 40,
                                            (1920-self.WIN_W)//2,
                                            (1080-self.WIN_H)//2))
        self._scene_init()

    # ---------------------------------------------------------------- #
    # 室内场景: 全屏背景 + 电视(右侧墙) + 风扇(中间) + 右上角齿轮 + 底部4卡片
    # ---------------------------------------------------------------- #
    def _scene_init(self):
        W, H = self.WIN_W, self.WIN_H
        # 背景层
        self.bg_item = self.canvas.create_image(0, 0, anchor="nw", image=self.bg_dark)

        # 电视: 右侧墙上(素材图自带边框) — 对齐参考图电视墙位置
        tv_x0, tv_y0 = 820, 210
        self.tv_item = self.canvas.create_image(
            tv_x0, tv_y0, anchor="nw", image=self.tv_off_img)

        # 风扇: 窗户上方中间(对齐参考图位置)
        self.fan_item = self.canvas.create_image(
            656, 296, anchor="center", image=self.fan_stop_img)
        self.fan_zone = (656-60, 296-60, 656+60, 296+60)

        # 右上角齿轮设置按钮
        self.gear_cx, self.gear_cy, self.gear_r = W-55, 45, 26
        self.gear_zone = (self.gear_cx-30, self.gear_cy-30,
                          self.gear_cx+30, self.gear_cy+30)
        self.canvas.create_oval(self.gear_cx-self.gear_r, self.gear_cy-self.gear_r,
                                self.gear_cx+self.gear_r, self.gear_cy+self.gear_r,
                                fill="#ffffff", outline="#cccccc")
        # 齿轮中心圆点 + 三条线 (简化齿轮图标)
        self.canvas.create_oval(self.gear_cx-8, self.gear_cy-8,
                                self.gear_cx+8, self.gear_cy+8,
                                outline="#555555", width=3)
        self.canvas.create_line(self.gear_cx-18, self.gear_cy,
                                self.gear_cx-8, self.gear_cy, fill="#555555", width=3)
        self.canvas.create_line(self.gear_cx+8, self.gear_cy,
                                self.gear_cx+18, self.gear_cy, fill="#555555", width=3)

        # 底部 4 个圆角半透明卡片
        card_w, card_h, gap = 280, 64, 16
        total = 4*card_w + 3*gap
        x0 = (W - total) // 2
        y0 = H - card_h - 12
        cards = [
            ("temp",  "#2b8fd6", "°C"),
            ("hum",   "#3aa76d", "%rh"),
            ("body",  "#2b8fd6", ""),
            ("light", "#3aa76d", "lux"),
        ]
        self.card_rects = {}
        self.card_value_items = {}
        self.card_unit_items = {}
        self.card_icon_items = {}
        for i, (key, color, unit) in enumerate(cards):
            cx = x0 + i*(card_w+gap)
            self._round_rect_helper(cx, y0, cx+card_w, y0+card_h,
                                    radius=14, fill=color, outline="")
            # 左侧图标
            self.card_icon_items[key] = self.canvas.create_image(
                cx+32, y0+card_h//2, anchor="center",
                image=self.card_icons[key])
            # 中间大数字
            self.card_value_items[key] = self.canvas.create_text(
                cx+card_w-95, y0+card_h//2, anchor="e", fill="white",
                font=("Microsoft YaHei", 24, "bold"), text="--")
            # 右侧单位
            self.card_unit_items[key] = self.canvas.create_text(
                cx+card_w-18, y0+card_h-16, anchor="e", fill="#e8f4ff",
                font=("Microsoft YaHei", 10), text=unit)

        # 点击: 风扇 / 齿轮
        self.canvas.bind("<Button-1>", self.on_canvas_click)

    # 兼容: Tk Canvas 没有 create_round_rect, 这里给它动态加一个
    def _round_rect_helper(self, x1, y1, x2, y2, radius=14, **kw):
        pts = [
            x1+radius, y1, x2-radius, y1, x2, y1, x2, y1+radius,
            x2, y2-radius, x2, y2, x2-radius, y2, x1+radius, y2,
            x1, y2, x1, y2-radius, x1, y1+radius, x1, y1,
        ]
        return self.canvas._polygon(pts, **kw) if False else self.canvas.create_polygon(
            self._rounded_poly(x1, y1, x2, y2, radius), **kw)

    @staticmethod
    def _rounded_poly(x1, y1, x2, y2, r):
        import math
        pts = []
        corners = [(x2-r, y1+r, 270, 360), (x2-r, y2-r, 180, 270),
                   (x1+r, y2-r, 90, 180),  (x1+r, y1+r, 0, 90)]
        for cx, cy, a0, a1 in corners:
            for a in range(a0, a1+1, 6):
                pts.append(cx + r*math.cos(math.radians(a)))
                pts.append(cy + r*math.sin(math.radians(a)))
        return pts

    def _scene_update(self):
        """按当前状态同步刷新场景显示(背景/电视/风扇)。"""
        # 背景: 光照 < 阈值 -> u0 关灯, 否则 u1 开灯
        bg = self.bg_dark if (self.light is not None
                              and self.light < self.light_threshold) else self.bg_light
        self.canvas.itemconfigure(self.bg_item, image=bg)
        # 电视画面: 风扇开 -> 彩色, 关 -> 黑屏
        tv = self.tv_on_img if self.fan_on else self.tv_off_img
        self.canvas.itemconfigure(self.tv_item, image=tv)
        # 风扇: 开 -> 旋转动画(帧在 _animate 中切换), 关 -> 停止图标
        if not self.fan_on:
            self.canvas.itemconfigure(self.fan_item, image=self.fan_stop_img)

    # ---------------------------------------------------------------- #
    # 登录 / 连接
    # ---------------------------------------------------------------- #
    def _create_client_and_login(self, show_error=True):
        mode = self.mode_var.get()
        server = self.server_var.get().strip()
        user = self.user_var.get().strip()
        pwd = self.pass_var.get().strip()
        if mode == "demo":
            self.client = DemoClient()
        else:
            self.client = create_client(mode, server, user, pwd)
        ok, msg = self.client.login(user, pwd)
        self.logged = ok
        if ok:
            self.device_id = None
            self._set_msg("登录成功")
        else:
            self._set_msg("登录失败: %s" % msg)
            if show_error and mode == "cloud":
                tk.messagebox.showwarning("环境监控", "登录失败:\n%s" % msg)
        return ok

    def on_login(self):
        self._create_client_and_login(show_error=True)
        self._refresh_now()

    # ---------------------------------------------------------------- #
    # 数据采集
    # ---------------------------------------------------------------- #
    def _fetch(self):
        """读取传感器数据, 返回 (values dict, device_id) 或 (None, None)。"""
        tags = [self.tag_temp, self.tag_hum, self.tag_light, self.tag_body]
        raw = self.client.fetch_sensor(tags)
        out = {}
        device_id = None
        for tag in tags:
            item = raw.get(tag) or {}
            if tag not in raw and len(raw):
                # 处理标签重复(同 tag 多个设备)时仍取第一个
                for k, v in raw.items():
                    if str(k) == tag:
                        item = v or {}
                        break
            out[tag] = item.get("value")
            if device_id is None and item.get("device_id") is not None:
                device_id = item.get("device_id")
        if device_id is None:
            try:
                devs = self.client.query_devices()
                if devs:
                    device_id = devs[0].get("DeviceID")
            except Exception:
                pass
        return out, device_id

    def _apply_data(self, values):
        """解析传感器数值并应用规则。"""
        self.temp = normalize_number(values.get(self.tag_temp))
        self.hum = normalize_number(values.get(self.tag_hum))
        self.light = normalize_number(values.get(self.tag_light))
        raw_body = values.get(self.tag_body)
        try:
            self.body_on = (float(str(raw_body)) > 0) if raw_body is not None else False
        except (TypeError, ValueError):
            self.body_on = False

        # ---- 控制规则 ----
        # 有人(红外=1) -> 自动开启风扇
        # 无人(红外=0) -> 自动关闭, 但允许用户手动关闭(优先)
        # 温度 >= 阈值   -> 强制开启(最高优先的独立规则, 无人时仍可被手动关闭)
        if self.body_on:
            self.manual_off = False
        if self.body_on:
            self.fan_on = True
        elif self.manual_off:
            self.fan_on = False
        else:
            self.fan_on = bool(
                self.temp is not None and self.temp >= self.temp_threshold)

    # ---------------------------------------------------------------- #
    # 执行器指令下发(与实训工位设备同步)
    # ---------------------------------------------------------------- #
    def _apply_actuators(self):
        """下发风扇与常亮指示灯指令到云服务系统。"""
        if not self.client:
            return
        device = self.device_id if self.device_id is not None else 1
        fan_val = 1 if self.fan_on else 0
        # 光照 < 阈值: 判定"关灯", 常亮指示灯-白 置 On(1); 否则 Off(0)
        light_on = 1 if (self.light is not None
                         and self.light < self.light_threshold) else 0
        try:
            ok1, m1 = self.client.send_command(device, self.tag_fan, fan_val)
            ok2, m2 = self.client.send_command(device, self.tag_light_on, light_on)
            if not (ok1 and ok2):
                self._set_msg("指令下发异常: %s / %s" % (m1, m2))
        except Exception as exc:
            self._set_msg("指令下发失败: %s" % exc)

    # ---------------------------------------------------------------- #
    # 界面刷新
    # ---------------------------------------------------------------- #
    def on_refresh_now(self):
        """手动立即刷新。"""
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
            self._after_id = None
        self._refresh_now()
        self._schedule()

    def _refresh_now(self):
        """读取数据并刷新全部显示。"""
        try:
            if self.client is None or not self.logged:
                if self.mode_var.get() == "cloud":
                    self._set_msg("尚未登录云服务系统, 请先点击登录")
                    return
            values, device_id = self._fetch()
            self.device_id = device_id
            self._apply_data(values)
            self.last_ok = True
        except Exception as exc:
            self.last_ok = False
            self._set_msg("数据读取失败: %s" % exc)

        self._scene_update()
        self._update_table()
        if self.last_ok:
            self._apply_actuators()

    def _update_table(self):
        """更新底部 4 个圆角卡片上的数值。"""
        # 温度卡
        if self.temp is None:
            self.canvas.itemconfigure(self.card_value_items["temp"], text="--")
        else:
            self.canvas.itemconfigure(self.card_value_items["temp"],
                                       text="%.1f" % self.temp)
        # 湿度卡
        if self.hum is None:
            self.canvas.itemconfigure(self.card_value_items["hum"], text="--")
        else:
            self.canvas.itemconfigure(self.card_value_items["hum"],
                                       text="%.0f" % self.hum)
        # 人体卡
        body_txt = "有人" if self.body_on else "无人"
        self.canvas.itemconfigure(self.card_value_items["body"], text=body_txt)
        # 光照卡
        if self.light is None:
            self.canvas.itemconfigure(self.card_value_items["light"], text="--")
        else:
            self.canvas.itemconfigure(self.card_value_items["light"],
                                       text="%.0f" % self.light)

    # ---------------------------------------------------------------- #
    # 风扇点击(无人时手动关闭)
    # ---------------------------------------------------------------- #
    def on_canvas_click(self, event):
        # 齿轮设置按钮
        gx0, gy0, gx1, gy1 = self.gear_zone
        if gx0 <= event.x <= gx1 and gy0 <= event.y <= gy1:
            self._open_settings()
            return
        # 风扇点击(无人时手动关闭)
        x0, y0, x1, y1 = self.fan_zone
        if x0 <= event.x <= x1 and y0 <= event.y <= y1:
            if self.body_on:
                self._set_msg("有人: 风扇由规则自动开启(不可手动关闭)")
                return
            # 无人: 点击手动关闭风扇; 再点一次恢复温度规则
            self.manual_off = not self.manual_off
            if self.manual_off:
                self.fan_on = False
            else:
                self.fan_on = bool(
                    self.temp is not None and self.temp >= self.temp_threshold)
            self._scene_update()
            self._update_table()
            self._apply_actuators()
            if self.fan_on:
                self._set_msg("无人: 风扇由温度规则开启(点击可手动关闭)")
            else:
                self._set_msg("无人: 已手动关闭风扇, 电视同步黑屏")

    # ---------------------------------------------------------------- #
    # 右上角齿轮: 设置/登录对话框
    # ---------------------------------------------------------------- #
    def _open_settings(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("设置 / 登录云服务")
        dlg.geometry("420x260")
        dlg.transient(self.root)
        dlg.grab_set()

        tk.Label(dlg, text="模式:").grid(row=0, column=0, padx=12, pady=10, sticky="e")
        mode_var = tk.StringVar(value=getattr(self, "mode_var", None).get()
                                 if hasattr(self, "mode_var") and self.mode_var else
                                 self.cfg.get("mode", "demo"))
        ttk.Combobox(dlg, textvariable=mode_var, width=10,
                     values=("cloud", "demo"), state="readonly").grid(row=0, column=1, sticky="w")

        tk.Label(dlg, text="服务器:").grid(row=1, column=0, padx=12, pady=6, sticky="e")
        server_var = tk.StringVar(value=self.cfg.get("server_url", ""))
        tk.Entry(dlg, textvariable=server_var, width=30).grid(row=1, column=1, columnspan=2, sticky="w")

        tk.Label(dlg, text="用户名:").grid(row=2, column=0, padx=12, pady=6, sticky="e")
        user_var = tk.StringVar(value=self.cfg.get("username", ""))
        tk.Entry(dlg, textvariable=user_var, width=20).grid(row=2, column=1, columnspan=2, sticky="w")

        tk.Label(dlg, text="密码:").grid(row=3, column=0, padx=12, pady=6, sticky="e")
        pass_var = tk.StringVar(value=self.cfg.get("password", ""))
        tk.Entry(dlg, textvariable=pass_var, show="*", width=20).grid(row=3, column=1, columnspan=2, sticky="w")

        msg_var = tk.StringVar(value="")
        tk.Label(dlg, textvariable=msg_var, fg="#b23030",
                 font=("Microsoft YaHei", 9)).grid(row=5, column=0, columnspan=3, pady=(6, 0))

        def do_login():
            self.mode_var = mode_var
            self.server_var = server_var
            self.user_var = user_var
            self.pass_var = pass_var
            try:
                self._create_client_and_login(show_error=True)
                if self.logged:
                    msg_var.set("登录成功")
                    self._refresh_now()
                    dlg.destroy()
                else:
                    msg_var.set("登录失败, 请检查参数")
            except Exception as exc:
                msg_var.set("错误: %s" % exc)

        tk.Button(dlg, text="登录 / 保存", command=do_login,
                  bg="#1f6fb2", fg="white", width=12).grid(row=4, column=1, pady=12, sticky="w")
        tk.Button(dlg, text="关闭", command=dlg.destroy, width=8).grid(row=4, column=2, pady=12)

    # ---------------------------------------------------------------- #
    # 风扇旋转动画
    # ---------------------------------------------------------------- #
    def _animate(self, force=False):
        if self.fan_on:
            self.angle = (self.angle + 1) % len(self.fan_frames)
            self.canvas.itemconfigure(self.fan_item, image=self.fan_frames[self.angle])
        elif force:
            self.canvas.itemconfigure(self.fan_item, image=self.fan_stop_img)
        self._anim_id = self.root.after(80, self._animate)

    # ---------------------------------------------------------------- #
    # 定时刷新
    # ---------------------------------------------------------------- #
    def _schedule(self):
        self._after_id = self.root.after(int(self.interval * 1000), self._on_timer)

    def _on_timer(self):
        self._after_id = None
        self._refresh_now()
        self._schedule()

    def _set_msg(self, text):
        """顶部居中浮层提示, 3 秒后自动消失。"""
        if hasattr(self, "msg_item") and self.msg_item is not None:
            try:
                self.canvas.delete(self.msg_item)
            except Exception:
                pass
        self.msg_item = self.canvas.create_text(
            self.WIN_W//2, 30, anchor="n", fill="#ffffff",
            font=("Microsoft YaHei", 12, "bold"), text=text)
        # 加半透明背景条
        self.msg_bg = self.canvas.create_rectangle(
            self.WIN_W//2-200, 8, self.WIN_W//2+200, 52,
            fill="#333333", outline="")
        self.canvas.tag_lower(self.msg_bg, self.msg_item)
        if hasattr(self, "_msg_timer") and self._msg_timer is not None:
            try:
                self.root.after_cancel(self._msg_timer)
            except Exception:
                pass
        self._msg_timer = self.root.after(3000, self._clear_msg)

    def _clear_msg(self):
        try:
            if hasattr(self, "msg_item") and self.msg_item is not None:
                self.canvas.delete(self.msg_item)
            if hasattr(self, "msg_bg") and self.msg_bg is not None:
                self.canvas.delete(self.msg_bg)
        except Exception:
            pass
        self.msg_item = None
        self.msg_bg = None

    # ---------------------------------------------------------------- #
    def on_close(self):
        if self._after_id is not None:
            self.root.after_cancel(self._after_id)
        if self._anim_id is not None:
            self.root.after_cancel(self._anim_id)
        self.root.destroy()


def main():
    root = tk.Tk()
    app = RoomApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()


if __name__ == "__main__":
    main()