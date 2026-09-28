"""
GZ038 物联网竞赛 - 题7 客厅环境监控系统
基于新大陆 nle_library 官方库
通信方式: ZigBee → 多传感器采集 → LED屏显示 → 云平台
"""
import json
import time
import threading
import http.client
from nle_library.databus.DataBusFactory import DataBusFactory
from nle_library.device.GenericConnector import GenericConnector
from nle_library.device.ZigbeeConnector import ZigbeeConnector
from nle_library.device.Zigbee import Zigbee, ZigbeeType
from nle_library.device.RGBLed import RGBLed
from nle_library.device.LedScreen import LedScreen
from nle_library.device.UWB import UWB
from nle_library.common.DataObserver import DataObserver
from nle_library.common.UWBData import UWBData


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
        body = json.dumps({
            "Account": account,
            "Password": password,
            "IsRememberMe": True
        })
        conn.request("POST", "/Users/Login", body=body,
                     headers={"Content-Type": "application/json"})
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        if data.get("Code") == 0:
            self.token = data["ResultObj"]["AccessToken"]
            return True
        return False

    def send_command(self, api_tag, value):
        if not self.token:
            return False
        conn = http.client.HTTPConnection(self.host, self.port)
        body = json.dumps({"Value": value})
        url = f"/Cmds?deviceId={self.device_id}&apiTag={api_tag}"
        conn.request("POST", url, body=body,
                     headers={"Content-Type": "application/json",
                              "AccessToken": self.token})
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        conn.close()
        return data.get("Code") == 0

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


class ZigBeeSensorNetwork:
    """ZigBee 传感器网络管理"""

    def __init__(self, data_bus):
        self.connector = ZigbeeConnector(data_bus)
        self.data_bus = data_bus
        self.nodes = {}
        self._lock = threading.Lock()

    def connect(self):
        self.data_bus.setup(lambda result: print(f"[ZigBee] 连接: {result}"))
        time.sleep(1)
        return self.data_bus.openSuccess()

    def set_data_handler(self, callback):
        """设置数据接收回调"""
        self.connector.setDataReceivedHandler(callback)

    def control_relay(self, serial_num, channel, is_open):
        """控制继电器"""
        self.connector.doubleRelay(serial_num, channel, is_open)

    def parse_sensor_data(self, data):
        """解析 ZigBee 传感器数据"""
        if not Zigbee.isReadZigbeeFrame(data):
            return None

        info = Zigbee.getZigbeeNodeInfo(data)
        if not info:
            return None

        serial = info.get("serial")
        sensor_type = info.get("type")

        result = {"serial": serial, "type": sensor_type}

        if sensor_type == ZigbeeType.TemHum:
            th = Zigbee.getTempHumiSensorData(data)
            result["temperature"] = th.get("temperature")
            result["humidity"] = th.get("humidity")
        elif sensor_type == ZigbeeType.Light:
            result["light"] = Zigbee.getLightSensorData(data)
        elif sensor_type == ZigbeeType.Body:
            result["body"] = Zigbee.getBodySensorData(data)
        elif sensor_type == ZigbeeType.Gas:
            result["gas"] = Zigbee.getGasSensorData(data)
        elif sensor_type == ZigbeeType.Fire:
            result["fire"] = Zigbee.getFireSensorData(data)
        elif sensor_type == ZigbeeType.AirQuality:
            result["air"] = Zigbee.getAirQualitySensorData(data)
        elif sensor_type == ZigbeeType.FourInput:
            channels = Zigbee.getFourInputSensorData(data)
            result["channels"] = channels

        with self._lock:
            self.nodes[serial] = result

        return result


