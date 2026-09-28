package com.env.newland.envdetect;

import android.app.AlertDialog;
import android.graphics.Color;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.support.v7.app.AppCompatActivity;
import android.view.View;
import android.widget.Button;
import android.widget.EditText;
import android.widget.TextView;

import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;
import java.util.Map;
import java.util.Random;

public class MainActivity extends AppCompatActivity implements TcpClient.Callback {

    private EditText etHost, etPort;
    private Button btnConnect, btnDisconnect, btnHelp;
    private TextView tvStatus, tvConnDot;
    private TextView tvTemper, tvHumidity, tvCo2, tvLight;
    private TextView tvTime;

    private TcpClient tcpClient;
    private Handler handler = new Handler(Looper.getMainLooper());
    private boolean connected = false;
    private boolean demoMode = true;
    private Random random = new Random();
    private SimpleDateFormat sdf = new SimpleDateFormat("yyyy-MM-dd HH:mm:ss", Locale.CHINA);

    private double temperVal = 25.0;
    private double humidityVal = 55.0;
    private double co2Val = 450.0;
    private double lightVal = 100.0;

    private Runnable demoRunnable = new Runnable() {
        @Override
        public void run() {
            if (demoMode && !connected) {
                temperVal = 18.0 + random.nextDouble() * 14.0;
                humidityVal = 40.0 + random.nextDouble() * 30.0;
                co2Val = 350.0 + random.nextDouble() * 850.0;
                lightVal = 20.0 + random.nextDouble() * 160.0;
                updateDisplay();
                handler.postDelayed(this, 2000);
            }
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        if (getSupportActionBar() != null) {
            getSupportActionBar().setTitle("环境监测系统");
        }

        etHost = findViewById(R.id.et_host);
        etPort = findViewById(R.id.et_port);
        btnConnect = findViewById(R.id.btn_connect);
        btnDisconnect = findViewById(R.id.btn_disconnect);
        btnHelp = findViewById(R.id.btn_help);
        tvStatus = findViewById(R.id.tv_status);
        tvConnDot = findViewById(R.id.tv_conn_dot);
        tvTemper = findViewById(R.id.tv_temper_val);
        tvHumidity = findViewById(R.id.tv_humidity_val);
        tvCo2 = findViewById(R.id.tv_co2_val);
        tvLight = findViewById(R.id.tv_light_val);
        tvTime = findViewById(R.id.tv_time);

        btnConnect.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                connectToServer();
            }
        });

        btnDisconnect.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                disconnect();
            }
        });

        btnHelp.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showHelpDialog();
            }
        });

        updateConnUI(false);
        startDemoMode();
    }

    private void connectToServer() {
        String host = etHost.getText().toString().trim();
        String portStr = etPort.getText().toString().trim();
        if (host.isEmpty() || portStr.isEmpty()) {
            tvStatus.setText("请输入服务器IP和端口");
            return;
        }
        int port;
        try {
            port = Integer.parseInt(portStr);
        } catch (NumberFormatException e) {
            tvStatus.setText("端口号格式错误");
            return;
        }

        stopDemoMode();
        demoMode = false;

        if (tcpClient != null) {
            tcpClient.stop();
        }
        tcpClient = new TcpClient(host, port, this);
        tcpClient.start();
        tvStatus.setText("正在连接 " + host + ":" + port + " ...");
    }

    private void disconnect() {
        if (tcpClient != null) {
            tcpClient.stop();
            tcpClient = null;
        }
        connected = false;
        updateConnUI(false);
        tvStatus.setText("已断开连接");
        startDemoMode();
    }

    private void startDemoMode() {
        demoMode = true;
        handler.removeCallbacks(demoRunnable);
        handler.postDelayed(demoRunnable, 1000);
        tvStatus.setText("演示模式 - 无服务器连接");
    }

    private void stopDemoMode() {
        demoMode = false;
        handler.removeCallbacks(demoRunnable);
    }

    private void updateConnUI(final boolean isConnected) {
        connected = isConnected;
        if (isConnected) {
            tvConnDot.setBackgroundResource(R.drawable.bg_conn_on);
            tvConnDot.setText("已连接");
            tvConnDot.setTextColor(Color.WHITE);
            tvStatus.setText("实时数据采集中");
        } else {
            tvConnDot.setBackgroundResource(R.drawable.bg_conn_off);
            tvConnDot.setText("未连接");
            tvConnDot.setTextColor(Color.parseColor("#999999"));
        }
    }

    private void updateDisplay() {
        tvTemper.setText(String.format(Locale.CHINA, "%.1f", temperVal));
        tvHumidity.setText(String.format(Locale.CHINA, "%.1f", humidityVal));
        tvCo2.setText(String.format(Locale.CHINA, "%.0f", co2Val));
        tvLight.setText(String.format(Locale.CHINA, "%.0f", lightVal));
        tvTime.setText(sdf.format(new Date()));
    }

    @Override
    public void onLineReceived(String line) {
        Map<String, Double> data = DataParser.parse(line);
        if (data != null) {
            stopDemoMode();
            demoMode = false;
            if (data.containsKey("temper")) temperVal = data.get("temper");
            if (data.containsKey("humidity")) humidityVal = data.get("humidity");
            if (data.containsKey("co2")) co2Val = data.get("co2");
            if (data.containsKey("light")) lightVal = data.get("light");
            tvStatus.setText("真实模式 - 实时数据");
        }
        updateDisplay();
    }

    @Override
    public void onConnected() {
        connected = true;
        updateConnUI(true);
        tvStatus.setText("已连接 - 等待数据...");
    }

    @Override
    public void onDisconnected(String reason) {
        connected = false;
        updateConnUI(false);
        if (!demoMode) {
            startDemoMode();
        }
        tvStatus.setText("连接失败: " + reason + "，3秒后自动重连（演示模式）");
    }

    private void showHelpDialog() {
        new AlertDialog.Builder(this)
                .setTitle("数据格式说明")
                .setMessage("本系统支持以下串口数据格式（大小写不敏感，中英文标点均可）：\n\n"
                        + "1. T:25.5 H:60 L:1200 C:400\n"
                        + "2. 温度=25.5,湿度=60.2,二氧化碳=400,光=120\n"
                        + "3. Co2:400 Light:120 Temp:25.5 Humidity:60\n"
                        + "4. CO2=500;光照=1200;温度=28;湿度=55\n\n"
                        + "支持的标记：\n"
                        + "温度: T/Temp/Temperature\n"
                        + "湿度: H/Humidity/Humi\n"
                        + "二氧化碳: C/CO2/Co2/二氧化碳\n"
                        + "光照: L/Light/Lux/光\n\n"
                        + "每行应包含所有4个传感器数据。")
                .setPositiveButton("知道了", null)
                .show();
    }

    @Override
    protected void onDestroy() {
        super.onDestroy();
        if (tcpClient != null) {
            tcpClient.stop();
        }
        handler.removeCallbacksAndMessages(null);
    }
}
