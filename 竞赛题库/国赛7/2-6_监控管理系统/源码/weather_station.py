"""
GZ038 题6 - 广场气象系统
百叶箱传感器 → 云平台API → matplotlib 实时图表
每10秒读取一次温湿度，绘制"温度-时间"和"湿度-时间"折线图
严格对齐官方 SDK API
"""
import json
import time
import datetime
import threading
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from nlecloud_client import NLECloudClient


class WeatherStation:
    """广场气象系统"""

    def __init__(self, config_file="config.json"):
        with open(config_file, "r", encoding="utf-8") as f:
            self.config = json.load(f)

        cloud = self.config["cloud"]
        self.client = NLECloudClient(f"http://{cloud['host']}:{cloud['port']}/")
        self.client.sign_in(cloud["account"], cloud["password"])
        self.device_id = str(cloud["device_id"])

        self.times = []
        self.temps = []
        self.humis = []
        self.running = False

    def read_sensors(self):
        """读取百叶箱温湿度"""
        tags = self.config["api_tags"]

        temp_resp = self.client.get_sensor(self.device_id, tags["temperature"])
        humi_resp = self.client.get_sensor(self.device_id, tags["humidity"])

        temp = temp_resp.get("ResultObj", {}).get("Value") if temp_resp else None
        humi = humi_resp.get("ResultObj", {}).get("Value") if humi_resp else None

        now = datetime.datetime.now().strftime("%H:%M:%S")
        return now, temp, humi

    def start(self):
        self.running = True
        threading.Thread(target=self._data_loop, daemon=True).start()

        try:
            import matplotlib
            matplotlib.use('TkAgg')
            import matplotlib.pyplot as plt
            import matplotlib.animation as animation

            fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6))
            fig.suptitle("广场气象系统", fontsize=14)

            def animate(frame):
                if self.times:
                    ax1.clear()
                    ax2.clear()
                    ax1.plot(self.times, self.temps, 'r-o', markersize=3, label='温度')
                    ax1.set_ylabel('温度 (°C)')
                    ax1.set_title('温度-时间变化图')
                    ax1.grid(True)
                    ax1.legend()
                    ax2.plot(self.times, self.humis, 'b-s', markersize=3, label='湿度')
                    ax2.set_ylabel('湿度 (%)')
                    ax2.set_xlabel('时间')
                    ax2.set_title('湿度-时间变化图')
                    ax2.grid(True)
                    ax2.legend()
                    plt.tight_layout()

            ani = animation.FuncAnimation(fig, animate, interval=2000)
            plt.tight_layout()
            plt.show()
        except ImportError:
            print("[System] matplotlib 未安装，仅显示文本数据")
            while self.running:
                if self.times:
                    print(f"[{self.times[-1]}] 温度={self.temps[-1]}°C 湿度={self.humis[-1]}%")
                time.sleep(10)

    def _data_loop(self):
        interval = self.config.get("interval", 10)
        while self.running:
            try:
                now, temp, humi = self.read_sensors()
                if temp is not None and humi is not None:
                    self.times.append(now)
                    self.temps.append(float(temp))
                    self.humis.append(float(humi))
                    if len(self.times) > 100:
                        self.times = self.times[-100:]
                        self.temps = self.temps[-100:]
                        self.humis = self.humis[-100:]
                    print(f"[{now}] 温度={temp}°C 湿度={humi}%")
            except Exception as e:
                print(f"[Error] {e}")
            time.sleep(interval)


if __name__ == "__main__":
    station = WeatherStation("config.json")
    station.start()
