"""
新大陆 NLECloud PyQt5 GUI Demo
对齐官方 DemoCloudWindow.py 模式, 使用 nlecloud_sdk
"""
import sys
import json
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QMessageBox, QHeaderView, QGroupBox, QFormLayout, QTabWidget,
    QComboBox, QSpinBox, QProgressBar, QStatusBar
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont, QColor

from nlecloud_sdk import NLECloudAPI


class LoginWidget(QWidget):
    """登录组件 (对齐官方 LoginActivity)"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)

        self.et_host = QLineEdit("192.168.0.138")
        self.et_port = QLineEdit("80")
        self.et_account = QLineEdit()
        self.et_password = QLineEdit()
        self.et_password.setEchoMode(QLineEdit.Password)

        layout.addRow("云平台地址:", self.et_host)
        layout.addRow("端口:", self.et_port)
        layout.addRow("用户名:", self.et_account)
        layout.addRow("密码:", self.et_password)

        self.btn_login = QPushButton("登录")
        layout.addRow(self.btn_login)

    def get_base_url(self):
        return f"http://{self.et_host.text()}:{self.et_port.text()}/"

    def get_account(self):
        return self.et_account.text()

    def get_password(self):
        return self.et_password.text()


class SensorWidget(QWidget):
    """传感器数据展示组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["传感器", "标识", "值", "状态"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.table)

        self.btn_refresh = QPushButton("刷新数据")
        layout.addWidget(self.btn_refresh)

    def update_data(self, sensors_data):
        self.table.setRowCount(len(sensors_data))
        for i, (api_tag, value) in enumerate(sensors_data.items()):
            self.table.setItem(i, 0, QTableWidgetItem(api_tag))
            self.table.setItem(i, 1, QTableWidgetItem(api_tag))
            self.table.setItem(i, 2, QTableWidgetItem(str(value)))
            status = "在线" if value is not None else "离线"
            item = QTableWidgetItem(status)
            if value is not None:
                item.setForeground(QColor("#39C42F"))
            else:
                item.setForeground(QColor("#CE5858"))
            self.table.setItem(i, 3, item)


class ControlWidget(QWidget):
    """控制组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QFormLayout(self)

        self.et_device_id = QLineEdit("1")
        self.et_api_tag = QLineEdit()
        self.et_data = QLineEdit()

        layout.addRow("设备ID:", self.et_device_id)
        layout.addRow("传感器标识:", self.et_api_tag)
        layout.addRow("控制值:", self.et_data)

        self.btn_control = QPushButton("发送控制")
        layout.addRow(self.btn_control)


class MainWindow(QMainWindow):
    """主窗口 (对齐官方 Demo 模式)"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("新大陆 NLECloud Python SDK (PyQt5)")
        self.setMinimumSize(800, 600)

        self.api = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_sensors)

        self.setup_ui()

    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)

        tabs = QTabWidget()
        main_layout.addWidget(tabs)

        # Tab 1: 登录
        login_widget = LoginWidget()
        login_widget.btn_login.clicked.connect(self.login)
        self.login_widget = login_widget
        tabs.addTab(login_widget, "登录")

        # Tab 2: 传感器数据
        sensor_widget = SensorWidget()
        sensor_widget.btn_refresh.clicked.connect(self.refresh_sensors)
        self.sensor_widget = sensor_widget
        tabs.addTab(sensor_widget, "传感器数据")

        # Tab 3: 控制
        control_widget = ControlWidget()
        control_widget.btn_control.clicked.connect(self.send_control)
        self.control_widget = control_widget
        tabs.addTab(control_widget, "控制设备")

        self.tabs = tabs
        self.statusBar().showMessage("请先登录云平台")

    def login(self):
        base_url = self.login_widget.get_base_url()
        account = self.login_widget.get_account()
        password = self.login_widget.get_password()

        self.api = NLECloudAPI(base_url)
        result = self.api.user_login(account, password)

        if result:
            self.statusBar().showMessage(f"登录成功 - Token: {result['AccessToken'][:20]}...")
            self.tabs.setCurrentIndex(1)
            self.timer.start(5000)
        else:
            QMessageBox.warning(self, "登录失败", "用户名或密码错误")

    def refresh_sensors(self):
        if not self.api or not self.api.access_token:
            return
        device_id = self.control_widget.et_device_id.text()
        resp = self.api.get_sensors(device_id)
        if resp and resp.get("Status") == 0:
            sensors = resp.get("ResultObj", [])
            data = {}
            for s in sensors:
                data[s.get("ApiTag", "")] = s.get("Value", None)
            self.sensor_widget.update_data(data)

    def send_control(self):
        if not self.api or not self.api.access_token:
            QMessageBox.warning(self, "错误", "请先登录")
            return
        device_id = self.control_widget.et_device_id.text()
        api_tag = self.control_widget.et_api_tag.text()
        value = self.control_widget.et_data.text()

        resp = self.api.control(device_id, api_tag, value)
        if resp and resp.get("Status") == 0:
            QMessageBox.information(self, "成功", "控制命令已发送")
        else:
            QMessageBox.warning(self, "失败", "控制命令发送失败")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())
