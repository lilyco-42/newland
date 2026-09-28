package com.nlecloud.materialmonitor;



import android.animation.ObjectAnimator;

import android.os.Bundle;

import android.os.Handler;

import android.view.View;

import android.view.animation.LinearInterpolator;

import android.widget.Button;

import android.widget.ImageView;

import android.widget.TextView;

import android.widget.Toast;



import android.support.v7.app.AppCompatActivity;



import java.io.BufferedReader;

import java.io.InputStreamReader;

import java.io.OutputStream;

import java.net.HttpURLConnection;

import java.net.URL;



public class MainActivity extends AppCompatActivity {

    

    private static final String API_BASE = "http://api.nlecloud.com";

    private static final String DEVICE_ID = "YOUR_DEVICE_ID";

    private static final String ACCESS_TOKEN = "YOUR_ACCESS_TOKEN";

    private static final int SPEED_MIN_THRESHOLD = 200;

    private static final int SPEED_MAX_THRESHOLD = 800;

    private static final int REFRESH_INTERVAL = 2000;

    

    private TextView tvSpeed, tvSpeedStatus, tvStirrerStatus;

    private TextView tvMicroSwitch, tvPushrodStatus, tvAlarmStatus, tvWarning;

    private TextView tvMinThreshold, tvMaxThreshold;

    private View viewAlarmLED, viewMicroSwitch;

    private View viewRedLight, viewYellowLight, viewGreenLight;

    private ImageView imgStirrer;

    private Button btnStart, btnStop;

    

    private Handler refreshHandler;

    private ObjectAnimator stirrerAnimator;

    

    private int currentSpeed = 0;

    private boolean microSwitchOn = false;

    private boolean motorRunning = false;

    

    @Override

    protected void onCreate(Bundle savedInstanceState) {

        super.onCreate(savedInstanceState);

        setContentView(R.layout.activity_main);

        

        initViews();

        setupListeners();

        refreshHandler = new Handler();

        

        startDataRefresh();

    }

    

    private void initViews() {

        tvSpeed = findViewById(R.id.tvSpeed);

        tvSpeedStatus = findViewById(R.id.tvSpeedStatus);

        tvStirrerStatus = findViewById(R.id.tvStirrerStatus);

        tvMicroSwitch = findViewById(R.id.tvMicroSwitch);

        tvPushrodStatus = findViewById(R.id.tvPushrodStatus);

        tvAlarmStatus = findViewById(R.id.tvAlarmStatus);

        tvWarning = findViewById(R.id.tvWarning);

        tvMinThreshold = findViewById(R.id.tvMinThreshold);

        tvMaxThreshold = findViewById(R.id.tvMaxThreshold);

        

        viewAlarmLED = findViewById(R.id.viewAlarmLED);

        viewMicroSwitch = findViewById(R.id.viewMicroSwitch);

        viewRedLight = findViewById(R.id.viewRedLight);

        viewYellowLight = findViewById(R.id.viewYellowLight);

        viewGreenLight = findViewById(R.id.viewGreenLight);

        

        imgStirrer = findViewById(R.id.imgStirrer);

        btnStart = findViewById(R.id.btnStart);

        btnStop = findViewById(R.id.btnStop);

    }

    

    private void setupListeners() {

        btnStart.setOnClickListener(v -> startMotor());

        btnStop.setOnClickListener(v -> pauseMotor());

    }

    

    private void startDataRefresh() {

        refreshHandler.postDelayed(new Runnable() {

            @Override

            public void run() {

                fetchData();

                refreshHandler.postDelayed(this, REFRESH_INTERVAL);

            }

        }, 0);

    }

    

