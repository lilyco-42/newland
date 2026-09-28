package com.nlecloud.cloudapp;

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
 * Cloud Service Application
 * Features: Remote device control, cloud data sync, device management
 * IoT cloud platform client application
 */
public class MainActivity extends AppCompatActivity {

    private static final String BASE_URL = "http://api.nlecloud.com";
    private static final String ACCESS_TOKEN = "your_access_token_here";
    private static final String DEVICE_ID = "your_device_id_here";

    private TextView tvDeviceStatus;
    private TextView tvSensorData1;
    private TextView tvSensorData2;
    private TextView tvControlStatus;
    private TextView tvCloudSync;
    private Button btnDeviceOn;
    private Button btnDeviceOff;
    private Button btnSyncData;
    private Button btnReset;
    private Button btnRefresh;

    private Handler handler;
    private Runnable dataFetchRunnable;
    private boolean isFetching = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        handler = new Handler(Looper.getMainLooper());

        initViews();
        setupClickListeners();

        Toast.makeText(this, "Cloud Service App Started", Toast.LENGTH_SHORT).show();
    }

    private void initViews() {
        tvDeviceStatus = findViewById(R.id.tv_device_status);
        tvSensorData1 = findViewById(R.id.tv_sensor_data1);
        tvSensorData2 = findViewById(R.id.tv_sensor_data2);
        tvControlStatus = findViewById(R.id.tv_control_status);
        tvCloudSync = findViewById(R.id.tv_cloud_sync);
        btnDeviceOn = findViewById(R.id.btn_device_on);
        btnDeviceOff = findViewById(R.id.btn_device_off);
        btnSyncData = findViewById(R.id.btn_sync_data);
        btnReset = findViewById(R.id.btn_reset);
        btnRefresh = findViewById(R.id.btn_refresh);
    }

    private void setupClickListeners() {
        btnDeviceOn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Device", "1");
            }
        });

        btnDeviceOff.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Device", "0");
            }
        });

        btnSyncData.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                syncCloudData();
            }
        });

        btnReset.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Reset", "1");
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
        fetchSensorData("Device", tvDeviceStatus, "Device Status");
        fetchSensorData("Sensor1", tvSensorData1, "Sensor 1");
        fetchSensorData("Sensor2", tvSensorData2, "Sensor 2");
        fetchSensorData("Control", tvControlStatus, "Control Status");
    }

    private void fetchSensorData(final String apiTag, final TextView textView, final String label) {
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
                                if ("Device".equals(apiTag)) {
                                    if ("1".equals(value)) {
                                        textView.setText(label + ": Online");
                                        textView.setTextColor(0xFF00FF00);
                                    } else {
                                        textView.setText(label + ": Offline");
                                        textView.setTextColor(0xFF888888);
                                    }
                                } else {
                                    textView.setText(label + ": " + value);
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

    private void syncCloudData() {
        new Thread(new Runnable() {
            @Override
            public void run() {
                try {
                    String urlStr = BASE_URL + "/api/" + DEVICE_ID + "/Sync"
                            + "?accessToken=" + ACCESS_TOKEN;
                    URL url = new URL(urlStr);
                    HttpURLConnection conn = (HttpURLConnection) url.openConnection();
                    conn.setRequestMethod("POST");
                    conn.setConnectTimeout(5000);
                    conn.setReadTimeout(5000);
                    conn.setRequestProperty("Content-Type", "application/json");
                    conn.setDoOutput(true);

                    JSONObject body = new JSONObject();
                    body.put("action", "sync");

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
                                tvCloudSync.setText("Cloud Sync: Success");
                                tvCloudSync.setTextColor(0xFF00FF00);
                                Toast.makeText(MainActivity.this,
                                        "Data synced to cloud", Toast.LENGTH_SHORT).show();
                            } else {
                                tvCloudSync.setText("Cloud Sync: Failed");
                                tvCloudSync.setTextColor(0xFFFF0000);
                            }
                        }
                    });
                } catch (Exception e) {
                    handler.post(new Runnable() {
                        @Override
                        public void run() {
                            Toast.makeText(MainActivity.this,
                                    "Sync error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
                        }
                    });
                }
            }
        }).start();
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