class HomeEnvironmentMonitor:
    """客厅环境监控系统主类"""

    def __init__(self, config_file="config.json"):
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        self.cloud = CloudClient(
            host=self.config["cloud"]["host"],
            port=self.config["cloud"]["port"],
            project_id=self.config["cloud"]["project_id"],
            device_id=self.config["cloud"]["device_id"]
        )
        self.running = False
        self.env_data = {
            "temperature": 0,
            "humidity": 0,
            "light": 0,
            "body": False,
            "gas": 0,
            "fire": False,
            "air_quality": 0
        }
        self.uwb_position = None

    def init_bus(self):
        """初始化 ZigBee 数据总线"""
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
        print("[System] 初始化 ZigBee 总线...")
        data_bus = self.init_bus()
        self.zigbee = ZigBeeSensorNetwork(data_bus)

        print("[System] 连接 ZigBee 网络...")
        if not self.zigbee.connect():
            print("[System] ZigBee 连接失败!")
            return

        print("[System] 登录云平台...")
        cloud_cfg = self.config["cloud"]
        if not self.cloud.login(cloud_cfg["account"], cloud_cfg["password"]):
            print("[System] 云平台登录失败!")

        # 设置 ZigBee 数据回调
        self.zigbee.set_data_handler(self._on_zigbee_data)

        self.running = True
        print("[System] 客厅环境监控系统启动!")

        threading.Thread(target=self._cloud_sync_loop, daemon=True).start()
        threading.Thread(target=self._led_display_loop, daemon=True).start()

        try:
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def _on_zigbee_data(self, data):
        """ZigBee 数据回调"""
        result = self.zigbee.parse_sensor_data(data)
        if result:
            with threading.Lock():
                if "temperature" in result:
                    self.env_data["temperature"] = result["temperature"]
                if "humidity" in result:
                    self.env_data["humidity"] = result["humidity"]
                if "light" in result:
                    self.env_data["light"] = result["light"]
                if "body" in result:
                    self.env_data["body"] = result["body"]
                if "gas" in result:
                    self.env_data["gas"] = result["gas"]
                if "fire" in result:
                    self.env_data["fire"] = result["fire"]
                if "air" in result:
                    self.env_data["air_quality"] = result["air"]

            print(f"[ZigBee] {result}")

    def _cloud_sync_loop(self):
        """云平台同步"""
        interval = self.config.get("cloud_interval", 10)
        tags = self.config.get("api_tags", {})

        while self.running:
            try:
                for key, api_tag in tags.items():
                    value = self.env_data.get(key)
                    if value is not None:
                        self.cloud.send_command(api_tag, str(value))

                # 检查报警
                if self.env_data.get("gas", 0) > 100:
                    self.cloud.send_command("alarm", "gas_leak")
                    print("[Alarm] 燃气泄漏!")
                if self.env_data.get("fire", False):
                    self.cloud.send_command("alarm", "fire")
                    print("[Alarm] 火警!")

            except Exception as e:
                print(f"[Cloud] 同步异常: {e}")

            time.sleep(interval)

    def _led_display_loop(self):
        """LED 屏显示循环"""
        interval = self.config.get("led_interval", 3)
        addr = self.config.get("led_address", 1)

        data_bus = self.init_bus()
        connector = GenericConnector(data_bus)
        data_bus.setup(lambda r: None)
        time.sleep(0.5)

        while self.running:
            try:
                temp = self.env_data.get("temperature", 0)
                humi = self.env_data.get("humidity", 0)
                light = self.env_data.get("light", 0)

                # 清屏
                observer = connector.sendLedClearScreen(addr, lambda d: None)
                DataObserver.wait(observer, timeout=1)

                # 显示温度
                text = f"Temp: {temp}C"
                observer = connector.sendLedScreenText(
                    addr, 0, 0, 16, 1, text, lambda d: None)
                DataObserver.wait(observer, timeout=1)

                # 显示湿度
                text = f"Humi: {humi}%"
                observer = connector.sendLedScreenText(
                    addr, 0, 20, 16, 1, text, lambda d: None)
                DataObserver.wait(observer, timeout=1)

                # 显示光照
                text = f"Light: {light}lux"
                observer = connector.sendLedScreenText(
                    addr, 0, 40, 16, 1, text, lambda d: None)
                DataObserver.wait(observer, timeout=1)

            except Exception as e:
                print(f"[LED] 显示异常: {e}")

            time.sleep(interval)

    def stop(self):
        self.running = False
        print("[System] 系统已停止")


if __name__ == "__main__":
    system = HomeEnvironmentMonitor("config.json")
    system.start()
