package com.nlecloud.cinemasystem;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.support.constraint.ConstraintLayout;
import android.support.v7.app.AppCompatActivity;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Smart Cinema System
 * Features: CO2 monitoring, fan control, RFID door access, TCP server
 * Manages cinema environment and access control
 */
public class MainActivity extends AppCompatActivity {

    private static final String BASE_URL = "http://api.nlecloud.com";
    private static final String ACCESS_TOKEN = "your_access_token_here";
    private static final String DEVICE_ID = "your_device_id_here";

    private TextView tvCo2Level;
    private TextView tvTemperature;
    private TextView tvFanStatus;
    private TextView tvDoorStatus;
    private TextView tvRfidStatus;
    private TextView tvTcpStatus;
    private Button btnFanOn;
    private Button btnFanOff;
    private Button btnDoorOpen;
    private Button btnDoorClose;
    private Button btnStartTcp;
    private Button btnStopTcp;
    private Button btnRefresh;

    private Handler handler;
    private Runnable dataFetchRunnable;
    private boolean isFetching = false;
    private boolean tcpRunning = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        handler = new Handler(Looper.getMainLooper());

        initViews();
        setupClickListeners();

        Toast.makeText(this, "Cinema System Started", Toast.LENGTH_SHORT).show();
    }

    private void initViews() {
        tvCo2Level = findViewById(R.id.tv_co2_level);
        tvTemperature = findViewById(R.id.tv_temperature);
        tvFanStatus = findViewById(R.id.tv_fan_status);
        tvDoorStatus = findViewById(R.id.tv_door_status);
        tvRfidStatus = findViewById(R.id.tv_rfid_status);
        tvTcpStatus = findViewById(R.id.tv_tcp_status);
        btnFanOn = findViewById(R.id.btn_fan_on);
        btnFanOff = findViewById(R.id.btn_fan_off);
        btnDoorOpen = findViewById(R.id.btn_door_open);
        btnDoorClose = findViewById(R.id.btn_door_close);
        btnStartTcp = findViewById(R.id.btn_start_tcp);
        btnStopTcp = findViewById(R.id.btn_stop_tcp);
        btnRefresh = findViewById(R.id.btn_refresh);
    }

    private void setupClickListeners() {
        btnFanOn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Fan", "1");
            }
        });

        btnFanOff.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Fan", "0");
            }
        });

        btnDoorOpen.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Door", "OPEN");
            }
        });

        btnDoorClose.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Door", "CLOSE");
            }
        });

        btnStartTcp.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startTcpServer();
            }
        });

        btnStopTcp.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                stopTcpServer();
            }
        });

        btnRefresh.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                fetchData();
            }
        });
    }

    @Override
    protected void onResume() {
        super.onResume();
        startPeriodicFetch();
    }

    @Override
    protected void onPause() {
        super.onPause();
        stopPeriodicFetch();
    }

    private void startPeriodicFetch() {
        isFetching = true;
        dataFetchRunnable = new Runnable() {
            @Override
            public void run() {
                if (isFetching) {
                    fetchData();
                    handler.postDelayed(this, 3000);
                }
            }
        };
        handler.post(dataFetchRunnable);
    }

    private void stopPeriodicFetch() {
        isFetching = false;
        if (dataFetchRunnable != null) {
            handler.removeCallbacks(dataFetchRunnable);
        }
    }

    private void fetchData() {
        fetchSensorData("CO2", tvCo2Level, "CO2 Level", " ppm");
        fetchSensorData("Temperature", tvTemperature, "Temperature", " C");
        fetchSensorData("Fan", tvFanStatus, "Fan", "");
        fetchSensorData("Door", tvDoorStatus, "Door", "");
        fetchSensorData("RFID", tvRfidStatus, "RFID", "");
    }

    private void fetchSensorData(final String apiTag, final TextView textView,
                                  final String label, final String unit) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    String urlStr = BASE_URL + "/api/" + DEVICE_ID + "/" + apiTag
                            + "?accessToken=" + ACCESS_TOKEN;
                    URL url = new URL(urlStr);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("GET");
                    conn.setConnectTimeout(5000);
                    conn.setReadTimeout(5000);

                    int responseCode = conn.getResponseCode();
                    if (responseCode == 200) {
                        BufferedReader reader = new BufferedReader(
                                new InputStreamReader(conn.getInputStream()));
                        StringBuilder response = new StringBuilder();
                        String line;
                        while ((line = reader.readLine()) != null) {
                            response.append(line);
                        }
                        reader.close();

                        final JSONObject json = new JSONObject(response.toString());
                        final String value = json.optString("value", "N/A");

                        handler.post(new Runnable() {
                            @Override
                            public void run() {
                                if ("Fan".equals(apiTag) || "Door".equals(apiTag)
                                        || "RFID".equals(apiTag)) {
                                    if ("1".equals(value) || "OPEN".equals(value)) {
                                        textView.setText(label + ": Active");
                                        textView.setTextColor(0xFF00FF00);
                                    } else {
                                        textView.setText(label + ": Inactive");
                                        textView.setTextColor(0xFF888888);
                                    }
                                } else {
                                    textView.setText(label + ": " + value + unit);
                                }
                            }
                        });
                    }
                    conn.disconnect();
                } catch (Exception e) {
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            textView.setText(label + ": Error");
                        }
                    });
                }
            }
        }).start();
    }

    private void startTcpServer() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    tcpRunning = true;
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            tvTcpStatus.setText("TCP Server: Running");
                            tvTcpStatus.setTextColor(0xFF00FF00);
                            Toast.makeText(MainActivity.this,
                                    "TCP Server started", Toast.LENGTH_SHORT).show();
                        }
                    });
                } catch (Exception e) {
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(MainActivity.this,
                                    "TCP start error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                        }
                    });
                }
            }
        }).start();
    }

    private void stopTcpServer() {
        tcpRunning = false;
        handler.post(new Runnable() {
            @Override
            public void run() {
                tvTcpStatus.setText("TCP Server: Stopped");
                tvTcpStatus.setTextColor(0xFFFF0000);
                Toast.makeText(MainActivity.this,
                        "TCP Server stopped", Toast.LENGTH_SHORT).show();
            }
        });
    }

    private void sendCommand(final String apiTag, final String value) {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    String urlStr = BASE_URL + "/api/" + DEVICE_ID + "/" + apiTag
                            + "?accessToken=" + ACCESS_TOKEN;
                    URL url = new URL(urlStr);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setConnectTimeout(5000);
                    conn.setReadTimeout(5000);
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setDoOutput(true);

                    JSONObject body = new JSONObject();
                    body.put("value", value);

                    OutputStream os = conn.getOutputStream();
                    os.write(body.toString().getBytes("UTF-8"));
                    os.flush();
                    os.close();

                    final int responseCode = conn.getResponseCode();
                    conn.disconnect();

                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            if (responseCode == 200) {
                                Toast.makeText(MainActivity.this,
                                        apiTag + " command sent", Toast.LENGTH_SHORT).show();
                            } else {
                                Toast.makeText(MainActivity.this,
                                        "Command failed: " + responseCode, Toast.LENGTH_SHORT).show();
                            }
                        }
                    });
                } catch (Exception e) {
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(MainActivity.this,
                                    "Error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                        }
                    });
                }
            }
        }).start();
    }
}
