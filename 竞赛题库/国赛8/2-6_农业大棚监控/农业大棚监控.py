# -*- coding: utf-8 -*-
"""套8 2-6 智能农业大棚监控 - Python 3.6 兼容"""
import time

try:
    import requests
except ImportError:
    requests = None


class NLECloudClient:
    BASE = "http://api.nlecloud.com"

    def __init__(self):
        self.token = ""

    def login(self, account, password):
        r = requests.post(
            "%s/Users/Login" % self.BASE,
            json={"Account": account, "Password": password, "IsRememberMe": True},
        )
        data = r.json()
        if data["Status"] == 0:
            self.token = data["ResultObj"]["AccessToken"]
            return True
        return False

    def upload_data(self, device_id, api_tag, value):
        r = requests.post(
            "%s/Devices/%s/Datas" % (self.BASE, device_id),
            headers={"AccessToken": self.token},
            json={"DatasDTO": [{"ApiTag": api_tag, "Value": str(value)}]},
        )
        return r.json()

    def send_command(self, device_id, api_tag, value):
        r = requests.post(
            "%s/Cmds" % self.BASE,
            headers={"AccessToken": self.token},
            params={"deviceId": device_id, "apiTag": api_tag},
            json=value,
        )
        return r.json()


class GreenhouseMonitor:
    """智能农业大棚监控"""
    TEMP_HIGH = 35.0
    TEMP_LOW = 15.0
    HUMI_HIGH = 85.0
    HUMI_LOW = 40.0
    SOIL_LOW = 30.0
    LIGHT_LOW = 2000

    def __init__(self):
        self.data = {
            "air_temp": 25.0,
            "air_humi": 60.0,
            "soil_temp": 22.0,
            "soil_humi": 45.0,
            "light": 5000,
            "co2": 400,
        }
        self.devices = {
            "fan": False,
            "heater": False,
            "pump": False,
            "light": False,
            "vent": False,
        }
        self.cloud = None

    def connect_cloud(self, account, password):
        if requests:
            self.cloud = NLECloudClient()
            if self.cloud.login(account, password):
                print("[OK] 云平台已连接")
                return True
        return False

    def check_and_control(self):
        """阈值检测与自动控制"""
        d = self.data
        alerts = []

        # 温度控制
        if d["air_temp"] > self.TEMP_HIGH:
            self.devices["fan"] = True
            self.devices["heater"] = False
            alerts.append("温度过高%.1fC->开风扇" % d["air_temp"])
        elif d["air_temp"] < self.TEMP_LOW:
            self.devices["fan"] = False
            self.devices["heater"] = True
            alerts.append("温度过低%.1fC->开加热" % d["air_temp"])
        else:
            self.devices["fan"] = False
            self.devices["heater"] = False

        # 湿度控制
        if d["air_humi"] > self.HUMI_HIGH:
            self.devices["vent"] = True
            alerts.append("湿度过高%.1f%%->开通风" % d["air_humi"])
        else:
            self.devices["vent"] = False

        # 土壤湿度控制（灌溉）
        if d["soil_humi"] < self.SOIL_LOW:
            self.devices["pump"] = True
            alerts.append("土壤过干%.1f%%->开灌溉" % d["soil_humi"])
        else:
            self.devices["pump"] = False

        # 光照控制
        if d["light"] < self.LIGHT_LOW:
            self.devices["light"] = True
            alerts.append("光照不足%d->开补光" % d["light"])
        else:
            self.devices["light"] = False

        return alerts

    def upload_to_cloud(self, device_id=1):
        if not self.cloud:
            return
        for tag, val in self.data.items():
            self.cloud.upload_data(device_id, tag, val)
        print("[UPLOAD] 数据已上传")

    def show_status(self):
        print("\n" + "=" * 50)
        print("  智能农业大棚监控")
        print("=" * 50)
        print("  空气温度: %.1f C    空气湿度: %.1f %%" % (
            self.data["air_temp"], self.data["air_humi"]))
        print("  土壤温度: %.1f C    土壤湿度: %.1f %%" % (
            self.data["soil_temp"], self.data["soil_humi"]))
        print("  光照强度: %d Lux    CO2浓度: %d ppm" % (
            self.data["light"], self.data["co2"]))
        print("-" * 50)
        print("  设备状态:")
        for name, state in self.devices.items():
            status = "ON" if state else "OFF"
            print("    %-8s : %s" % (name, status))
        print("=" * 50)

    def run(self, interval=10):
        print("智能农业大棚监控系统启动...")
        while True:
            alerts = self.check_and_control()
            self.show_status()
            for a in alerts:
                print("[AUTO] %s" % a)
            self.upload_to_cloud()
            time.sleep(interval)


if __name__ == "__main__":
    gh = GreenhouseMonitor()
    gh.connect_cloud("13329262958", "qwe123456789")
    gh.run()
