========================================
  社区视频监控系统 - 监控管理系统
  竞赛任务 2-6
========================================

一、运行方法
----------
  确保已安装 Python 3.11 及以下库：
    - tkinter（Python 内置）
    - requests
    - Pillow（PIL）

  安装依赖：
    pip install requests Pillow

  启动程序：
    cd D:\源码\2-6_监控管理系统
    python 监控管理系统.py

二、config.json 字段说明
-----------------------
  camera.ip          - 摄像头 IP 地址，默认 192.168.1.100
  camera.port        - 摄像头端口，默认 80
  camera.user        - 登录用户名，默认 admin
  camera.pass        - 登录密码，默认 admin123
  camera.snapshot_url - 快照 URL 模板，支持 {ip}{port}{user}{pass} 占位符
  camera.stream_url   - MJPEG 流 URL 模板
  camera.ptz_url      - 云台控制 URL 模板，{dir} 替换为 up/down/left/right
  interval_ms         - 快照轮询间隔（毫秒），默认 80
  timeout             - 网络请求超时（秒），默认 3

三、支持的摄像头接入方式
-----------------------
  1. HTTP 快照轮询：定期抓取 JPEG 快照图片（默认方式）
  2. MJPEG 流：持续读取 MJPEG 视频流的帧（优先尝试，失败降级为快照）
  3. 云台 PTZ 控制：通过 HTTP GET 请求控制摄像头方向

  注：本程序不依赖 OpenCV，使用 requests + PIL 实现所有图像功能。

四、模拟模式
-----------
  当未连接真实摄像头时，程序自动进入模拟模式，
  显示带网格、REC 标志、时间戳的模拟监控画面，便于演示。
