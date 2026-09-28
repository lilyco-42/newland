"""
GZ038 题7 - 客厅环境监控系统升级
温湿度+光照+人体红外 → 云平台API → Python表格显示
每30秒采集一次，光照控制白色常亮灯
严格对齐官方 SDK API
"""
import json
import time
import datetime
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from nlecloud_client import NLECloudClient


class RoomEnvironmentMonitor:
    def __init__(self, config_file="config.json"):
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        cloud = self.config["cloud"]
        self.client = NLECloudClient(f"http://{cloud['host']}:{cloud['port']}/")
        self.client.sign_in(cloud["account"], cloud["password"])
        self.device_id = str(cloud["device_id"])
        self.data = {}

    def read_all(self):
        tags = self.config["api_tags"]

        temp_resp = self.client.get_sensor(self.device_id, tags["temperature"])
        humi_resp = self.client.get_sensor(self.device_id, tags["humidity"])
        light_resp = self.client.get_sensor(self.device_id, tags["light"])
        body_resp = self.client.get_sensor(self.device_id, tags["body"])

        self.data["temperature"] = temp_resp.get("ResultObj", {}).get("Value") if temp_resp else "--"
        self.data["humidity"] = humi_resp.get("ResultObj", {}).get("Value") if humi_resp else "--"
        self.data["light"] = light_resp.get("ResultObj", {}).get("Value") if light_resp else "--"
        body_val = body_resp.get("ResultObj", {}).get("Value") if body_resp else "0"
        self.data["body"] = "有人" if str(body_val) == "1" else "无人"

        light_val = float(self.data.get("light", 0) or 0)
        if light_val > 100:
            self.client.control(self.device_id, tags["led"], "0")
            self.data["led"] = "Off"
        else:
            self.client.control(self.device_id, tags["led"], "1")
            self.data["led"] = "On"

    def display_table(self):
        temp = self.data.get("temperature", "--")
        humi = self.data.get("humidity", "--")
        light = self.data.get("light", "--")
        body = self.data.get("body", "--")
        led = self.data.get("led", "--")

        print("\033[2J\033[H")
        print("=" * 40)
        print("      客厅环境监控系统")
        print("=" * 40)
        print(f"  温度℃          {temp}")
        print(f"  湿度%          {humi}")
        print(f"  光照度lux      {light}")
        print(f"  红外对射       {body}")
        print(f"  常亮指示灯-白  {led}")
        print("=" * 40)
        now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"  更新时间: {now}")

    def start(self):
        interval = self.config.get("interval", 30)
        print("[System] 客厅环境监控系统启动")
        print(f"[System] 每 {interval} 秒采集一次")
        try:
            while True:
                self.read_all()
                self.display_table()
                time.sleep(interval)
        except KeyboardInterrupt:
            print("\n[System] 已停止")


if __name__ == "__main__":
    monitor = RoomEnvironmentMonitor("config.json")
    monitor.start()
