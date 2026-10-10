@echo off
chcp 65001 >nul
set QT_QPA_PLATFORM_PLUGIN_PATH=D:\环境部署\运行时\python36\Lib\site-packages\PyQt5\Qt5\plugins\platforms
"D:\环境部署\运行时\python36\python.exe" "%~dp0monitor_system_official.py"
pause
