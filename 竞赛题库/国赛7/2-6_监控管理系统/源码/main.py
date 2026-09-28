"""
GZ038 物联网竞赛 - 题6 监控管理系统
基于新大陆 nle_library 官方库
通信方式: TCP/串口 → 传感器采集 → 云平台上报
"""

import http.client
import json
import threading
import time

from nle_library.common.DataObserver import DataObserver
from nle_library.databus.DataBusFactory import DataBusFactory
from nle_library.device.GenericConnector import GenericConnector
from nle_library.device.LedScreen import LedScreen
from nle_library.device.ModbusDev import ModbusDev
from nle_library.device.NLAllInOneSensor import NLAllInOneSensor
from nle_library.device.RGBLed import RGBLed


class CloudClient:
    """新大陆云平台客户端"""

    def __init__(self, host, port, project_id, device_id):
        self.host = host
        self.port = port
        self.project_id = project_id
        self.device_id = device_id
        self.token = None

    def login(self, account, password):
        conn = http.client.HTTPConnection(self.host, self.port)
        body = json.dumps(
            {"Account": account, "Password": password, "IsRememberMe": True}
        )
        conn.request(
            "POST",
            "/Users/Login",
            body=body,
            headers={"Content-Type": "application/json"},
        )
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        if data.get("Code") == 0:
            self.token = data["ResultObj"]["AccessToken"]
            print("[Cloud] 登录成功")
            return True
        print(f"[Cloud] 登录失败: {data.get('Message')}")
        return False

    def get_sensor_data(self, api_tag):
        if not self.token:
            return None
        conn = http.client.HTTPConnection(self.host, self.port)
        url = f"/devices/{self.device_id}/sensors/{api_tag}"
        conn.request("GET", url, headers={"AccessToken": self.token})
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        if data.get("Code") == 0:
            return data["ResultObj"]["Value"]
        return None

    def get_all_sensors(self):
        if not self.token:
            return None
        conn = http.client.HTTPConnection(self.host, self.port)
        url = f"/devices/{self.device_id}/Datas?project_id={self.project_id}"
        conn.request("GET", url, headers={"AccessToken": self.token})
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        if data.get("Code") == 0:
            return data["ResultObj"]
        return None

    def send_command(self, api_tag, value):
        if not self.token:
            return False
        conn = http.client.HTTPConnection(self.host, self.port)
        body = json.dumps({"Value": value})
        url = f"/Cmds?deviceId={self.device_id}&apiTag={api_tag}"
        conn.request(
            "POST",
            url,
            body=body,
            headers={"Content-Type": "application/json", "AccessToken": self.token},
        )
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        return data.get("Code") == 0


class SensorReader:
    """传感器数据采集 (基于 nle_library 官方 API)"""

    def __init__(self, data_bus):
        self.connector = GenericConnector(data_bus)
        self.data_bus = data_bus

    def connect(self):
        self.data_bus.setup(lambda result: print(f"[Bus] 连接: {result}"))
        time.sleep(1)
        return self.data_bus.openSuccess()

    def read_temperature_humidity(self, address=1):
        """读取温湿度 (多合一传感器)"""
        result = {"temperature": None, "humidity": None}

        def callback(data):
            value = NLAllInOneSensor.getTempHumiValue(data)
            if value:
                result["temperature"] = value.get("temperature")
                result["humidity"] = value.get("humidity")

        frame = NLAllInOneSensor.getTempHumiValueFrame(address)
        observer = self.connector.sendAllInOneTempHum(address, callback)
        DataObserver.wait(observer, timeout=2)
        return result

    def read_pm25(self, address=1):
        """读取 PM2.5"""

        def callback(data):
            return NLAllInOneSensor.getPM25Value(data)

        observer = self.connector.sendAllInOnePM25(address, callback)
        DataObserver.wait(observer, timeout=2)
        return observer

    def read_air_quality(self, address=1):
        """读取空气质量"""

        def callback(data):
            return NLAllInOneSensor.getAirQualityValue(data)

        observer = self.connector.sendAllInOneAirQuality(address, callback)
        DataObserver.wait(observer, timeout=2)
        return observer

    def read_body(self, address=1):
        """读取人体感应"""

        def callback(data):
            return NLAllInOneSensor.getBodyValue(data)

        observer = self.connector.sendAllInOneBody(address, callback)
        DataObserver.wait(observer, timeout=2)
        return observer

    def read_485_co2(self, address=1):
        """读取 CO2 (485)"""

        def callback(data):
            return ModbusDev.getCo2Value(data)

        observer = self.connector.sendGet485Co2Value(address, callback)
        DataObserver.wait(observer, timeout=2)
        return observer

    def read_illuminance(self, address=1):
        """读取光照度"""

        def callback(data):
            return ModbusDev.getIlluminance(data)

        observer = self.connector.sendGetIlluminance(address, callback)
        DataObserver.wait(observer, timeout=2)
        return observer

    def read_noise(self, address=1):
        """读取噪音"""

        def callback(data):
            return ModbusDev.getNoise(data)

        observer = self.connector.sendGetNoise(address, callback)
        DataObserver.wait(observer, timeout=2)
        return observer

    def control_rgb(self, r, g, b, address=1):
        """控制 RGB 灯"""

        def callback(data):
            pass

        observer = self.connector.controlRGB(r, g, b, address, callback)
        DataObserver.wait(observer, timeout=1)

    def control_led_text(self, address, x, y, text, size=16, color=1):
        """LED 屏显示文字"""

        def callback(data):
            pass

        observer = self.connector.sendLedScreenText(
            address, x, y, size, color, text, callback
        )
        DataObserver.wait(observer, timeout=1)


