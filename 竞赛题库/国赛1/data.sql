-- --------------------------------------------------------
-- nleedge 物联网数据管理系统数据库
-- 适用 MySQL 5.7
-- --------------------------------------------------------
CREATE DATABASE IF NOT EXISTS nleedge DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE nleedge;

-- 用户表
DROP TABLE IF EXISTS tb_user;
CREATE TABLE tb_user (
  id INT(11) NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  username VARCHAR(50) NOT NULL COMMENT '用户名',
  password VARCHAR(100) NOT NULL COMMENT '密码',
  phone VARCHAR(20) NOT NULL COMMENT '手机号',
  email VARCHAR(100) DEFAULT NULL COMMENT '邮箱',
  role TINYINT(4) NOT NULL DEFAULT 0 COMMENT '角色：0普通用户 1管理员',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  status TINYINT(4) NOT NULL DEFAULT 1 COMMENT '状态：0禁用 1启用',
  PRIMARY KEY (id),
  UNIQUE KEY uk_username (username)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='用户表';

-- 项目表
DROP TABLE IF EXISTS tb_project;
CREATE TABLE tb_project (
  id INT(11) NOT NULL AUTO_INCREMENT COMMENT '项目ID',
  user_id INT(11) NOT NULL COMMENT '所属用户ID',
  project_name VARCHAR(100) NOT NULL COMMENT '项目名称',
  industry_type VARCHAR(50) NOT NULL COMMENT '行业类别',
  network_type VARCHAR(50) NOT NULL COMMENT '联网方案',
  description VARCHAR(255) DEFAULT NULL COMMENT '项目描述',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  KEY idx_user_id (user_id),
  CONSTRAINT fk_project_user FOREIGN KEY (user_id) REFERENCES tb_user (id)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='项目表';

-- 网关设备表
DROP TABLE IF EXISTS tb_device;
CREATE TABLE tb_device (
  id INT(11) NOT NULL AUTO_INCREMENT COMMENT '设备ID',
  project_id INT(11) NOT NULL COMMENT '所属项目ID',
  device_name VARCHAR(100) NOT NULL COMMENT '设备名称',
  device_identifier VARCHAR(100) NOT NULL COMMENT '设备标识',
  device_type VARCHAR(50) NOT NULL COMMENT '设备类型：gateway网关 terminal4G终端',
  online_status TINYINT(4) NOT NULL DEFAULT 0 COMMENT '在线状态：0离线 1在线',
  remark VARCHAR(255) DEFAULT NULL COMMENT '备注',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (id),
  UNIQUE KEY uk_device_identifier (device_identifier),
  KEY idx_project_id (project_id),
  CONSTRAINT fk_device_project FOREIGN KEY (project_id) REFERENCES tb_project (id)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='网关设备表';

-- 传感器数据上报记录表
DROP TABLE IF EXISTS tb_sensor_data;
CREATE TABLE tb_sensor_data (
  id BIGINT(20) NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  device_id INT(11) NOT NULL COMMENT '设备ID',
  sensor_name VARCHAR(50) NOT NULL COMMENT '传感器名称',
  sensor_identifier VARCHAR(50) NOT NULL COMMENT '传感器标识',
  sensor_value DECIMAL(10,2) DEFAULT NULL COMMENT '上报数值',
  sensor_unit VARCHAR(20) DEFAULT NULL COMMENT '单位',
  sensor_status TINYINT(4) DEFAULT NULL COMMENT '状态值：0正常 1报警',
  report_time DATETIME NOT NULL COMMENT '上报时间',
  PRIMARY KEY (id),
  KEY idx_device_id (device_id),
  KEY idx_report_time (report_time),
  CONSTRAINT fk_sensor_data_device FOREIGN KEY (device_id) REFERENCES tb_device (id)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='传感器数据上报记录表';

-- 控制命令记录表
DROP TABLE IF EXISTS tb_command;
CREATE TABLE tb_command (
  id INT(11) NOT NULL AUTO_INCREMENT COMMENT '命令ID',
  device_id INT(11) NOT NULL COMMENT '设备ID',
  command_type VARCHAR(50) NOT NULL COMMENT '命令类型：switch控制 switch_set开关状态',
  command_name VARCHAR(50) DEFAULT NULL COMMENT '执行器名称',
  command_value VARCHAR(20) DEFAULT NULL COMMENT '命令值：0关 1开',
  command_state TINYINT(4) NOT NULL DEFAULT 0 COMMENT '执行状态：0未执行 1成功 2失败',
  create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '下发时间',
  PRIMARY KEY (id),
  KEY idx_device_id (device_id),
  CONSTRAINT fk_command_device FOREIGN KEY (device_id) REFERENCES tb_device (id)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='控制命令记录表';

-- 传感器配置表
DROP TABLE IF EXISTS tb_sensor_config;
CREATE TABLE tb_sensor_config (
  id INT(11) NOT NULL AUTO_INCREMENT COMMENT '配置ID',
  device_id INT(11) NOT NULL COMMENT '设备ID',
  sensor_name VARCHAR(50) NOT NULL COMMENT '传感器名称',
  sensor_identifier VARCHAR(50) NOT NULL COMMENT '传感器标识',
  trans_type VARCHAR(20) NOT NULL DEFAULT '只上报' COMMENT '传输类型',
  data_type VARCHAR(20) NOT NULL DEFAULT '浮点型' COMMENT '数据类型',
  data_min DECIMAL(10,2) DEFAULT NULL COMMENT '数据范围最小值',
  data_max DECIMAL(10,2) DEFAULT NULL COMMENT '数据范围最大值',
  unit VARCHAR(20) DEFAULT NULL COMMENT '单位',
  alarm_threshold DECIMAL(10,2) DEFAULT NULL COMMENT '报警阈值',
  PRIMARY KEY (id),
  KEY idx_device_id (device_id),
  CONSTRAINT fk_sensor_config_device FOREIGN KEY (device_id) REFERENCES tb_device (id)
) ENGINE=InnoDB AUTO_INCREMENT=1 DEFAULT CHARSET=utf8mb4 COMMENT='传感器配置表';

-- 示例数据
INSERT INTO tb_user (id, username, password, phone, email, role) VALUES
(1, '18912345601', '123456', '18912345601', 'user01@example.com', 0);

INSERT INTO tb_project (id, user_id, project_name, industry_type, network_type, description) VALUES
(1, 1, '智能市政', '智慧城市', '以太网', '市政物联网示范项目');

INSERT INTO tb_device (id, project_id, device_name, device_identifier, device_type, online_status) VALUES
(1, 1, '物联网网关', 'GW001', 'gateway', 1),
(2, 1, '4G通讯终端', '4GMT1234501', 'terminal', 1);

INSERT INTO tb_sensor_config (id, device_id, sensor_name, sensor_identifier, trans_type, data_type, data_min, data_max, unit, alarm_threshold) VALUES
(1, 1, '温湿度传感器-温度', 'm_temp', '只上报', '浮点型', -40, 80, '℃', 45),
(2, 1, '温湿度传感器-湿度', 'm_hum', '只上报', '浮点型', 0, 100, '%rh', 85),
(3, 1, '光照传感器', 'm_light', '只上报', '浮点型', 0, 100000, 'Lux', 20000),
(4, 1, '甲烷', 'm_Methane1', '只上报', '浮点型', 0, 100, '%rh', 20),
(5, 2, '水浸传感器', 'm_water_immersion', '只上报', '浮点型', 0, 1, '', 1);

INSERT INTO tb_sensor_data (id, device_id, sensor_name, sensor_identifier, sensor_value, sensor_unit, sensor_status, report_time) VALUES
(1, 1, '温湿度传感器-温度', 'm_temp', 28.50, '℃', 0, NOW()),
(2, 1, '温湿度传感器-湿度', 'm_hum', 60.00, '%rh', 0, NOW()),
(3, 1, '光照传感器', 'm_light', 80.00, 'Lux', 0, NOW()),
(4, 1, '甲烷', 'm_Methane1', 5.20, '%rh', 0, NOW()),
(5, 2, '水浸传感器', 'm_water_immersion', 1.00, '', 1, NOW());

INSERT INTO tb_command (id, device_id, command_type, command_name, command_value, command_state) VALUES
(1, 1, 'switch', '多层指示灯-绿', '1', 1),
(2, 1, 'switch', '风扇', '0', 1);