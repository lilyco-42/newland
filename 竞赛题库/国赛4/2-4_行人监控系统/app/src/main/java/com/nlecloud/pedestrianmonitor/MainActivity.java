package com.nlecloud.pedestrianmonitor;

import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.support.constraint.ConstraintLayout;
import android.support.v7.app.AppCompatActivity;
import android.view.View;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;
import android.net.Uri;
import android.util.Base64;
import android.widget.VideoView;
import java.security.MessageDigest;
import java.security.SecureRandom;
import java.util.TimeZone;
import org.json.JSONObject;
import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;

/**
 * Pedestrian Monitoring System
 * Features: Camera-based pedestrian detection, alarm management
 * Monitors pedestrian traffic and triggers alerts
 */
public class MainActivity extends AppCompatActivity {

    private static final String BASE_URL = "http://api.nlecloud.com";
    private static final String ACCESS_TOKEN = "your_access_token_here";
    private static final String DEVICE_ID = "your_device_id_here";

    private TextView tvPedestrianCount;
    private TextView tvCameraStatus;
    private TextView tvAlarmStatus;
    private TextView tvDetectionStatus;
    private Button btnCameraOn;
    private Button btnCameraOff;
    private Button btnAlarmArm;
    private Button btnAlarmDisarm;
    private Button btnDetectionStart;
    private Button btnDetectionStop;
    private Button btnRefresh;

    private Handler handler;
    private VideoView videoView;
    private String onvifProfileToken;
    private static final String RTSP_URL = "rtsp://172.18.1.13:554/stream2";
    private static final String ONVIF_URL = "http://172.18.1.13/onvif/device_service";
    private Runnable dataFetchRunnable;
    private boolean isFetching = false;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        handler = new Handler(Looper.getMainLooper());

        initViews();
        setupClickListeners();

