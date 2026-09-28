# 国赛5（GZ038 第5套）模块二 Android/Python 源码与二进制归档

> 归档时间：2026-09-18

| 子任务 | 项目 | 技术栈 | 源码 | 二进制 |
|---|---|---|---|---|
| 2-4 远程监控应用开发 | 远程监控 | Android (Gradle + Java) | `2-4_远程监控应用开发/源码/` (51 文件) | `远程监控.apk` (2.2MB) + `远程监控.rar` 源码包 |
| 2-5 森林火灾报警系统 | 森林火灾监控 | Android (Gradle + Java) | `2-5_森林火灾报警系统/源码/` (42 文件) | `森林火灾监控.apk` (2.2MB) + `.rar` 源码包 |
| 2-6 运输数据监控系统 | 运输监控 | Python (Tkinter + nle_cloud) | `2-6_运输数据监控系统/源码/` (4 文件) | `运输监控.exe` (+_internal) |
| 2-7 智能商超系统 | 智能商超 | Python (Tkinter + nle_cloud) | `2-7_智能商超系统/源码/` (4 文件) | `智能商超.exe` (+_internal) |

## 说明
- 2-4 远程监控：与国赛1 同一题目（多套卷共用同一项目）
- 2-6/2-7 二进制为 PyInstaller 打包（含 `_internal` 依赖目录），可直接双击运行
- Android 源码均已剔除 `.gradle`/`build` 生成物；Python 源码剔除 `.venv`/`build`/`dist`/`__pycache__`
- 云平台参数在 `config.json` / 源码内配置（api.nlecloud.com）
