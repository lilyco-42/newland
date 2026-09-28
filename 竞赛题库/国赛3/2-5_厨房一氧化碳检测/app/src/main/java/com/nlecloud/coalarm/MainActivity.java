package com.nlecloud.coalarm;

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
 * Kitchen CO Alarm App
 * Features: Carbon monoxide detection, buzzer control, alarm management
 * Critical safety system for kitchen environment
 */
public class MainActivity extends AppCompatActivity {

    private static final String BASE_URL = "http://api.nlecloud.com";
    private static final String ACCESS_TOKEN = "your_access_token_here";
    private static final String DEVICE_ID = "your_device_id_here";

    private TextView tvCoLevel;
    private TextView tvTemperature;
    private TextView tvBuzzerStatus;
    private TextView tvAlarmStatus;
    private TextView tvVentStatus;
    private Button btnBuzzerOn;
    private Button btnBuzzerOff;
    private Button btnVentOn;
    private Button btnVentOff;
    private Button btnAlarmReset;
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

        Toast.makeText(this, "CO Alarm System Started", Toast.LENGTH_SHORT).show();
    }

    private void initViews() {
        tvCoLevel = findViewById(R.id.tv_co_level);
        tvTemperature = findViewById(R.id.tv_temperature);
        tvBuzzerStatus = findViewById(R.id.tv_buzzer_status);
        tvAlarmStatus = findViewById(R.id.tv_alarm_status);
        tvVentStatus = findViewById(R.id.tv_vent_status);
        btnBuzzerOn = findViewById(R.id.btn_buzzer_on);
        btnBuzzerOff = findViewById(R.id.btn_buzzer_off);
        btnVentOn = findViewById(R.id.btn_vent_on);
        btnVentOff = findViewById(R.id.btn_vent_off);
        btnAlarmReset = findViewById(R.id.btn_alarm_reset);
        btnRefresh = findViewById(R.id.btn_refresh);
    }

    private void setupClickListeners() {
        btnBuzzerOn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Buzzer", "1");
            }
        });

        btnBuzzerOff.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Buzzer", "0");
            }
        });

        btnVentOn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Ventilation", "1");
            }
        });

        btnVentOff.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Ventilation", "0");
            }
        });

        btnAlarmReset.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Alarm", "RESET");
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
        fetchSensorData("CO", tvCoLevel, "CO Level", " ppm");
        fetchSensorData("Temperature", tvTemperature, "Temperature", " C");
        fetchSensorData("Buzzer", tvBuzzerStatus, "Buzzer", "");
        fetchSensorData("Alarm", tvAlarmStatus, "Alarm", "");
        fetchSensorData("Ventilation", tvVentStatus, "Ventilation", "");
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
                                        textView.setText(label + ": DANGER");
                                        textView.setTextColor(0xFFFF0000);
                                    } else {
                                        textView.setText(label + ": Safe");
                                        textView.setTextColor(0xFF00FF00);
                                    }
                                } else if ("Buzzer".equals(apiTag) || "Ventilation".equals(apiTag)) {
                                    if ("1".equals(value)) {
                                        textView.setText(label + ": ON");
                                        textView.setTextColor(0xFF00FF00);
                                    } else {
                                        textView.setText(label + ": OFF");
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
