# -*- coding: utf-8 -*-
"""
图片素材生成工具
=================
用 PIL 生成"客厅环境监控"程序所需的图片素材, 保存到本文件同目录的 images/ 文件夹。

生成内容:
    u0.jpg      室内关灯背景(深蓝昏暗室内: 窗户/沙发轮廓/台灯暖光)
    u1.jpg      室内开灯背景(暖黄明亮灯效, 同布局)
    tv_on.jpg   电视彩色画面(彩色测试卡/风景色块)
    tv_off.jpg  电视黑屏(纯黑)
    fan_on.png  风扇开启图标(圆+叶片, 彩色)
    fan_off.png 风扇关闭图标(圆+叶片, 灰色)

可直接运行:  python make_images.py
或在 room.py 启动发现素材缺失时自动调用本文件生成。
"""

import math
import os
import sys

# 禁止生成 __pycache__
sys.dont_write_bytecode = True

from PIL import Image, ImageDraw

W, H = 640, 400

# ============================ 关灯背景 u0 ============================


def make_u0(path):
    """室内关灯背景: 深蓝昏暗房间(窗户、沙发轮廓、台灯暖光), 右墙留空给电视。"""
    img = Image.new("RGB", (W, H), (22, 28, 50))
    d = ImageDraw.Draw(img)

    # 墙面(深蓝)与深浅渐变
    for i in range(8):
        y = i * 50
        d.rectangle([0, y, W, y + 50], fill=(24 + i, 30 + i, 52 + i * 2))

    # 地板
    d.rectangle([0, 300, W, H], fill=(40, 32, 25))
    d.rectangle([0, 300, W, 306], fill=(58, 46, 36))  # 踢脚线

    # ---- 窗户(左墙) ----
    d.rectangle([40, 32, 235, 195], fill=(66, 76, 100))          # 窗框
    d.rectangle([46, 38, 229, 189], fill=(26, 48, 96))           # 玻璃
    d.rectangle([130, 38, 138, 189], fill=(72, 84, 112))         # 竖棂
    d.rectangle([46, 112, 229, 120], fill=(72, 84, 112))         # 横棂
    for sx, sy in ((60, 70), (90, 150), (170, 100), (195, 160)):  # 星星
        d.rectangle([sx, sy, sx + 2, sy + 2], fill=(210, 220, 240))
    d.ellipse([172, 46, 190, 62], fill=(200, 208, 226))          # 月亮
    # 窗帘
    d.rectangle([236, 30, 246, 198], fill=(78, 54, 64))
    d.rectangle([30, 30, 42, 198], fill=(68, 46, 56))
    d.rectangle([28, 24, 248, 32], fill=(84, 74, 62))            # 窗帘杆

    # ---- 墙壁书架(左墙) ----
    d.rectangle([60, 104, 210, 122], fill=(58, 44, 32))          # 搁板
    d.rectangle([66, 78, 84, 104], fill=(120, 60, 60))
    d.rectangle([88, 82, 108, 104], fill=(92, 110, 62))
    d.rectangle([112, 76, 128, 104], fill=(120, 110, 60))
    d.rectangle([132, 84, 150, 104], fill=(70, 92, 120))

    # ---- 沙发 ----
    d.rounded_rectangle([70, 190, 300, 300], radius=14, fill=(40, 44, 64))     # 底座
    d.rounded_rectangle([80, 148, 170, 205], radius=10, fill=(46, 50, 72))     # 左扶手
    d.rounded_rectangle([230, 148, 295, 205], radius=10, fill=(46, 50, 72))    # 右扶手
    d.rounded_rectangle([100, 140, 270, 200], radius=12, fill=(52, 56, 80))    # 靠背
    d.rounded_rectangle([92, 200, 282, 226], radius=8, fill=(58, 62, 88))      # 坐垫

    # 地毯
    d.ellipse([120, 300, 380, 340], fill=(44, 40, 60))
    # 茶几
    d.rounded_rectangle([205, 292, 370, 318], radius=6, fill=(56, 44, 32))

    # ---- 台灯(左前地板) ----
    d.rectangle([20, 250, 31, 302], fill=(46, 40, 34))           # 灯杆
    d.ellipse([6, 298, 46, 318], fill=(60, 50, 42))              # 底座
    d.polygon([(4, 216), (44, 216), (27, 182)], fill=(72, 60, 46))  # 灯罩
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([0, 170, 60, 245], fill=(150, 120, 70, 40))       # 台灯光晕
    img = Image.alpha_composite(img.convert("RGBA"), glow)

    # 整体压暗增加夜色氛围
    shadow = Image.new("RGBA", (W, H), (8, 6, 16, 50))
    img = Image.alpha_composite(img, shadow)
    img.convert("RGB").save(path, "JPEG", quality=88)
    return path