    private void fetchData() {

        new Thread(() -> {

            try {

                URL url = new URL(API_BASE + "/Devices/" + DEVICE_ID + "/Datas");

                HttpURLConnection conn = (HttpURLConnection) url.openConnection();

                conn.setRequestMethod("GET");

                conn.setRequestProperty("AccessToken", ACCESS_TOKEN);

                

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

                    

                    parseData(response.toString());

                }

            } catch (Exception e) {

                e.printStackTrace();

            }

        }).start();

    }

    

    private void parseData(String json) {

        try {

            int speedIdx = json.indexOf("Speed");

            if (speedIdx > 0) {

                int start = json.indexOf(":", speedIdx) + 1;

                int end = json.indexOf(",", start);

                if (end == -1) end = json.indexOf("}", start);

                currentSpeed = Integer.parseInt(json.substring(start, end).trim());

            }

            

            int switchIdx = json.indexOf("MicroSwitch");

            if (switchIdx > 0) {

                int start = json.indexOf(":", switchIdx) + 1;

                int end = json.indexOf(",", start);

                if (end == -1) end = json.indexOf("}", start);

                microSwitchOn = Integer.parseInt(json.substring(start, end).trim()) > 0;

            }

        } catch (Exception e) {

            e.printStackTrace();

        }

        

        runOnUiThread(this::updateUI);

    }

    

    private void updateUI() {

        tvSpeed.setText(String.valueOf(currentSpeed));

        

        if (currentSpeed > SPEED_MAX_THRESHOLD) {

            tvSpeed.setTextColor(0xFFFF0000);

            tvSpeedStatus.setText("...");

            tvSpeedStatus.setTextColor(0xFFFF0000);

            setAlarm(true, "SPEED ALARM");

            setTriColorLight(true, false, false); // 

        } else if (currentSpeed < SPEED_MIN_THRESHOLD) {

            tvSpeed.setTextColor(0xFFFFD93D);

            tvSpeedStatus.setText("...");

            setTriColorLight(false, true, false); // 

            autoRefill();

        } else {

            tvSpeed.setTextColor(0xFF4ECDC4);

            tvSpeedStatus.setText("...");

            setTriColorLight(false, false, true); // 

        }

        

        // 

        updateStirrerAnimation();

        

        viewMicroSwitch.setBackgroundColor(microSwitchOn ? 0xFF00FF00 : 0xFF555555);

        tvMicroSwitch.setText(microSwitchOn ? "ON" : "OFF");

        tvMicroSwitch.setTextColor(microSwitchOn ? 0xFF00FF00 : 0xFFAAAAAA);

        

        if (microSwitchOn && motorRunning) {

            pauseMotor();

        }

    }

    

    private void updateStirrerAnimation() {
        if (currentSpeed > 0 && motorRunning) {
            if (stirrerAnimator == null || !stirrerAnimator.isRunning()) {
                long duration = Math.max(100, 2000 - currentSpeed * 2);
                stirrerAnimator = ObjectAnimator.ofFloat(imgStirrer, "rotation", 0f, 360f);
                stirrerAnimator.setDuration(duration);
                stirrerAnimator.setRepeatCount(ObjectAnimator.INFINITE);
                stirrerAnimator.setInterpolator(new LinearInterpolator());
                stirrerAnimator.start();
            }
            if (currentSpeed > SPEED_MAX_THRESHOLD) {
                tvStirrerStatus.setText("TOO FAST");
                tvStirrerStatus.setTextColor(0xFFFF5555);
            } else if (currentSpeed < SPEED_MIN_THRESHOLD) {
                tvStirrerStatus.setText("TOO SLOW");
                tvStirrerStatus.setTextColor(0xFFFFD93D);
            } else {
                tvStirrerStatus.setText("NORMAL");
                tvStirrerStatus.setTextColor(0xFFAAAAAA);
            }
        }
    }

    

    private void setAlarm(boolean on, String message) {

        viewAlarmLED.setBackgroundColor(on ? 0xFFFF0000 : 0xFF555555);

        tvAlarmStatus.setText(on ? "ON" : "OFF");

        tvAlarmStatus.setTextColor(on ? 0xFFFF0000 : 0xFF00FF00);

        tvWarning.setText(message);

        tvWarning.setTextColor(on ? 0xFFFF5555 : 0xFF00FF00);

        

        sendCommand("AlarmLED", on ? "1" : "0");

    }

    

    private void setTriColorLight(boolean red, boolean yellow, boolean green) {

        viewRedLight.setBackgroundColor(red ? 0xFFFF0000 : 0xFF555555);

        viewYellowLight.setBackgroundColor(yellow ? 0xFFFFD93D : 0xFF555555);

        viewGreenLight.setBackgroundColor(green ? 0xFF00FF00 : 0xFF555555);

        

        sendCommand("TriColorLight", (red ? "R" : "") + (yellow ? "Y" : "") + (green ? "G" : ""));

    }

    

    private void autoRefill() {

        //  - 

        tvPushrodStatus.setText("...");

        tvPushrodStatus.setTextColor(0xFF4ECDC4);

        sendCommand("Pushrod", "1");

        

        new Handler().postDelayed(() -> {

            tvPushrodStatus.setText("STANDBY");

            tvPushrodStatus.setTextColor(0xFFAAAAAA);

            sendCommand("Pushrod", "0");

        }, 3000);

    }

    

    private void startMotor() {

        motorRunning = true;

        btnStart.setEnabled(false);

        btnStop.setEnabled(true);

        sendCommand("Motor", "0");
        Toast.makeText(this, "Motor stopped", Toast.LENGTH_SHORT).show();

    }

    

    private void pauseMotor() {

        motorRunning = false;

        tvPushrodStatus.setText("...");

        tvPushrodStatus.setTextColor(0xFFFFD93D);

    }

    

    private void sendCommand(String apiTag, String value) {

        new Thread(() -> {

            try {

                JSONObject jsonBody = new JSONObject();

                jsonBody.put("apiTag", apiTag);

                jsonBody.put("value", value);

                

                URL url = new URL(API_BASE + "/Cmds");

                HttpURLConnection conn = (HttpURLConnection) url.openConnection();

                conn.setRequestMethod("POST");

                conn.setRequestProperty("Content-Type", "application/json");

                conn.setRequestProperty("AccessToken", ACCESS_TOKEN);

                conn.setDoOutput(true);

                

                OutputStream os = conn.getOutputStream();

                os.write(jsonBody.toString().getBytes());

                os.flush();

                os.close();

                

                conn.getResponseCode();

            } catch (Exception e) {

                e.printStackTrace();

            }

        }).start();

    }

    

    @Override

    protected void onDestroy() {

        super.onDestroy();

        refreshHandler.removeCallbacksAndMessages(null);

        if (stirrerAnimator != null) {

            stirrerAnimator.cancel();

        }

    }

    

    private static class JSONObject {

        private StringBuilder sb = new StringBuilder();

        

        public JSONObject() {

            sb.append("{");

        }

        

        public JSONObject put(String key, String value) {

            if (sb.length() > 1) sb.append(",");

            sb.append("\"").append(key).append("\":\"").append(value).append("\"");

            return this;

        }

        

        @Override

        public String toString() {

            return sb.append("}").toString();

        }

    }

}


