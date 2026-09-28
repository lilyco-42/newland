# -*- coding: utf-8 -*-
"""
物联网云服务系统(NL-Cloud / nlecloud) RESTful API 客户端模块

接口说明(基于新大陆物联网云平台 RESTful API):
    1. POST  {base}/users/login             用户登录, 返回 AccessToken
    2. GET   {base}/Devices                 模糊查询用户设备
    3. GET   {base}/Devices/Datas?devIds=.. 批量查询设备内全部传感器最新数据
    4. GET   {base}/Devices/{id}            查询单个设备(含传感器最新值)

所有接口(除 users/login 外)均需在请求头携带 AccessToken。
"""

import json
import random
import time
from datetime import datetime

import requests

DEFAULT_TIMEOUT = 10


def _get(data, key):
    """大小写不敏感地获取 JSON 字段值。"""
    if isinstance(data, dict):
        for k, v in data.items():
            if k.lower() == key.lower():
                return v
    return None


class CloudError(Exception):
    """云服务调用异常。"""


class NLECloudClient(object):
    """物联网云服务系统客户端。"""

    def __init__(self, base_url, username=None, password=None):
        self.base_url = (base_url or "").rstrip("/")
        self.username = username
        self.password = password
        self.token = None
        self.user = None
        self.session = requests.Session()
        self.last_error = ""

    # ------------------------------------------------------------------ #
    # 登录
    # ------------------------------------------------------------------ #
    def login(self, username=None, password=None):
        """登录云服务系统, 成功返回 True, 失败返回 False。"""
        if username is not None:
            self.username = username
        if password is not None:
            self.password = password

        if not self.base_url:
            self.last_error = "未配置云服务地址"
            return False, self.last_error
        if not self.username or not self.password:
            self.last_error = "用户名或密码不能为空"
            return False, self.last_error

        url = self.base_url + "/users/login"
        payload = {
            "Account": self.username,
            "Password": self.password,
            "IsRememberMe": True,
        }
        try:
            resp = self.session.post(
                url, json=payload, timeout=DEFAULT_TIMEOUT
            )
            data = resp.json()
        except Exception as exc:
            self.last_error = "登录请求失败: %s" % exc
            return False, self.last_error

        result = _get(data, "ResultObj")
        token = _get(result, "AccessToken") if isinstance(result, dict) else None
        if token:
            self.token = token
            self.user = result
            self.session.headers["AccessToken"] = self.token
            user_name = _get(result, "UserName") or self.username
            return True, "登录成功 - %s" % user_name

        msg = _get(data, "Msg") or "登录失败"
        self.last_error = str(msg)
        return False, self.last_error

    # ------------------------------------------------------------------ #
    # 设备
    # ------------------------------------------------------------------ #
    def query_devices(self, project_keyword=None, keyword=None, page_size=100):
        """模糊查询设备列表。"""
        self._ensure_token()
        params = {"PageSize": page_size, "PageIndex": 1}
        if project_keyword:
            params["ProjectKeyWord"] = project_keyword
        if keyword:
            params["Keyword"] = keyword
        url = self.base_url + "/Devices"
        resp = self.session.get(url, params=params, timeout=DEFAULT_TIMEOUT)
        data = resp.json()
        result = _get(data, "ResultObj") or {}
        page_set = _get(result, "PageSet") or []
        if not page_set and isinstance(result, list):
            page_set = result
        return page_set or []

    def get_device(self, device_id):
        """查询单个设备(含各传感器最新数据)。"""
        self._ensure_token()
        url = "%s/Devices/%s" % (self.base_url, device_id)
        resp = self.session.get(url, timeout=DEFAULT_TIMEOUT)
        data = resp.json()
        return _get(data, "ResultObj") or {}

    # ------------------------------------------------------------------ #
    # 传感数据
    # ------------------------------------------------------------------ #
    def get_latest_datas(self, dev_ids):
        """批量查询设备传感器最新数据。"""
        self._ensure_token()
        ids = []
        for d in dev_ids:
            if d not in ids:
                ids.append(d)
        if not ids:
            return []
        url = self.base_url + "/Devices/Datas"
        resp = self.session.get(
            url, params={"devIds": ",".join(str(i) for i in ids)}, timeout=DEFAULT_TIMEOUT
        )
        data = resp.json()
        result = _get(data, "ResultObj") or []
        return result or []

    def fetch_sensor(self, tags, device_ids=None):
        """抓取指定传感器标识的最新数据。

        :param tags: 传感器标识集合
        :param device_ids: 可选的设备ID列表
        :return: dict {tag: {"value":..., "time":..., "device":..., "device_id":...}}
        """
        wanted = set(tags)
        result = {}
        dev_ids = []
        devices = []
        if device_ids:
            dev_ids = [int(x) for x in device_ids]
            devices = [{"DeviceID": i} for i in dev_ids]
        else:
            devices = self.query_devices()
            if devices:
                dev_ids = [
                    _get(d, "DeviceID") for d in devices if _get(d, "DeviceID") is not None
                ]
        devs = self.get_latest_datas(dev_ids) if dev_ids else []

        if not devs:
            devs = []
            for d in devices:
                dev = self.get_device(_get(d, "DeviceID"))
                if dev:
                    devs.append(dev)

        for dev in devs:
            device_id = _get(dev, "DeviceID")
            device_name = _get(dev, "Name")
            for sensor in _get(dev, "Datas") or []:
                tag = _get(sensor, "ApiTag")
                if tag in wanted:
                    result[tag] = {
                        "value": _get(sensor, "Value"),
                        "time": _get(sensor, "RecordTime"),
                        "device": device_name,
                        "device_id": device_id,
                    }
                    wanted.discard(tag)
        return result

    def list_all_tags(self, device_ids=None):
        """列出账号下设备的所有传感器标识(ApiTag)及最新值。"""
        ids = []
        if device_ids:
            ids = [int(x) for x in device_ids]
        else:
            devices = self.query_devices()
            if devices:
                ids = [
                    _get(d, "DeviceID") for d in devices if _get(d, "DeviceID") is not None
                ]
        devs = self.get_latest_datas(ids) if ids else []
        if not devs:
            devs = []
            for i in ids:
                dev = self.get_device(i)
                if dev:
                    devs.append(dev)
        out = {}
        for dev in devs:
            device_id = _get(dev, "DeviceID")
            device_name = _get(dev, "Name")
            for sensor in _get(dev, "Datas") or []:
                tag = _get(sensor, "ApiTag")
                if not tag:
                    continue
                out[tag] = {
                    "value": _get(sensor, "Value"),
                    "time": _get(sensor, "RecordTime"),
                    "device": device_name,
                    "device_id": device_id,
                }
        return out

    # ------------------------------------------------------------------ #
    # 命令下发(执行器控制)
    # ------------------------------------------------------------------ #
    def send_command(self, device_id, api_tag, value):
        """向执行器下发指令。返回 (ok, msg)。"""
        self._ensure_token()
        url = "%s/Devices/%s/Cmds" % (self.base_url, device_id)
        payload = {"apikey": self.token, "apitag": api_tag, "value": value}
        try:
            resp = self.session.post(
                url, json=payload, timeout=DEFAULT_TIMEOUT
            )
            data = resp.json()
        except Exception as exc:
            return False, "指令发送失败: %s" % exc
        status_code = _get(data, "StatusCode")
        if status_code in (1, 2):
            return True, _get(data, "Msg") or "发送成功"
        return False, _get(data, "Msg") or "发送失败"

    # ------------------------------------------------------------------ #
    # 内部
    # ------------------------------------------------------------------ #
    def _ensure_token(self):
        if not self.token:
            raise CloudError("尚未登录, 请先调用 login()")