# ============================ 开灯背景 u1 ============================


def make_u1(path):
    """室内开灯背景: 同布局但暖黄明亮灯效, 右墙留空给电视。"""
    img = Image.new("RGB", (W, H), (230, 210, 175))
    d = ImageDraw.Draw(img)

    # 墙面(暖色)
    for i in range(8):
        y = i * 50
        d.rectangle([0, y, W, y + 50], fill=(226 + i, 206 + i, 168 + i))

    # 地板
    d.rectangle([0, 300, W, H], fill=(152, 112, 74))
    d.rectangle([0, 300, W, 306], fill=(190, 150, 100))

    # ---- 窗户(白天明亮) ----
    d.rectangle([40, 32, 235, 195], fill=(150, 150, 140))
    d.rectangle([46, 38, 229, 189], fill=(150, 205, 250))         # 玻璃
    d.rectangle([130, 38, 138, 189], fill=(210, 230, 248))        # 竖棂
    d.rectangle([46, 112, 229, 120], fill=(210, 230, 248))        # 横棂
    d.ellipse([52, 48, 82, 78], fill=(255, 236, 130))             # 太阳
    d.rectangle([236, 30, 246, 198], fill=(200, 120, 130))        # 窗帘
    d.rectangle([30, 30, 42, 198], fill=(185, 104, 114))
    d.rectangle([28, 24, 248, 32], fill=(168, 140, 100))

    # ---- 墙壁书架 ----
    d.rectangle([60, 104, 210, 122], fill=(120, 92, 62))
    d.rectangle([66, 78, 84, 104], fill=(190, 90, 90))
    d.rectangle([88, 82, 108, 104], fill=(150, 178, 96))
    d.rectangle([112, 76, 128, 104], fill=(190, 176, 92))
    d.rectangle([132, 84, 150, 104], fill=(110, 150, 188))

    # ---- 沙发 ----
    d.rounded_rectangle([70, 190, 300, 300], radius=14, fill=(150, 118, 102))
    d.rounded_rectangle([80, 148, 170, 205], radius=10, fill=(168, 132, 114))
    d.rounded_rectangle([230, 148, 295, 205], radius=10, fill=(168, 132, 114))
    d.rounded_rectangle([100, 140, 270, 200], radius=12, fill=(178, 142, 122))
    d.rounded_rectangle([92, 200, 282, 226], radius=8, fill=(196, 158, 134))

    # 地毯
    d.ellipse([120, 300, 380, 340], fill=(130, 108, 96))
    # 茶几
    d.rounded_rectangle([205, 292, 370, 318], radius=6, fill=(116, 86, 54))

    # ---- 台灯(明亮) ----
    d.rectangle([20, 250, 31, 302], fill=(130, 108, 88))
    d.ellipse([6, 298, 46, 318], fill=(150, 126, 100))
    d.polygon([(4, 216), (44, 216), (27, 182)], fill=(170, 152, 116))
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd = ImageDraw.Draw(glow)
    gd.ellipse([0, 168, 62, 248], fill=(255, 216, 130, 70))
    img = Image.alpha_composite(img.convert("RGBA"), glow)

    # 屋顶暖光吊灯
    dd = ImageDraw.Draw(img)
    dd.rectangle([300, 26, 360, 36], fill=(120, 104, 86))
    dd.polygon([(308, 36), (352, 36), (340, 58), (320, 58)], fill=(240, 228, 180))
    glow2 = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    gd2 = ImageDraw.Draw(glow2)
    gd2.ellipse([250, 36, 410, 120], fill=(255, 224, 150, 60))
    img = Image.alpha_composite(img, glow2)

    img.convert("RGB").save(path, "JPEG", quality=90)
    return path


