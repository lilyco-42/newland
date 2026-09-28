package com.nlecloud.locationtracker;

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
 * Location Tracking System
 * Features: GPS tracking, geofence alerts, location history
 * Real-time location monitoring and management
 */
public class MainActivity extends AppCompatActivity {

    private static final String BASE_URL = "http://api.nlecloud.com";
    private static final String ACCESS_TOKEN = "your_access_token_here";
    private static final String DEVICE_ID = "your_device_id_here";

    private TextView tvLatitude;
    private TextView tvLongitude;
    private TextView tvLocationStatus;
    private TextView tvGeofenceStatus;
    private Button btnTrackStart;
    private Button btnTrackStop;
    private Button btnGeofenceOn;
    private Button btnGeofenceOff;
    private Button btnRefresh;

    private Handler handler;
    private Runnable dataFetchRunnable;
    private boolean isFetching = false;
    private boolean tracking = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        handler = new Handler(Looper.getMainLooper());

        initViews();
        setupClickListeners();

        Toast.makeText(this, "Location Tracker Started", Toast.LENGTH_SHORT).show();
    }

    private void initViews() {
        tvLatitude = findViewById(R.id.tv_latitude);
        tvLongitude = findViewById(R.id.tv_longitude);
        tvLocationStatus = findViewById(R.id.tv_location_status);
        tvGeofenceStatus = findViewById(R.id.tv_geofence_status);
        btnTrackStart = findViewById(R.id.btn_track_start);
        btnTrackStop = findViewById(R.id.btn_track_stop);
        btnGeofenceOn = findViewById(R.id.btn_geofence_on);
        btnGeofenceOff = findViewById(R.id.btn_geofence_off);
        btnRefresh = findViewById(R.id.btn_refresh);
    }

    private void setupClickListeners() {
        btnTrackStart.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                tracking = true;
                sendCommand("Tracking", "1");
                tvLocationStatus.setText("Tracking: Active");
                tvLocationStatus.setTextColor(0xFF00FF00);
            }
        });

        btnTrackStop.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                tracking = false;
                sendCommand("Tracking", "0");
                tvLocationStatus.setText("Tracking: Stopped");
                tvLocationStatus.setTextColor(0xFF888888);
            }
        });

        btnGeofenceOn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Geofence", "1");
            }
        });

        btnGeofenceOff.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Geofence", "0");
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
        fetchSensorData("Latitude", tvLatitude, "Latitude");
        fetchSensorData("Longitude", tvLongitude, "Longitude");
        fetchSensorData("Geofence", tvGeofenceStatus, "Geofence");
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
                                if ("Geofence".equals(apiTag)) {
                                    if ("1".equals(value)) {
                                        textView.setText(label + ": Active");
                                        textView.setTextColor(0xFF00FF00);
                                    } else {
                                        textView.setText(label + ": Inactive");
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
