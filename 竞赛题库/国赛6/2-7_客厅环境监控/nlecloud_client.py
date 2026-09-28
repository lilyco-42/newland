"""
新大陆云平台 API 官方 SDK (Python 版)
严格对齐 Android-SDK / JS-SDK / CSharp-SDK 官方接口
API 文档: http://www.nlecloud.com/doc/resources_sdk.shtml
"""
import json
import http.client


class NLECloudClient:
    """
    新大陆云平台 Python SDK
    对齐官方 Android-SDK NetWorkBusiness.java + ApiService.java
    """

    def __init__(self, base_url="http://192.168.0.138/"):
        """
        初始化客户端
        :param base_url: 云平台地址, 格式 http://{ip}:{port}/
        """
        if not base_url.endswith("/"):
            base_url += "/"
        from urllib.parse import urlparse
        parsed = urlparse(base_url)
        self.host = parsed.hostname
        self.port = parsed.port or 80
        self.base_url = base_url
        self.access_token = None

    def sign_in(self, account, password):
        """
        用户登录 (对齐 NetWorkBusiness.signIn)
        POST Users/Login
        """
        body = json.dumps({
            "Account": account,
            "Password": password
        })
        resp = self._post("Users/Login", body)
        if resp and resp.get("Status") == 0:
            self.access_token = resp["ResultObj"]["AccessToken"]
            return resp["ResultObj"]
        return None

    def get_project(self, project_id):
        """
        查询单个项目 (对齐 NetWorkBusiness.getProject)
        GET Projects/{projectId}
        """
        return self._get(f"Projects/{project_id}")

    def get_projects(self, keyword=None, page_size=20, page_index=1):
        """
        模糊查询项目 (对齐 NetWorkBusiness.getProjects)
        GET Projects
        """
        params = []
        if keyword:
            params.append(f"Keyword={keyword}")
        params.append(f"PageSize={page_size}")
        params.append(f"PageIndex={page_index}")
        query = "&".join(params)
        return self._get(f"Projects?{query}")

    def get_all_sensors(self, project_id):
        """
        查询项目所有传感器 (对齐 NetWorkBusiness.getAllSensors)
        GET Projects/{projectId}/Sensors
        """
        return self._get(f"Projects/{project_id}/Sensors")

    def get_devices_datas(self, device_ids):
        """
        批量查询设备最新数据 (对齐 NetWorkBusiness.getDevicesDatas)
        GET Devices/Datas?devIds=1,2,3
        """
        return self._get(f"Devices/Datas?devIds={device_ids}")

    def get_device_info(self, device_id):
        """
        查询单个设备 (对齐 NetWorkBusiness.getDeviceInfo)
        GET Devices/{deviceId}
        """
        return self._get(f"Devices/{device_id}")

    def get_sensor(self, device_id, api_tag):
        """
        查询单个传感器 (对齐 NetWorkBusiness.getSensor)
        GET devices/{deviceId}/Sensors/{apiTag}
        """
        return self._get(f"devices/{device_id}/Sensors/{api_tag}")

    def get_sensors(self, device_id, api_tags=None):
        """
        模糊查询传感器 (对齐 NetWorkBusiness.getSensors)
        GET devices/{deviceId}/Sensors?apiTags=tag1,tag2
        """
        url = f"devices/{device_id}/Sensors"
        if api_tags:
            url += f"?apiTags={api_tags}"
        return self._get(url)

    def add_sensor_data(self, device_id, api_tag, value, record_time=None):
        """
        新增传感数据 (对齐 NetWorkBusiness.addSensorData)
        POST devices/{deviceId}/Datas
        """
        datas = [{
            "ApiTag": api_tag,
            "Points": [{"Value": str(value), "RecordTime": record_time or ""}]
        }]
        body = json.dumps({"Datas": datas})
        return self._post(f"devices/{device_id}/Datas", body)

    def get_sensor_data(self, device_id, api_tags, method=None, time_ago=None,
                        start_date=None, end_date=None, sort="DESC",
                        page_size=20, page_index=1):
        """
        查询传感数据 (对齐 NetWorkBusiness.getSensorData)
        GET devices/{deviceId}/Datas
        """
        params = [f"ApiTags={api_tags}"]
        if method:
            params.append(f"Method={method}")
        if time_ago:
            params.append(f"TimeAgo={time_ago}")
        if start_date:
            params.append(f"StartDate={start_date}")
        if end_date:
            params.append(f"EndDate={end_date}")
        params.append(f"Sort={sort}")
        params.append(f"PageSize={page_size}")
        params.append(f"PageIndex={page_index}")
        query = "&".join(params)
        return self._get(f"devices/{device_id}/Datas?{query}")

    def control(self, device_id, api_tag, data):
        """
        发送命令/控制设备 (对齐 NetWorkBusiness.control)
        POST Cmds?deviceId={deviceId}&apiTag={apiTag}
        body: data (开关=1/0, 亮度=0~254, RGB=2~239)
        """
        body = json.dumps({"Data": data})
        return self._post(f"Cmds?deviceId={device_id}&apiTag={api_tag}", body)

    def _get(self, path):
        return self._request("GET", path)

    def _post(self, path, body=None):
        return self._request("POST", path, body)

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
            result = json.loads(data)
            return result
        except Exception as e:
            conn.close()
            return None
