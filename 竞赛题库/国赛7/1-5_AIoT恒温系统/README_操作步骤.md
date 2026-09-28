# GZ038 子任务1-5：AIoT 恒温系统 —— 完整操作步骤（A-14）

> 对应赛题：GZ038 物联网应用开发赛项 第6套 A-14（子任务1-5 AIoT 系统的配置与使用）
> 任务：温湿度传感器 + 风扇均使用 LoRaWAN 通讯；温度 >28℃ 时自动启动风扇降温；完成 ChirpStack 通讯服务配置、TB 仪表板配置、冻库改造（虚拟仿真）。
> 每步对应同目录下的截图文件（文件名 = 步骤编号）。

---

## 0. 环境与账号

| 项目 | 内容 |
|---|---|
| 平台 | UUSIMA 智慧教学实验平台 https://aiot.nlecloud.com/ |
| 账号 | 14026070702 / 123456（学生权限） |
| ChirpStack Web | http://124.70.206.170:20805（admin / admin） |
| ThingsBoard | tb.uusima.com（随平台免密登录） |
| 涉及系统 | ① ChirpStack（LoRaWAN 通讯服务）② ThingsBoard（仪表板）③ 工程虚拟仿真（设备搭建） |

---

## 第1步 登录 UUSIMA 平台并进入实验环境

1. 浏览器打开 https://aiot.nlecloud.com/，跳转统一认证登录页。
2. 输入账号 14026070702 / 密码 123456 登录（Keycloak，client aiot-app）。
3. 登录后进入课程大厅，打开课程「GZ038 物联网应用开发赛项」。
4. 从课程中选择实验环境（含 平台型 ThingsBoard / 容器型终端 / 平台型虚拟仿真 三个入口）。

---

## 第2步 部署 ChirpStack LoRaWAN 通讯服务（A-14-2）

### 2.1 在终端（容器）下载并启动 ChirpStack

```bash
cd /root
wget https://newland-test.obs.cn-east-3.myhuaweicloud.com/student/chirpstack-docker-cn.tgz
tar zxvf chirpstack-docker-cn.tgz
cd chirpstack-docker-cn
docker-compose up -d          # 9 个容器全部 Up
```

> 掉线后重启：`cd /root/chirpstack-docker-cn && docker-compose up -d`

### 2.2 创建网络服务器（截图 02_网络服务器配置.png）

ChirpStack Web → 左侧「网络服务」→ 添加：
- 名称：`lorawan_default`
- 服务：`chirpstack-network-server:8000`

### 2.3 创建服务配置文件（截图 03_服务配置文件.png）

左侧「服务配置文件」→ 创建：
- 名称：`service_profile`，绑定网络服务器 `lorawan_default`

### 2.4 创建设备配置文件（截图 04_设备配置文件.png、05_设备编解码配置.png）

左侧「设备配置文件」→ 创建 `device_profile`：
- LoRaWAN MAC 版本：`1.0.2`，区域参数修订版：`A`
- 入网方式：`OTAA`
- Payload codec：`自定义 JavaScript 编解码函数`（Decode/Encode）

### 2.5 创建网关 gateway1（截图 06_网关列表.png、07_网关配置.png）

左侧「网关列表」→ 创建：
- 名称：`gateway1`，网关 ID：`663356dd2eaf8198`
- 网络服务器：`lorawan_default`，网关配置文件：`gateway_profile`

### 2.6 创建应用 app（截图 08_应用配置.png）

左侧「应用列表」→ 创建：
- 名称：`app`，服务配置文件：`service_profile`

### 2.7 创建 LoRaWAN 设备（截图 09_设备OTAA密钥.png）

应用 `app` → 设备列表 → 创建两台 OTAA 设备（设备配置文件 device_profile）：

| 设备名 | devEUI | 用途 |
|---|---|---|
| Temperature_Humidity | 4aaa21eafb621f97 | 温湿度传感器（LoRaWAN 上报温度/湿度） |
| AutoFan | 7cb15d50b9f3ea6c | 排气扇（LoRaWAN 接收开关控制） |

OTAA 密钥：NwkKey / AppKey 按平台生成填入（见截图 09）。

---

## 第3步 ChirpStack 与 ThingsBoard 建立通讯（A-14-3）

### 3.1 设备配置变量 ThingsBoardDeviceName（截图 10_TB通讯变量_温湿度.png、11_TB通讯变量_排气扇.png）

ChirpStack 应用 `app` → 设备 → 配置 → 变量，为两台设备添加：

| 设备 | 变量名 | 变量值 |
|---|---|---|
| Temperature_Humidity | ThingsBoardDeviceName | 温湿度传感器 |
| AutoFan | ThingsBoardDeviceName | 排气扇 |

### 3.2 数据转发通路

