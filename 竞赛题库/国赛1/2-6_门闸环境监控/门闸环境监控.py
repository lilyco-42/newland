# -*- coding: utf-8 -*-
"""套1 2-6 门闸环境监控系统 - Python 3.6 兼容"""
import json
import time
import threading

try:
    import requests
except ImportError:
    requests = None

try:
    import serial
except ImportError:
    serial = None


class NLECloudClient:
    """新大陆物联网云平台 API 客户端"""
    BASE = "http://api.nlecloud.com"

    def __init__(self):
        self.token = ""

    def login(self, account, password):
        """登录获取Token"""
        r = requests.post(
            "%s/Users/Login" % self.BASE,
            json={
                "Account": account,
                "Password": password,
                "IsRememberMe": True,
            },
        )
        data = r.json()
        if data["Status"] == 0:
            self.token = data["ResultObj"]["AccessToken"]
            return True
        return False

    def upload_data(self, device_id, api_tag, value):
        """上传传感器数据"""
        r = requests.post(
            "%s/Devices/%s/Datas" % (self.BASE, device_id),
            headers={"AccessToken": self.token},
            json={"DatasDTO": [{"ApiTag": api_tag, "Value": str(value)}]},
        )
        return r.json()

    def send_command(self, device_id, api_tag, value):
        """发送控制命令"""
        r = requests.post(
            "%s/Cmds" % self.BASE,
            headers={"AccessToken": self.token},
            params={"deviceId": device_id, "apiTag": api_tag},
            json=value,
        )
        return r.json()


class EnvironmentMonitor:
    """门闸环境监控"""
    # 阈值配置
    TEMP_HIGH = 35.0    # 温度上限
    TEMP_LOW = 10.0     # 温度下限
    HUMI_HIGH = 80.0    # 湿度上限
    HUMI_LOW = 30.0     # 湿度下限
    PM25_HIGH = 75.0    # PM2.5上限
    CO2_HIGH = 1000.0   # CO2上限

    def __init__(self):
        self.data = {
            "temperature": 25.0,
            "humidity": 50.0,
            "pm25": 35.0,
            "co2": 450.0,
            "light": 500,
        }
        self.alerts = []
        self.running = False
        self.ser = None
        self.cloud = None

    def connect_serial(self, port="COM3", baudrate=9600):
        """连接串口（ZigBee网关）"""
        if serial:
            try:
                self.ser = serial.Serial(port, baudrate, timeout=1)
                print("[OK] 串口已连接: %s" % port)
                return True
            except Exception as e:
                print("[ERR] 串口连接失败: %s" % e)
        return False

    def connect_cloud(self, account, password):
        """连接云平台"""
        if requests:
            self.cloud = NLECloudClient()
            if self.cloud.login(account, password):
                print("[OK] 云平台已连接")
                return True
        return False

    def read_serial_data(self):
        """从串口读取传感器数据"""
        if not self.ser:
            return None
        try:
            line = self.ser.readline().decode("utf-8", errors="ignore").strip()
            if line:
                # 格式: T:25.5,H:60.2,P:35,C:450,L:500
                parts = line.split(",")
                for part in parts:
                    if part.startswith("T:"):
                        self.data["temperature"] = float(part[2:])
                    elif part.startswith("H:"):
                        self.data["humidity"] = float(part[2:])
                    elif part.startswith("P:"):
                        self.data["pm25"] = float(part[2:])
                    elif part.startswith("C:"):
                        self.data["co2"] = float(part[2:])
                    elif part.startswith("L:"):
                        self.data["light"] = int(part[2:])
                return self.data
        except Exception:
            pass
        return None

    def check_thresholds(self):
        """检查阈值告警"""
        self.alerts = []
        d = self.data
        if d["temperature"] > self.TEMP_HIGH:
            self.alerts.append("温度过高: %.1f°C" % d["temperature"])
        if d["temperature"] < self.TEMP_LOW:
            self.alerts.append("温度过低: %.1f°C" % d["temperature"])
        if d["humidity"] > self.HUMI_HIGH:
            self.alerts.append("湿度过高: %.1f%%" % d["humidity"])
        if d["humidity"] < self.HUMI_LOW:
            self.alerts.append("湿度过低: %.1f%%" % d["humidity"])
        if d["pm25"] > self.PM25_HIGH:
            self.alerts.append("PM2.5超标: %.1f" % d["pm25"])
        if d["co2"] > self.CO2_HIGH:
            self.alerts.append("CO2超标: %.1f" % d["co2"])
        return self.alerts

    def auto_control(self):
        """自动联动控制"""
        if not self.cloud:
            return
        alerts = self.check_thresholds()
        for alert in alerts:
            if "温度过高" in alert:
                # 开启风扇
                self.cloud.send_command(1, "fan", 1)
                print("[AUTO] 温度过高 -> 开启风扇")
            elif "温度过低" in alert:
                # 关闭风扇
                self.cloud.send_command(1, "fan", 0)
                print("[AUTO] 温度过低 -> 关闭风扇")
            elif "PM25超标" in alert or "CO2超标" in alert:
                # 开启排风
                self.cloud.send_command(1, "vent", 1)
                print("[AUTO] 空气质量差 -> 开启排风")

    def upload_to_cloud(self, device_id=1):
        """上传数据到云平台"""
        if not self.cloud:
            return
        for tag, val in self.data.items():
            self.cloud.upload_data(device_id, tag, val)
        print("[UPLOAD] 数据已上传: T=%.1f H=%.1f P=%.1f C=%.1f" % (
            self.data["temperature"], self.data["humidity"],
            self.data["pm25"], self.data["co2"],
        ))

    def run(self, interval=5):
        """主循环"""
        self.running = True
        print("=" * 40)
        print("  门闸环境监控系统")
        print("=" * 40)
        while self.running:
            # 读取数据
            if self.ser:
                self.read_serial_data()

            # 检查告警
            alerts = self.check_thresholds()
            if alerts:
                for a in alerts:
                    print("[ALERT] %s" % a)
                self.auto_control()

            # 上传数据
            self.upload_to_cloud()

            # 显示数据
            print("[DATA] T=%.1f°C  H=%.1f%%  P=%.1f  C=%.1f  L=%d" % (
                self.data["temperature"], self.data["humidity"],
                self.data["pm25"], self.data["co2"], self.data["light"],
            ))

            time.sleep(interval)

    def stop(self):
        self.running = False
        if self.ser:
            self.ser.close()


if __name__ == "__main__":
    monitor = EnvironmentMonitor()
    monitor.connect_cloud("13329262958", "qwe123456789")
    monitor.run(interval=10)
