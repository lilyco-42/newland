# -*- coding: utf-8 -*-
"""套8 2-7 水质监测系统 - Python 3.6 兼容"""
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


class WaterQualityMonitor:
    """水质监测系统"""
    # 水质标准
    PH_NORMAL = (6.5, 8.5)       # pH正常范围
    TURB_NORMAL = (0, 5.0)       # 浊度 NTU
    DO_NORMAL = (5.0, 14.0)      # 溶解氧 mg/L
    TEMP_NORMAL = (5, 35)        # 水温

    def __init__(self):
        self.data = {
            "ph": 7.2,
            "turbidity": 2.5,
            "dissolved_o2": 8.0,
            "water_temp": 22.0,
            "conductivity": 350,
            "orp": 400,
        }
        self.cloud = None

    def connect_cloud(self, account, password):
        if requests:
            self.cloud = NLECloudClient()
            if self.cloud.login(account, password):
                print("[OK] 云平台已连接")
                return True
        return False

    def evaluate_quality(self):
        """水质评估"""
        score = 100
        issues = []
        d = self.data

        if d["ph"] < self.PH_NORMAL[0]:
            score -= 15
            issues.append("pH偏低: %.1f" % d["ph"])
        elif d["ph"] > self.PH_NORMAL[1]:
            score -= 15
            issues.append("pH偏高: %.1f" % d["ph"])

        if d["turbidity"] > self.TURB_NORMAL[1]:
            score -= 20
            issues.append("浊度超标: %.1f NTU" % d["turbidity"])

        if d["dissolved_o2"] < self.DO_NORMAL[0]:
            score -= 25
            issues.append("溶解氧不足: %.1f mg/L" % d["dissolved_o2"])

        if d["water_temp"] < self.TEMP_NORMAL[0]:
            score -= 10
            issues.append("水温过低: %.1f C" % d["water_temp"])
        elif d["water_temp"] > self.TEMP_NORMAL[1]:
            score -= 10
            issues.append("水温过高: %.1f C" % d["water_temp"])

        if score >= 80:
            level = "优"
        elif score >= 60:
            level = "良"
        elif score >= 40:
            level = "中"
        else:
            level = "差"
        return score, level, issues

    def upload_to_cloud(self, device_id=1):
        if not self.cloud:
            return
        for tag, val in self.data.items():
            self.cloud.upload_data(device_id, tag, val)
        print("[UPLOAD] 水质数据已上传")

    def show_report(self):
        score, level, issues = self.evaluate_quality()
        print("\n" + "=" * 50)
        print("  水质监测报告")
        print("=" * 50)
        print("  pH值:      %.1f      (正常: %.1f~%.1f)" % (
            self.data["ph"], self.PH_NORMAL[0], self.PH_NORMAL[1]))
        print("  浊度:      %.1f NTU  (正常: <%.1f)" % (
            self.data["turbidity"], self.TURB_NORMAL[1]))
        print("  溶解氧:    %.1f mg/L (正常: %.1f~%.1f)" % (
            self.data["dissolved_o2"], self.DO_NORMAL[0], self.DO_NORMAL[1]))
        print("  水温:      %.1f C    (正常: %d~%d)" % (
            self.data["water_temp"], self.TEMP_NORMAL[0], self.TEMP_NORMAL[1]))
        print("  电导率:    %d uS/cm" % self.data["conductivity"])
        print("  ORP:       %d mV" % self.data["orp"])
        print("-" * 50)
        print("  综合评分:  %d 分  等级: %s" % (score, level))
        if issues:
            print("  问题:")
            for i in issues:
                print("    - %s" % i)
        print("=" * 50)

    def run(self, interval=15):
        print("水质监测系统启动...")
        while True:
            self.show_report()
            self.upload_to_cloud()
            time.sleep(interval)


if __name__ == "__main__":
    wq = WaterQualityMonitor()
    wq.connect_cloud("13329262958", "qwe123456789")
    wq.run()
