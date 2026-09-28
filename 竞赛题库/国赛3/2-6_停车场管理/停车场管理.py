# -*- coding: utf-8 -*-
"""套3 2-6 停车场管理 - Python 3.6 兼容"""
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


class ParkingManager:
    """智能停车场管理"""
    TOTAL_SPACES = 200

    def __init__(self):
        self.spaces = {}  # plate -> enter_time
        self.cloud = None

    def connect_cloud(self, account, password):
        if requests:
            self.cloud = NLECloudClient()
            if self.cloud.login(account, password):
                print("[OK] 云平台已连接")
                return True
        return False

    def car_enter(self, plate):
        if len(self.spaces) >= self.TOTAL_SPACES:
            print("[ERR] 车位已满!")
            return False
        self.spaces[plate] = time.time()
        print("[OK] %s 已入场  当前占用: %d/%d" % (
            plate, len(self.spaces), self.TOTAL_SPACES))
        return True

    def car_exit(self, plate):
        if plate not in self.spaces:
            print("[ERR] 未找到车辆: %s" % plate)
            return None
        enter_time = self.spaces.pop(plate)
        duration = time.time() - enter_time
        hours = max(1, int(duration / 3600))
        fee = hours * 5  # 5元/小时
        print("[OK] %s 已出场  停车%d小时  费用: %d元" % (plate, hours, fee))
        return fee

    def show_status(self):
        used = len(self.spaces)
        free = self.TOTAL_SPACES - used
        print("\n" + "=" * 40)
        print("  智能停车场管理")
        print("=" * 40)
        print("  总车位: %d  已用: %d  空闲: %d" % (
            self.TOTAL_SPACES, used, free))
        print("-" * 40)
        if self.spaces:
            for plate, t in self.spaces.items():
                mins = int((time.time() - t) / 60)
                print("  %-12s  已停 %d 分钟" % (plate, mins))
        else:
            print("  （无车辆）")
        print("=" * 40)

    def upload_status(self, device_id=1):
        if not self.cloud:
            return
        self.cloud.upload_data(device_id, "used_spaces", len(self.spaces))
        self.cloud.upload_data(device_id, "free_spaces",
                               self.TOTAL_SPACES - len(self.spaces))

    def interactive(self):
        print("智能停车场管理系统启动")
        while True:
            print("\n1.车辆入场  2.车辆出场  3.查看状态  4.同步云  0.退出")
            choice = input("请选择: ").strip()
            if choice == "1":
                plate = input("车牌号: ").strip()
                self.car_enter(plate)
            elif choice == "2":
                plate = input("车牌号: ").strip()
                self.car_exit(plate)
            elif choice == "3":
                self.show_status()
            elif choice == "4":
                self.upload_status()
                print("[OK] 已同步")
            elif choice == "0":
                break


if __name__ == "__main__":
    pm = ParkingManager()
    pm.connect_cloud("13329262958", "qwe123456789")
    pm.interactive()