# ============================ 电视画面 ============================


def make_tv_on(path):
    """电视彩色画面: 风景色块+彩色测试卡色条。"""
    tw, th = 340, 220
    img = Image.new("RGB", (tw, th), (40, 40, 50))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, tw, th], fill=(110, 190, 250))             # 天空
    d.ellipse([252, 20, 297, 65], fill=(255, 220, 60))            # 太阳
    d.rectangle([0, 150, tw, th], fill=(70, 160, 60))             # 草地
    d.polygon([(0, 150), (90, 80), (180, 150)], fill=(90, 130, 90))
    d.polygon([(160, 150), (270, 60), (340, 150)], fill=(100, 150, 100))
    d.rectangle([60, 108, 130, 165], fill=(230, 160, 90))         # 房子
    d.polygon([(55, 108), (95, 72), (135, 108)], fill=(205, 60, 60))
    d.rectangle([92, 128, 108, 165], fill=(150, 90, 50))
    bars = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]  # 测试卡色条
    bw = tw // 4
    for i, c in enumerate(bars):
        d.rectangle([i * bw, th - 28, (i + 1) * bw, th], fill=c)
    img.save(path, "JPEG", quality=88)
    return path


def make_tv_off(path):
    """电视黑屏: 纯黑。"""
    img = Image.new("RGB", (340, 220), (5, 5, 5))
    img.save(path, "JPEG", quality=90)
    return path


# ============================ 风扇图标 ============================


def _fan_icon(on):
    """绘制风扇图标(圆+4片叶片+中心轴)。on=True 彩色, on=False 灰色。"""
    S = 160
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    cx, cy = S // 2, S // 2

    if on:
        blade = (70, 190, 120)
        hub = (240, 150, 60)
        cage = (120, 160, 210)
    else:
        blade = (175, 180, 182)
        hub = (165, 165, 168)
        cage = (140, 140, 143)

    r = S // 2 - 8
    for idx in range(4):
        ang = idx * (math.pi / 2)
        ex = cx + int(math.cos(ang) * r * 0.45)
        ey = cy + int(math.sin(ang) * r * 0.45)
        d.ellipse([ex - 22, ey - 34, ex + 22, ey + 34], fill=blade)
    d.ellipse([cx - 20, cy - 20, cx + 20, cy + 20], fill=hub)
    d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=(250, 250, 250))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=cage, width=6)
    return img


def ensure_images(force=False):
    """确保所有图片素材存在; force=True 时强制重新生成。"""
    here = os.path.dirname(os.path.abspath(__file__))
    folder = os.path.join(here, "images")
    if not os.path.isdir(folder):
        os.makedirs(folder)
    jobs = [
        ("u0.jpg", make_u0),
        ("u1.jpg", make_u1),
        ("tv_on.jpg", make_tv_on),
        ("tv_off.jpg", make_tv_off),
    ]
    for name, fn in jobs:
        p = os.path.join(folder, name)
        if force or not os.path.isfile(p):
            fn(p)
    for name, on in (("fan_on.png", True), ("fan_off.png", False)):
        p = os.path.join(folder, name)
        if force or not os.path.isfile(p):
            _fan_icon(on).save(p, "PNG")
    return folder


if __name__ == "__main__":
    folder = ensure_images(force=True)
    for name in (
        "u0.jpg", "u1.jpg", "tv_on.jpg", "tv_off.jpg", "fan_on.png", "fan_off.png",
    ):
        if os.path.isfile(os.path.join(folder, name)):
            print("OK %s" % name)
    print("图片素材目录:", folder)