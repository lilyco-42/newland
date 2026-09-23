# 国赛7 模块二 Android/Python 源码与二进制归档

> 归档时间：2026-09-18
> 说明：国赛7（GZ038 第7套）模块二子任务 2-5/2-6/2-7 对应 Android 与 Python 应用，本目录收录**完整源码 + 可运行二进制**，供备赛参考与提交使用。

## 对应关系

| 子任务 | 项目名称 | 技术栈 | 源码位置 | 二进制位置 |
|---|---|---|---|---|
| 2-5 环境监测系统 | 环境监测系统 | Android (Gradle + Java) | `2-5_环境监测系统/源码/` | `2-5_环境监测系统/二进制/环境监测系统.apk` (1.9MB) |
| 2-6 监控管理系统 | 监控管理系统 | Python (Tkinter + nlecloud SDK) | `2-6_监控管理系统/源码/` | `2-6_监控管理系统/二进制/监控管理系统.exe` (+_internal) |
| 2-7 客厅环境监控系统升级 | 客厅环境监控 | Python (Tkinter + nle_cloud) | `2-7_客厅环境监控/源码/` | `2-7_客厅环境监控/二进制/环境监控.exe` (+_internal) |

## 源码内容

### 2-5 环境监测系统（Android）
- 完整 Gradle 工程：`build.gradle` / `settings.gradle` / `gradlew` + wrapper
- 源码：`app/src/main/`、`java/com/env/`（Activity + 逻辑）、`res/`（布局/图标/背景图）
- 功能：环境数据（温湿度/光照/CO2/人体）显示，云平台对接

### 2-6 监控管理系统（Python）
- 主程序：`监控管理系统.py`（29KB，Tkinter 界面 + 云平台逻辑）
- 依赖库：`nlecloud_sdk.py` / `nlecloud_client.py` / `main.py`
- 打包配置：`监控管理系统.spec`，运行配置 `config.json`

### 2-7 客厅环境监控（Python）
- 主程序：`环境监控.py`（29KB）+ `make_images.py`（场景图生成）
- 依赖库：`nle_cloud.py` / `nlecloud_sdk.py` / `room_monitor.py`
- 资源：`images/`（风扇/电视/场景图素材）

## 说明
- 二进制为 PyInstaller 打包产物（含 `_internal` 运行依赖目录），可直接双击运行；无硬件时界面容错显示 `--`
- Android apk 需 Android 设备或模拟器安装，云平台参数在 `config.json` / 代码内配置
- 源码排除 `.venv` / `build` / `dist` / `__pycache__` 等可再生成物