        Toast.makeText(this, "Pedestrian Monitor Started", Toast.LENGTH_SHORT).show();
    }

    private void initViews() {
        videoView = findViewById(R.id.video_view);
        tvPedestrianCount = findViewById(R.id.tv_pedestrian_count);
        tvCameraStatus = findViewById(R.id.tv_camera_status);
        tvAlarmStatus = findViewById(R.id.tv_alarm_status);
        tvDetectionStatus = findViewById(R.id.tv_detection_status);
        btnCameraOn = findViewById(R.id.btn_camera_on);
        btnCameraOff = findViewById(R.id.btn_camera_off);
        btnAlarmArm = findViewById(R.id.btn_alarm_arm);
        btnAlarmDisarm = findViewById(R.id.btn_alarm_disarm);
        btnDetectionStart = findViewById(R.id.btn_detection_start);
        btnDetectionStop = findViewById(R.id.btn_detection_stop);
        btnRefresh = findViewById(R.id.btn_refresh);
    }

    private void setupClickListeners() {
        btnCameraOn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startCamera();
            }
        });

        btnCameraOff.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                stopCamera();
            }
        });

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

        btnDetectionStart.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Detection", "1");
            }
        });

        btnDetectionStop.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                sendCommand("Detection", "0");
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
        fetchSensorData("PedestrianCount", tvPedestrianCount, "Pedestrian Count", " persons");
        fetchSensorData("Camera", tvCameraStatus, "Camera", "");
        fetchSensorData("Alarm", tvAlarmStatus, "Alarm", "");
        fetchSensorData("Detection", tvDetectionStatus, "Detection", "");
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
                                if ("Camera".equals(apiTag) || "Alarm".equals(apiTag)
                                        || "Detection".equals(apiTag)) {
                                    if ("1".equals(value)) {
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


    private void startCamera() {
        try {
            videoView.setVideoURI(Uri.parse(RTSP_URL));
            videoView.start();
            Toast.makeText(this, "Camera stream starting...", Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            Toast.makeText(this, "Camera error: " + e.getMessage(), Toast.LENGTH_SHORT).show();
        }
    }

    private void stopCamera() {
        try {
            videoView.stopPlayback();
            Toast.makeText(this, "Camera stopped", Toast.LENGTH_SHORT).show();
        } catch (Exception e) {
            e.printStackTrace();
        }
    }

    private void sendPtz(final String direction) {
        Toast.makeText(this, "PTZ " + direction + "...", Toast.LENGTH_SHORT).show();
        new Thread(new Runnable() {
            @Override
            public void run() {
                final boolean ok = onvifPtz(direction);
                handler.post(new Runnable() {
                    @Override
                    public void run() {
                        if (ok) {
                            Toast.makeText(MainActivity.this,
                                    "PTZ " + direction + " OK", Toast.LENGTH_SHORT).show();
                        } else {
                            Toast.makeText(MainActivity.this,
                                    "PTZ " + direction + " failed", Toast.LENGTH_SHORT).show();
                        }
                    }
                });
            }
        }).start();
    }

    private String onvifPost(String body) throws Exception {
        // WS-Security UsernameToken (PasswordDigest), admin / empty password
        byte[] nonce = new byte[16];
        new SecureRandom().nextBytes(nonce);
        java.text.SimpleDateFormat sdf =
                new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'");
        sdf.setTimeZone(TimeZone.getTimeZone("GMT"));
        String created = sdf.format(new java.util.Date());
        MessageDigest sha1 = MessageDigest.getInstance("SHA-1");
        sha1.update("".getBytes("UTF-8"));
        sha1.update(nonce);
        sha1.update(created.getBytes("UTF-8"));
        String digest = Base64.encodeToString(sha1.digest(), Base64.NO_WRAP);
        String nonceB64 = Base64.encodeToString(nonce, Base64.NO_WRAP);

        String xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
                + "<s:Envelope xmlns:s=\"http://www.w3.org/2003/05/soap-envelope\""
                + " xmlns:tds=\"http://www.onvif.org/ver10/device/wsdl\""
                + " xmlns:trt=\"http://www.onvif.org/ver10/media/wsdl\""
                + " xmlns:trp=\"http://www.onvif.org/ver20/ptz/wsdl\""
                + " xmlns:tt=\"http://www.onvif.org/ver10/schema\">"
                + "<s:Header><wsse:Security xmlns:wsse=\"http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-secext-1.0.xsd\" s:mustUnderstand=\"1\">"
                + "<wsse:UsernameToken>"
                + "<wsse:Username>admin</wsse:Username>"
                + "<wsse:Password Type=\"http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-username-token-profile-1.0#PasswordDigest\">" + digest + "</wsse:Password>"
                + "<wsse:Nonce EncodingType=\"http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-soap-message-security-1.0#Base64Binary\">" + nonceB64 + "</wsse:Nonce>"
                + "<wsu:Created xmlns:wsu=\"http://docs.oasis-open.org/wss/2004/01/oasis-200401-wss-wssecurity-utility-1.0.xsd\">" + created + "</wsu:Created>"
                + "</wsse:UsernameToken></wsse:Security></s:Header>"
                + "<s:Body>" + body + "</s:Body></s:Envelope>";

        URL url = new URL(ONVIF_URL);
        HttpURLConnection conn = (HttpURLConnection) url.openConnection();
        conn.setRequestMethod("POST");
        conn.setConnectTimeout(3000);
        conn.setReadTimeout(3000);
        conn.setDoOutput(true);
        conn.setRequestProperty("Content-Type", "application/soap+xml; charset=utf-8");
        OutputStream os = conn.getOutputStream();
        os.write(xml.getBytes("UTF-8"));
        os.flush();
        os.close();
        int code = conn.getResponseCode();
        java.io.InputStream in = code >= 400 ? conn.getErrorStream() : conn.getInputStream();
        StringBuilder sb = new StringBuilder();
        if (in != null) {
            BufferedReader br = new BufferedReader(new InputStreamReader(in, "UTF-8"));
            String line;
            while ((line = br.readLine()) != null) {
                sb.append(line);
            }
            br.close();
        }
        conn.disconnect();
        String resp = sb.toString();
        if (code != 200 || resp.contains("faultstring")) {
            throw new Exception("ONVIF HTTP " + code);
        }
        return resp;
    }

    private boolean onvifPtz(String direction) {
        try {
            if (onvifProfileToken == null) {
                String resp = onvifPost("<trt:GetProfiles/>");
                int i = resp.indexOf("token=\"");
                if (i < 0) {
                    return false;
                }
                int start = i + 7;
                int end = resp.indexOf('"', start);
                onvifProfileToken = resp.substring(start, end);
            }
            double vx = 0.0;
            double vy = 0.0;
            if ("LEFT".equals(direction)) {
                vx = -0.5;
            } else if ("RIGHT".equals(direction)) {
                vx = 0.5;
            } else if ("UP".equals(direction)) {
                vy = 0.5;
            } else if ("DOWN".equals(direction)) {
                vy = -0.5;
            }
            onvifPost("<trp:ContinuousMove><trp:ProfileToken>" + onvifProfileToken
                    + "</trp:ProfileToken><trp:Velocity><tt:PanTilt x=\"" + vx
                    + "\" y=\"" + vy + "\"/></trp:Velocity></trp:ContinuousMove>");
            Thread.sleep(500);
            onvifPost("<trp:Stop><trp:ProfileToken>" + onvifProfileToken
                    + "</trp:ProfileToken><trp:PanTilt>true</trp:PanTilt><trp:Zoom>false</trp:Zoom></trp:Stop>");
            return true;
        } catch (Exception e) {
            e.printStackTrace();
            return false;
        }
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