class MonitorSystem:
    """监控管理系统主类"""

    def __init__(self, config_file="config.json"):
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.cloud = CloudClient(
            host=self.config["cloud"]["host"],
            port=self.config["cloud"]["port"],
            project_id=self.config["cloud"]["project_id"],
            device_id=self.config["cloud"]["device_id"],
        )
        self.running = False
        self.sensor_data = {}

    def init_bus(self):
        """初始化数据总线"""
        bus_type = self.config.get("bus", "serial")
        if bus_type == "serial":
            port = self.config["serial"]["port"]
            baud = self.config["serial"]["baud"]
            return DataBusFactory.newSerialDataBus(port, baud)
        else:
            ip = self.config["tcp"]["ip"]
            port = self.config["tcp"]["port"]
            return DataBusFactory.newSocketDataBus(ip, port)

    def start(self):
        """启动系统"""
        print("[System] 初始化数据总线...")
        data_bus = self.init_bus()
        self.reader = SensorReader(data_bus)

        print("[System] 连接设备...")
        if not self.reader.connect():
            print("[System] 设备连接失败!")
            return

        print("[System] 登录云平台...")
        cloud_cfg = self.config["cloud"]
        if not self.cloud.login(cloud_cfg["account"], cloud_cfg["password"]):
            print("[System] 云平台登录失败!")
            return

        self.running = True
        print("[System] 监控系统启动成功!")

        # 启动数据采集线程
        threading.Thread(target=self._sensor_loop, daemon=True).start()
        # 启动云平台同步线程
        threading.Thread(target=self._cloud_sync_loop, daemon=True).start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def _sensor_loop(self):
        """传感器数据采集循环"""
        interval = self.config.get("sensor_interval", 2)
        addr = self.config.get("sensor_address", 1)

        while self.running:
            try:
                th = self.reader.read_temperature_humidity(addr)
                self.sensor_data["temperature"] = th.get("temperature")
                self.sensor_data["humidity"] = th.get("humidity")

                self.sensor_data["pm25"] = self.reader.read_pm25(addr)
                self.sensor_data["co2"] = self.reader.read_485_co2(addr)
                self.sensor_data["illuminance"] = self.reader.read_illuminance(addr)
                self.sensor_data["noise"] = self.reader.read_noise(addr)
                self.sensor_data["body"] = self.reader.read_body(addr)

                print(
                    f"[Sensor] T={self.sensor_data.get('temperature')} "
                    f"H={self.sensor_data.get('humidity')} "
                    f"PM2.5={self.sensor_data.get('pm25')} "
                    f"CO2={self.sensor_data.get('co2')}"
                )

            except Exception as e:
                print(f"[Sensor] 采集异常: {e}")

            time.sleep(interval)

    def _cloud_sync_loop(self):
        """云平台数据同步循环"""
        interval = self.config.get("cloud_interval", 10)
        tags = self.config.get("api_tags", {})

        while self.running:
            try:
                for key, api_tag in tags.items():
                    value = self.sensor_data.get(key)
                    if value is not None:
                        self.cloud.send_command(api_tag, str(value))
                        print(f"[Cloud] 上报 {key}={value}")

                # 读取云平台下发命令
                body_val = self.cloud.get_sensor_data(tags.get("body", "body"))
                light_val = self.cloud.get_sensor_data(tags.get("light", "light"))
                if body_val is not None:
                    self.reader.control_rgb(int(body_val), 0, 0) if body_val else None

            except Exception as e:
                print(f"[Cloud] 同步异常: {e}")

            time.sleep(interval)

    def stop(self):
        self.running = False
        print("[System] 监控系统已停止")


if __name__ == "__main__":
    system = MonitorSystem("config.json")
    system.start()