def save_config(path, cfg):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def load_config(path, default):
    try:
        with open(path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        for k, v in default.items():
            cfg.setdefault(k, v)
        return cfg
    except Exception:
        return dict(default)


def normalize_number(value, default=None):
    """把任意值尽量转成浮点数, 失败返回 default。"""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    try:
        return float(text)
    except ValueError:
        return default


class SimulatedCloudClient(object):
    """模拟测试客户端。"""

    _PROFILES = {
        "m_temp": (27.0, 1.2),
        "m_hum": (60.0, 3.0),
        "m_light": (100.0, 30.0),
        "m_louverbox_temp": (26.5, 1.0),
        "m_louverbox_hum": (62.0, 3.0),
        "m_light_curtain": (0.5, 0.5),
        "m_steady_white": (1.0, 0.0),
    }

    def __init__(self, base_url="", username="demo", password="demo"):
        self.base_url = base_url
        self.username = username
        self.password = password
        self.token = "SIMULATED-TOKEN"
        self.session = requests.Session()
        self.last_error = ""
        self._state = {}
        self._body_person = False
        self._tick = 0

    def login(self, username=None, password=None):
        if username is not None:
            self.username = username
        if password is not None:
            self.password = password
        return True, "模拟模式登录成功(演示数据)"

    def fetch_sensor(self, tags, device_ids=None):
        result = {}
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        for tag in tags:
            result[tag] = {
                "value": self._next_value(tag),
                "time": now,
                "device": "模拟设备",
                "device_id": 1,
            }
        return result

    def query_devices(self):
        return [{"DeviceID": 1, "Name": "模拟网关", "Tag": "sim_gw"}]

    def send_command(self, device_id, api_tag, value):
        return True, "模拟下发成功"

    def _next_value(self, tag):
        center, amp = self._PROFILES.get(tag, (50.0, 5.0))
        self._tick += 1
        if tag.endswith("curtain") or tag.endswith("body"):
            if self._tick % 6 == 0:
                self._body_person = not self._body_person
            return 1 if self._body_person else 0
        if tag.endswith("light") and "curtain" not in tag:
            value = self._state.get(tag)
            if value is None:
                value = 95.0
            value = max(20.0, min(180.0, value + (random.uniform(-amp, amp))))
            self._state[tag] = value
            return round(value, 1)
        value = self._state.get(tag)
        if value is None:
            value = center
        value += random.uniform(-amp, amp) * 0.4
        value = max(center - amp * 2.0, min(center + amp * 2.0, value))
        self._state[tag] = value
        return round(value, 1)


def create_client(mode, base_url, username, password):
    """按模式创建客户端。mode: cloud(真实云服务) / demo(模拟测试)。"""
    if mode == "demo":
        return SimulatedCloudClient(base_url, username, password)
    return NLECloudClient(base_url, username, password)