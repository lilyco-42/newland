# -*- coding: utf-8 -*-
"""套3 2-7 室内环境控制 - Python 3.6 兼容"""
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
        r = requests.post("%s/Users/Login" % self.BASE,
            json={"Account": account, "Password": password, "IsRememberMe": True})
        data = r.json()
        if data["Status"] == 0:
            self.token = data["ResultObj"]["AccessToken"]
            return True
        return False
    def upload_data(self, device_id, api_tag, value):
        r = requests.post("%s/Devices/%s/Datas" % (self.BASE, device_id),
            headers={"AccessToken": self.token},
            json={"DatasDTO": [{"ApiTag": api_tag, "Value": str(value)}]})
        return r.json()
    def send_command(self, device_id, api_tag, value):
        r = requests.post("%s/Cmds" % self.BASE,
            headers={"AccessToken": self.token},
            params={"deviceId": device_id, "apiTag": api_tag}, json=value)
        return r.json()


class IndoorEnvControl:
    """室内环境控制系统"""
    def __init__(self):
        self.data = {"temp": 25.0, "humi": 55.0, "light": 400, "pm25": 30.0}
        self.devices = {"ac": False, "humidifier": False, "light": False}
        self.cloud = None

    def connect_cloud(self, account, password):
        if requests:
            self.cloud = NLECloudClient()
            if self.cloud.login(account, password):
                print("[OK] 云平台已连接")
                return True
        return False

    def auto_control(self):
        d = self.data
        if d["temp"] > 28:
            self.devices["ac"] = True
        elif d["temp"] < 20:
            self.devices["ac"] = False
        if d["humi"] < 40:
            self.devices["humidifier"] = True
        elif d["humi"] > 65:
            self.devices["humidifier"] = False
        if d["light"] < 300:
            self.devices["light"] = True

    def show(self):
        print("\n=== 室内环境 ===")
        print("温度: %.1fC  湿度: %.1f%%  光照: %d  PM2.5: %.1f" % (
            self.data["temp"], self.data["humi"],
            self.data["light"], self.data["pm25"]))
        print("空调: %s  加湿器: %s  灯: %s" % (
            "ON" if self.devices["ac"] else "OFF",
            "ON" if self.devices["humidifier"] else "OFF",
            "ON" if self.devices["light"] else "OFF"))

    def run(self, interval=10):
        print("室内环境控制系统启动")
        while True:
            self.auto_control()
            self.show()
            if self.cloud:
                for k, v in self.data.items():
                    self.cloud.upload_data(1, k, v)
            time.sleep(interval)


if __name__ == "__main__":
    env = IndoorEnvControl()
    env.connect_cloud("13329262958", "qwe123456789")
    env.run()
