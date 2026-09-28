package com.nlecloud.forestfire;

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
 * Forest Fire Alarm System
 * Features: Temperature monitoring, smoke detection, alarm management
 * Critical early warning system for forest fire prevention
 */
public class MainActivity extends AppCompatActivity {

    private static final String BASE_URL = "http://api.nlecloud.com";
    private static final String ACCESS_TOKEN = "your_access_token_here";
    private static final String DEVICE_ID = "your_device_id_here";

    private TextView tvTemperature;
    private TextView tvSmokeLevel;
    private TextView tvHumidity;
    private TextView tvAlarmStatus;
    private TextView tvAlertLevel;
    private Button btnAlarmArm;
    private Button btnAlarmDisarm;
    private Button btnSirenOn;
    private Button btnSirenOff;
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

        Toast.makeText(this, "Forest Fire Alarm Started", Toast.LENGTH_SHORT).show();
    }

    private void initViews() {
        tvTemperature = findViewById(R.id.tv_temperature);
        tvSmokeLevel = findViewById(R.id.tv_smoke_level);
        tvHumidity = findViewById(R.id.tv_humidity);
        tvAlarmStatus = findViewById(R.id.tv_alarm_status);
        tvAlertLevel = findViewById(R.id.tv_alert_level);
        btnAlarmArm = findViewById(R.id.btn_alarm_arm);
        btnAlarmDisarm = findViewById(R.id.btn_alarm_disarm);
        btnSirenOn = findViewById(R.id.btn_siren_on);
        btnSirenOff = findViewById(R.id.btn_siren_off);
        btnRefresh = findViewById(R.id.btn_refresh);
    }

    private void setupClickListeners() {
        btnAlarmArm.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Alarm", "1");
            }
        });

        btnAlarmDisarm.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Alarm", "0");
            }
        });

        btnSirenOn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Siren", "1");
            }
        });

        btnSirenOff.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Siren", "0");
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
        fetchSensorData("Temperature", tvTemperature, "Temperature", " C");
        fetchSensorData("Smoke", tvSmokeLevel, "Smoke Level", " ppm");
        fetchSensorData("Humidity", tvHumidity, "Humidity", " %RH");
        fetchSensorData("Alarm", tvAlarmStatus, "Alarm", "");
        fetchSensorData("AlertLevel", tvAlertLevel, "Alert Level", "");
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
                                if ("Alarm".equals(apiTag)) {
                                    if ("1".equals(value)) {
                                        textView.setText(label + ": TRIGGERED");
                                        textView.setTextColor(0xFFFF0000);
                                    } else {
                                        textView.setText(label + ": Normal");
                                        textView.setTextColor(0xFF00FF00);
                                    }
                                } else if ("AlertLevel".equals(apiTag)) {
                                    textView.setText(label + ": " + value);
                                    if ("HIGH".equals(value)) {
                                        textView.setTextColor(0xFFFF0000);
                                    } else if ("MEDIUM".equals(value)) {
                                        textView.setTextColor(0xFFFF8800);
                                    } else {
                                        textView.setTextColor(0xFF00FF00);
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
