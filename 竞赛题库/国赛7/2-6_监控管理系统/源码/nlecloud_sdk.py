"""
新大陆 NLECloud Python SDK (PyQt5 版)
对齐官方 Android-SDK / JS-SDK / CSharp-SDK 全部 API
参考: http://www.nlecloud.com/doc/resources_sdk.shtml
GitHub: github.com/newlandedu

官方 SDK 仓库 (无 Python 版):
  Android-SDK: github.com/newlandedu/Android-SDK
  JS-SDK:      github.com/newlandedu/JS-SDK
  CSharp-SDK:  github.com/newlandedu/CSharp-SDK
  JAVA-SDK:    github.com/newlandedu/JAVA-SDK
  PHP-SDK:     github.com/newlandedu/PHP-SDK

本 SDK 补齐 Python 生态, API 完全对齐官方接口
"""
import json
import http.client
from urllib.parse import urlparse


class NLECloudAPI:
    """
    新大陆云平台 Python SDK
    对齐官方 ApiService.java / nlecloud-sdk.js 全部接口
    """

    def __init__(self, base_url="http://192.168.0.138/"):
        if not base_url.endswith("/"):
            base_url += "/"
        parsed = urlparse(base_url)
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.base_url = base_url
        self.access_token = None

    # ============ 用户 ============

    def user_login(self, account, password):
        """POST Users/Login"""
        body = json.dumps({"Account": account, "Password": password})
        resp = self._post("Users/Login", body)
        if resp and resp.get("Status") == 0:
            self.access_token = resp["ResultObj"]["AccessToken"]
            return resp["ResultObj"]
        return None

    # ============ 项目 ============

    def get_project(self, project_id):
        """GET Projects/{projectId}"""
        return self._get(f"Projects/{project_id}")

    def get_projects(self, keyword=None, project_tag=None, network_kind=None,
                     page_size=20, start_date=None, end_date=None, page_index=1):
        """GET Projects"""
        params = []
        if keyword: params.append(f"Keyword={keyword}")
        if project_tag: params.append(f"ProjectTag={project_tag}")
        if network_kind: params.append(f"NetWorkKind={network_kind}")
        if start_date: params.append(f"StartDate={start_date}")
        if end_date: params.append(f"EndDate={end_date}")
        params.append(f"PageSize={page_size}")
        params.append(f"PageIndex={page_index}")
        return self._get(f"Projects?{'&'.join(params)}")

    def get_all_sensors(self, project_id):
        """GET Projects/{projectId}/Sensors"""
        return self._get(f"Projects/{project_id}/Sensors")

    # ============ 设备 ============

    def get_devices_datas(self, device_ids):
        """GET Devices/Datas?devIds=1,2,3"""
        return self._get(f"Devices/Datas?devIds={device_ids}")

    def get_devices_status(self, device_ids):
        """GET Devices/Status?devIds=1,2,3"""
        return self._get(f"Devices/Status?devIds={device_ids}")

    def get_device_info(self, device_id):
        """GET Devices/{deviceId}"""
        return self._get(f"Devices/{device_id}")

    def get_devices(self, keyword=None, device_ids=None, tag=None,
                    is_online=None, is_share=None, project_keyword=None,
                    page_size=20, start_date=None, end_date=None, page_index=1):
        """GET Devices"""
        params = []
        if keyword: params.append(f"Keyword={keyword}")
        if device_ids: params.append(f"DeviceIds={device_ids}")
        if tag: params.append(f"Tag={tag}")
        if is_online: params.append(f"IsOnline={is_online}")
        if is_share: params.append(f"IsShare={is_share}")
        if project_keyword: params.append(f"ProjectKeyWord={project_keyword}")
        if start_date: params.append(f"StartDate={start_date}")
        if end_date: params.append(f"EndDate={end_date}")
        params.append(f"PageSize={page_size}")
        params.append(f"PageIndex={page_index}")
        return self._get(f"Devices?{'&'.join(params)}")

    def post_add_device(self, device_info):
        """POST Devices"""
        return self._post("Devices", json.dumps(device_info))

    def update_device(self, device_id, device_info):
        """PUT Devices/{deviceId}"""
        return self._put(f"Devices/{device_id}", json.dumps(device_info))

    def delete_device(self, device_id):
        """DELETE Devices/{deviceId}"""
        return self._delete(f"Devices/{device_id}")

    # ============ 传感器/执行器 ============

    def get_sensor(self, device_id, api_tag):
        """GET devices/{deviceId}/Sensors/{apiTag}"""
        return self._get(f"devices/{device_id}/Sensors/{api_tag}")

    def get_sensors(self, device_id, api_tags=None):
        """GET devices/{deviceId}/Sensors?apiTags=tag1,tag2"""
        url = f"devices/{device_id}/Sensors"
        if api_tags:
            url += f"?apiTags={api_tags}"
        return self._get(url)

    def add_sensor(self, device_id, device_element):
        """POST devices/{deviceId}/Sensors"""
        return self._post(f"devices/{device_id}/Sensors", json.dumps(device_element))

    def update_sensor(self, device_id, api_tag, device_element):
        """PUT devices/{deviceId}/Sensors/{apiTag}"""
        return self._put(f"devices/{device_id}/Sensors/{api_tag}", json.dumps(device_element))

    def delete_device_element(self, device_id, api_tag):
        """DELETE devices/{deviceId}/Sensors/{apiTag}"""
        return self._delete(f"devices/{device_id}/Sensors/{api_tag}")

    # ============ 传感数据 ============

    def add_sensor_data(self, device_id, api_tag, value, record_time=None):
        """POST devices/{deviceId}/Datas"""
        datas = [{"ApiTag": api_tag,
                  "Points": [{"Value": str(value), "RecordTime": record_time or ""}]}]
        return self._post(f"devices/{device_id}/Datas", json.dumps({"Datas": datas}))

    def get_sensor_data(self, device_id, api_tags, method=None, time_ago=None,
                        start_date=None, end_date=None, sort="DESC",
                        page_size=20, page_index=1):
        """GET devices/{deviceId}/Datas"""
        params = [f"ApiTags={api_tags}"]
        if method: params.append(f"Method={method}")
        if time_ago: params.append(f"TimeAgo={time_ago}")
        if start_date: params.append(f"StartDate={start_date}")
        if end_date: params.append(f"EndDate={end_date}")
        params.append(f"Sort={sort}")
        params.append(f"PageSize={page_size}")
        params.append(f"PageIndex={page_index}")
        return self._get(f"devices/{device_id}/Datas?{'&'.join(params)}")

    def get_sensor_data_grouping(self, device_id, api_tags, group_by="2",
                                  func="MAX", start_date=None, end_date=None):
        """GET devices/{deviceId}/Datas/Grouping"""
        params = [f"ApiTags={api_tags}", f"GroupBy={group_by}", f"Func={func}"]
        if start_date: params.append(f"StartDate={start_date}")
        if end_date: params.append(f"EndDate={end_date}")
        return self._get(f"devices/{device_id}/Datas/Grouping?{'&'.join(params)}")

    # ============ 控制 ============

    def control(self, device_id, api_tag, data):
        """POST Cmds?deviceId={deviceId}&apiTag={apiTag}"""
        return self._post(f"Cmds?deviceId={device_id}&apiTag={api_tag}",
                         json.dumps({"Data": data}))

    # ============ HTTP 封装 ============

    def _get(self, path):
        return self._request("GET", path)

    def _post(self, path, body=None):
        return self._request("POST", path, body)

    def _put(self, path, body=None):
        return self._request("PUT", path, body)

    def _delete(self, path):
        return self._request("DELETE", path)

    def _request(self, method, path, body=None):
        conn = http.client.HTTPConnection(self.host, self.port)
        headers = {"Content-Type": "application/json"}
        if self.access_token:
            headers["AccessToken"] = self.access_token
        try:
            conn.request(method, path, body=body, headers=headers)
            resp = conn.getresponse()
            data = resp.read().decode("utf-8")
            conn.close()
            return json.loads(data)
        except Exception:
            conn.close()
            return None