- ChirpStack application-server 集成：`MQTT tcp://mosquitto:1883`
- distribution 容器执行：`./OnlinePlatformDataDistribute -a 172.18.0.1 -s mq.test.nlecloud.com`
- 数据流：仿真设备 → ChirpStack → MQTT → distribution → mq.test.nlecloud.com → ThingsBoard 同名设备

---

## 第4步 ThingsBoard 设备实体（A-14-4）

### 4.1 ChirpStack 侧设备关系（截图 12_通讯服务设备列表.png）

应用 `app` 设备列表显示 Temperature_Humidity / AutoFan 已注册在 LoRaWAN 通讯服务中（描述分别为「温湿度传感器」「排气扇」）。

### 4.2 TB 侧设备（截图 13_TB设备列表.png）

ThingsBoard → 设备 → 创建/确认两台设备（Device Profile = default）：
- `温湿度传感器`（承接 LoRaWAN 温湿度数据）
- `排气扇`（承接风扇开关控制）

---

## 第5步 ThingsBoard 仪表板「恒温系统」配置（A-14-5，截图 15_TB仪表板恒温系统.png）

### 5.1 新建仪表板
TB → 仪表板库 → 新建「恒温系统」。

### 5.2 配置实体别名
- 别名「温湿度传感器」：设备类型过滤输入 `default` → 选 温湿度传感器 设备（resolveMultiple）
- 别名「排气扇」：设备类型过滤 `default` + 名称前缀 `排气扇` → 选 排气扇 设备

### 5.3 添加四个部件（2×2 布局）

| 部件 | 数据源/目标 | 关键设置 |
|---|---|---|
| Analogue gauge（radial gauge）温度表 | 实体 `temperature` | units=℃，maxValue=50，minValue=-10 |
| Digital gauges（digital_vertical_bar）湿度条 | 实体 `humidity` | 实时湿度 % |
| maps_v2 Image Map 风扇状态图 | 别名「排气扇」，dataKey `fan` | mapImageUrl=ON-SVG；markerImageFunction 按 fan 值返回 ON/OFF 两图；markerImageSize=150；fitMapBounds |
| Control Widgets（switch_control）开关 | 目标=别名「排气扇」 | type=rpc，getValue/setValue |

### 5.4 保存并打开仪表板
- 温度表显示温度（℃）、湿度条显示湿度（%）、Image Map 按风扇状态切换「风扇运行中 / 风扇已停止」图片、开关可下发 RPC 控制风扇启停。

---

## 第6步 虚拟仿真平台搭建（A-14-1，截图 14_虚拟仿真设备搭建.png）

1. 进入工程虚拟仿真（智慧矿山场景，画布可拖拽设备）。
2. 拖拽设备到画布：
   - 「其他设备 → 负载 → 风扇」→ 画布
   - 「传感器 → 无线传感器 → 温湿度」→ 画布，弹出「选择底板」→ 选「需要电源」（温湿度 5V 供电）
   - 「网关 → ChirpStack」→ 画布（ChirpStack 网关）
3. 「连线验证」开启，检查设备连线。
4. 点击「模拟实验」启动仿真（设备间需正确连线后才能启动；若提示「连线存在错误，请检查」，需先在画布完成设备连线）。

---

## 第7步 截图交付清单（A-14-1 ~ A-14-5）

| 截图编号 | 文件 | 内容 |
|---|---|---|
| A-14-2 | 02~09 图 | ChirpStack 网络服务器 / 服务配置文件 / 设备配置文件 / 编解码 / 网关 / 应用 / OTAA 密钥 |
| A-14-3 | 10~11 图 | ChirpStack 设备变量 ThingsBoardDeviceName（温湿度传感器 / 排气扇） |
| A-14-4 | 12~13 图 | ChirpStack 通讯服务设备列表 + TB 设备列表 |
| A-14-5 | 15 图 | TB 仪表板：Analogue gauge 温度 / Digital gauges 湿度 / Image Map 风扇双状态 / Control Widgets 开关 |
| A-14-1 | 14 图 | 虚拟仿真设备搭建（温湿度传感器 + 风扇 + ChirpStack 网关） |

---

## 注意事项

- 仿真平台设备连线为画布交互，需在平台内完成设备间连线后启动模拟实验；模拟实验启动后，TB 温度/湿度表将显示真实采集数据（当前未启动时显示异常负值属正常）。
- >28℃ 自动降温可由 TB 规则链（温度阈值 → RPC 下发开关）或仿真平台条件逻辑实现。
- ChirpStack 密钥：Temperature_Humidity nwkKey `50 5d 4d de 50 62 af 0a 8b d1 c7 d5 b6 f2 2b 14`、genAppKey `0e 08 2b fc ef 75 09 39 9a 3b 9e 4b cf bb 10 ba`（写入截图 09）。
