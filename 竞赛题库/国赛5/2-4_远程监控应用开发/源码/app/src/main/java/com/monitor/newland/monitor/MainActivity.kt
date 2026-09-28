package com.monitor.newland.monitor

import android.Manifest
import android.app.AlarmManager
import android.app.PendingIntent
import android.app.TimePickerDialog
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import android.hardware.Camera
import android.media.AudioManager
import android.media.MediaPlayer
import android.os.Build
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.support.v4.app.ActivityCompat
import android.support.v4.content.ContextCompat
import android.support.v7.app.AppCompatActivity
import android.view.SurfaceHolder
import android.view.SurfaceView
import android.view.View
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import java.net.HttpURLConnection
import java.net.URL
import java.util.*
import kotlin.concurrent.thread

class MainActivity : AppCompatActivity(), SurfaceHolder.Callback {

    companion object {
        private const val REQUEST_CAMERA_PERMISSION = 100
        private const val PREFS_NAME = "monitor_settings"
    }

    private lateinit var tvMonitorStatus: TextView
    private lateinit var tvLightStatus: TextView
    private lateinit var surfaceCamera: SurfaceView
    private lateinit var layoutMonitorOff: LinearLayout
    private lateinit var btnStartMonitor: Button
    private lateinit var btnStopMonitor: Button
    private lateinit var layoutManualLight: LinearLayout
    private lateinit var layoutCameraControl: LinearLayout
    private lateinit var layoutAutoSettings: LinearLayout
    private lateinit var ivLightIndicator: ImageView
    private lateinit var btnLightOn: Button
    private lateinit var btnLightOff: Button
    private lateinit var btnUp: Button
    private lateinit var btnDown: Button
    private lateinit var btnLeft: Button
    private lateinit var btnRight: Button
    private lateinit var tvAutoOnTime: TextView
    private lateinit var tvAutoOffTime: TextView
    private lateinit var etRtsp: EditText
    private lateinit var etPtz: EditText
    private lateinit var btnSaveSettings: Button

    private var isMonitorOn = false
    private var isLightOn = false
    private var isSimulated = false

    private var camera: Camera? = null
    private var mediaPlayer: MediaPlayer? = null
    private var rtspUrl = ""
    private var ptzBaseUrl = ""
    private val handler = Handler(Looper.getMainLooper())
    private val prefs by lazy { getSharedPreferences(PREFS_NAME, MODE_PRIVATE) }

    private var autoOnHour = 18
    private var autoOnMinute = 0
    private var autoOffHour = 6
    private var autoOffMinute = 0

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        LightStateManager.loadState(this)
        isLightOn = LightStateManager.lightOn
        if (savedInstanceState != null) {
            isMonitorOn = savedInstanceState.getBoolean("is_monitor_on", false)
            isLightOn = savedInstanceState.getBoolean("is_light_on", isLightOn)
        }

        initViews()
        loadSettings()
        setupListeners()
        updateUI()
        if (isMonitorOn) {
            surfaceCamera.visibility = View.VISIBLE
            layoutMonitorOff.visibility = View.GONE
            connectCamera()
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putBoolean("is_monitor_on", isMonitorOn)
        outState.putBoolean("is_light_on", isLightOn)
    }

    private fun initViews() {
        tvMonitorStatus = findViewById(R.id.tv_monitor_status)
        tvLightStatus = findViewById(R.id.tv_light_status)
        surfaceCamera = findViewById(R.id.surface_camera)
        layoutMonitorOff = findViewById(R.id.layout_monitor_off)
        btnStartMonitor = findViewById(R.id.btn_start_monitor)
        btnStopMonitor = findViewById(R.id.btn_stop_monitor)
        layoutManualLight = findViewById(R.id.layout_manual_light)
        layoutCameraControl = findViewById(R.id.layout_camera_control)
        layoutAutoSettings = findViewById(R.id.layout_auto_settings)
        ivLightIndicator = findViewById(R.id.iv_light_indicator)
        btnLightOn = findViewById(R.id.btn_light_on)
        btnLightOff = findViewById(R.id.btn_light_off)
        btnUp = findViewById(R.id.btn_up)
        btnDown = findViewById(R.id.btn_down)
        btnLeft = findViewById(R.id.btn_left)
        btnRight = findViewById(R.id.btn_right)
        tvAutoOnTime = findViewById(R.id.tv_auto_on_time)
        tvAutoOffTime = findViewById(R.id.tv_auto_off_time)
        etRtsp = findViewById(R.id.et_rtsp)
        etPtz = findViewById(R.id.et_ptz)
        btnSaveSettings = findViewById(R.id.btn_save_settings)

        surfaceCamera.holder.addCallback(this)
    }

    private fun loadSettings() {
        autoOnHour = prefs.getInt("auto_on_hour", 18)
        autoOnMinute = prefs.getInt("auto_on_minute", 0)
        autoOffHour = prefs.getInt("auto_off_hour", 6)
        autoOffMinute = prefs.getInt("auto_off_minute", 0)
        rtspUrl = prefs.getString("rtsp_url", "") ?: ""
        ptzBaseUrl = prefs.getString("ptz_base_url", "") ?: ""
        updateAutoTimeDisplay()
    }

    private fun fillSettingFields() {
        etRtsp.setText(rtspUrl)
        etPtz.setText(ptzBaseUrl)
    }

    private fun updateAutoTimeDisplay() {
        tvAutoOnTime.text = String.format("%02d:%02d", autoOnHour, autoOnMinute)
        tvAutoOffTime.text = String.format("%02d:%02d", autoOffHour, autoOffMinute)
    }

    private fun setupListeners() {
        btnStartMonitor.setOnClickListener { startMonitor() }
        btnStopMonitor.setOnClickListener { stopMonitor() }
        btnLightOn.setOnClickListener { controlLight(true) }
        btnLightOff.setOnClickListener { controlLight(false) }
        btnUp.setOnClickListener { sendPTZCommand("上") }
        btnDown.setOnClickListener { sendPTZCommand("下") }
        btnLeft.setOnClickListener { sendPTZCommand("左") }
        btnRight.setOnClickListener { sendPTZCommand("右") }
        tvAutoOnTime.setOnClickListener { showTimePickerDialog(true) }
        tvAutoOffTime.setOnClickListener { showTimePickerDialog(false) }
        btnSaveSettings.setOnClickListener { saveAutoSettings() }
    }

    private fun showTimePickerDialog(isOnTime: Boolean) {
        val hour = if (isOnTime) autoOnHour else autoOffHour
        val minute = if (isOnTime) autoOnMinute else autoOffMinute

        TimePickerDialog(this, { _, selectedHour, selectedMinute ->
            if (isOnTime) {
                autoOnHour = selectedHour
                autoOnMinute = selectedMinute
            } else {
                autoOffHour = selectedHour
                autoOffMinute = selectedMinute
            }
            updateAutoTimeDisplay()
        }, hour, minute, true).show()
    }

    private fun saveAutoSettings() {
        rtspUrl = etRtsp.text.toString().trim()
        ptzBaseUrl = etPtz.text.toString().trim()
        prefs.edit()
            .putInt("auto_on_hour", autoOnHour)
            .putInt("auto_on_minute", autoOnMinute)
            .putInt("auto_off_hour", autoOffHour)
            .putInt("auto_off_minute", autoOffMinute)
            .putString("rtsp_url", rtspUrl)
            .putString("ptz_base_url", ptzBaseUrl)
            .apply()

        if (isMonitorOn) {
            scheduleAutoLight()
            if (mediaPlayer == null && camera == null) {
                connectCamera()
            }
        }
        Toast.makeText(this, "设置已保存", Toast.LENGTH_SHORT).show()
    }

    private fun startMonitor() {
        isMonitorOn = true
        surfaceCamera.visibility = View.VISIBLE
        layoutMonitorOff.visibility = View.GONE
        updateUI()
        connectCamera()
        scheduleAutoLight()
    }

    private fun stopMonitor() {
        isMonitorOn = false
        disconnectCamera()
        surfaceCamera.visibility = View.GONE
        layoutMonitorOff.visibility = View.VISIBLE
        cancelAutoLight()
        controlLight(false)
        updateUI()
    }

    private fun connectCamera() {
        try {
            val holder = surfaceCamera.holder
            if (!holder.surface.isValid) return
            if (rtspUrl.isNotBlank() && startRtspStream()) {
                return
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M &&
                ContextCompat.checkSelfPermission(this, Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED
            ) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.CAMERA),
                    REQUEST_CAMERA_PERMISSION
                )
                return
            }
            openCamera(holder)
        } catch (e: Exception) {
            e.printStackTrace()
            startSimulatedMonitor()
        }
    }

    private fun startRtspStream(): Boolean {
        return try {
            releaseMediaPlayer()
            val mp = MediaPlayer()
            mediaPlayer = mp
            mp.setAudioStreamType(AudioManager.STREAM_MUSIC)
            mp.setDataSource(rtspUrl)
            mp.setDisplay(surfaceCamera.holder)
            mp.setScreenOnWhilePlaying(true)
            mp.setOnPreparedListener { player ->
                player.start()
                isSimulated = false
                Toast.makeText(this, "摄像头已连接", Toast.LENGTH_SHORT).show()
            }
            mp.setOnInfoListener { _, what, _ ->
                if (what == MediaPlayer.MEDIA_INFO_VIDEO_RENDERING_START) {
                    isSimulated = false
                    Toast.makeText(this, "摄像头已连接", Toast.LENGTH_SHORT).show()
                }
                true
            }
            mp.setOnErrorListener { _, what, extra ->
                releaseMediaPlayer()
                Toast.makeText(this, "RTSP连接失败，使用模拟画面", Toast.LENGTH_LONG).show()
                startSimulatedMonitor()
                true
            }
            mp.prepareAsync()
            true
        } catch (e: Exception) {
            e.printStackTrace()
            releaseMediaPlayer()
            false
        }
    }

    private fun releaseMediaPlayer() {
        try {
            mediaPlayer?.run {
                if (isPlaying) stop()
                reset()
                release()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
        mediaPlayer = null
    }

    private fun openCamera(holder: SurfaceHolder) {
        try {
            val cam = Camera.open()

            val params = cam.parameters
            val sizes = params.supportedPreviewSizes
            if (sizes != null && sizes.isNotEmpty()) {
                params.setPreviewSize(sizes[0].width, sizes[0].height)
                cam.parameters = params
            }

            cam.setPreviewDisplay(holder)
            cam.startPreview()
            camera = cam
            isSimulated = false
            Toast.makeText(this, "摄像头已连接", Toast.LENGTH_SHORT).show()
        } catch (e: Exception) {
            e.printStackTrace()
            camera?.release()
            camera = null
            startSimulatedMonitor()
        }
    }

    private fun startSimulatedMonitor() {
        isSimulated = true
        Toast.makeText(this, "无摄像头设备，使用模拟监控画面", Toast.LENGTH_LONG).show()
        thread {
            try {
                while (isMonitorOn && isSimulated) {
                    val holder = surfaceCamera.holder
                    val surface = holder.surface
                    if (surface.isValid) {
                        val canvas = surface.lockCanvas(null)
                        if (canvas != null) {
                            drawSimulatedFrame(canvas)
                            surface.unlockCanvasAndPost(canvas)
                        }
                    }
                    Thread.sleep(80)
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }
    }

    private fun drawSimulatedFrame(canvas: Canvas) {
        val w = canvas.width.toFloat()
        val h = canvas.height.toFloat()

        val paint = Paint()
        paint.color = Color.parseColor("#1A1A2E")
        canvas.drawRect(0f, 0f, w, h, paint)

        paint.color = Color.parseColor("#222244")
        paint.strokeWidth = 2f
        for (i in 1..5) {
            val x = w * i / 6f
            canvas.drawLine(x, 0f, x, h, paint)
        }
        for (j in 1..5) {
            val y = h * j / 6f
            canvas.drawLine(0f, y, w, y, paint)
        }

        paint.color = Color.RED
        paint.style = Paint.Style.FILL
        canvas.drawCircle(w - 60f, 40f, 12f, paint)
        paint.color = Color.WHITE
        paint.textSize = 30f
        paint.textAlign = Paint.Align.LEFT
        canvas.drawText("REC", w - 42f, 48f, paint)

        paint.color = Color.parseColor("#AA44FF44")
        paint.style = Paint.Style.STROKE
        paint.strokeWidth = 3f
        canvas.drawCircle(w / 2f, h / 2f, 40f, paint)
        canvas.drawLine(w / 2f - 25f, h / 2f, w / 2f + 25f, h / 2f, paint)
        canvas.drawLine(w / 2f, h / 2f - 25f, w / 2f, h / 2f + 25f, paint)

        paint.color = Color.parseColor("#AAF0F0F0")
        paint.textSize = 24f
        paint.textAlign = Paint.Align.LEFT
        val now = Calendar.getInstance()
        val stamp = String.format(
            Locale.getDefault(),
            "%04d-%02d-%02d %02d:%02d:%02d",
            now.get(Calendar.YEAR), now.get(Calendar.MONTH) + 1,
            now.get(Calendar.DAY_OF_MONTH), now.get(Calendar.HOUR_OF_DAY),
            now.get(Calendar.MINUTE), now.get(Calendar.SECOND)
        )
        canvas.drawText(stamp, 12f, h - 18f, paint)
    }

    private fun disconnectCamera() {
        isSimulated = false
        releaseMediaPlayer()
        try {
            camera?.stopPreview()
            camera?.release()
        } catch (e: Exception) {
            e.printStackTrace()
        }
        camera = null
    }

    private fun sendPTZCommand(direction: String) {
        if (!isMonitorOn) {
            Toast.makeText(this, "请先开启监控系统", Toast.LENGTH_SHORT).show()
            return
        }
        if (ptzBaseUrl.isBlank()) {
            Toast.makeText(this, "摄像头方向: $direction（未配置PTZ控制地址）", Toast.LENGTH_LONG).show()
            return
        }
        Toast.makeText(this, "摄像头方向: $direction", Toast.LENGTH_SHORT).show()
        val code = when (direction) {
            "上" -> "up"
            "下" -> "down"
            "左" -> "left"
            "右" -> "right"
            else -> direction
        }
        val url = ptzBaseUrl.replace("{dir}", code)
        val okMsg = "云台" + direction + "控制成功"
        val netFailMsg = "云台" + direction + "控制失败：无法连接摄像头"
        thread {
            try {
                val conn = URL(url).openConnection() as HttpURLConnection
                conn.connectTimeout = 5000
                conn.readTimeout = 5000
                conn.requestMethod = "GET"
                val code2 = conn.responseCode
                conn.disconnect()
                handler.post {
                    if (isMonitorOn) {
                        val msg = if (code2 in 200..299) okMsg else "云台" + direction + "控制失败(" + code2 + ")"
                        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
                    }
                }
            } catch (e: Exception) {
                handler.post {
                    if (isMonitorOn) {
                        Toast.makeText(this, netFailMsg, Toast.LENGTH_LONG).show()
                    }
                }
            }
        }
    }

    private fun controlLight(on: Boolean) {
        LightStateManager.setLightOn(this, on)
        isLightOn = LightStateManager.lightOn
        updateUI()
        val msg = if (on) "路灯已开启" else "路灯已关闭"
        Toast.makeText(this, msg, Toast.LENGTH_SHORT).show()
    }

    private fun scheduleAutoLight() {
        val alarmManager = getSystemService(Context.ALARM_SERVICE) as AlarmManager

        val calendarOn = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, autoOnHour)
            set(Calendar.MINUTE, autoOnMinute)
            set(Calendar.SECOND, 0)
            if (timeInMillis <= System.currentTimeMillis()) {
                add(Calendar.DAY_OF_YEAR, 1)
            }
        }

        val calendarOff = Calendar.getInstance().apply {
            set(Calendar.HOUR_OF_DAY, autoOffHour)
            set(Calendar.MINUTE, autoOffMinute)
            set(Calendar.SECOND, 0)
            if (timeInMillis <= System.currentTimeMillis()) {
                add(Calendar.DAY_OF_YEAR, 1)
            }
        }

        val onIntent = Intent(this, LightReceiver::class.java).apply { action = LightReceiver.ACTION_LIGHT_ON }
        val onPendingIntent = PendingIntent.getBroadcast(
            this, 0, onIntent, PendingIntent.FLAG_UPDATE_CURRENT
        )

        val offIntent = Intent(this, LightReceiver::class.java).apply { action = LightReceiver.ACTION_LIGHT_OFF }
        val offPendingIntent = PendingIntent.getBroadcast(
            this, 1, offIntent, PendingIntent.FLAG_UPDATE_CURRENT
        )

        try {
            if (Build.VERSION.SDK_INT >= 23) {
                alarmManager.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP, calendarOn.timeInMillis, onPendingIntent
                )
                alarmManager.setExactAndAllowWhileIdle(
                    AlarmManager.RTC_WAKEUP, calendarOff.timeInMillis, offPendingIntent
                )
            } else {
                alarmManager.setRepeating(
                    AlarmManager.RTC_WAKEUP,
                    calendarOn.timeInMillis,
                    AlarmManager.INTERVAL_DAY,
                    onPendingIntent
                )
                alarmManager.setRepeating(
                    AlarmManager.RTC_WAKEUP,
                    calendarOff.timeInMillis,
                    AlarmManager.INTERVAL_DAY,
                    offPendingIntent
                )
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun cancelAutoLight() {
        val alarmManager = getSystemService(Context.ALARM_SERVICE) as AlarmManager

        val onIntent = Intent(this, LightReceiver::class.java).apply { action = LightReceiver.ACTION_LIGHT_ON }
        val onPendingIntent = PendingIntent.getBroadcast(
            this, 0, onIntent, PendingIntent.FLAG_UPDATE_CURRENT
        )
        alarmManager.cancel(onPendingIntent)
        onPendingIntent.cancel()

        val offIntent = Intent(this, LightReceiver::class.java).apply { action = LightReceiver.ACTION_LIGHT_OFF }
        val offPendingIntent = PendingIntent.getBroadcast(
            this, 1, offIntent, PendingIntent.FLAG_UPDATE_CURRENT
        )
        alarmManager.cancel(offPendingIntent)
        offPendingIntent.cancel()
    }

    private fun updateUI() {
        if (isMonitorOn) {
            tvMonitorStatus.text = "监控中"
            tvMonitorStatus.setTextColor(Color.parseColor("#4CAF50"))
            btnStartMonitor.visibility = View.GONE
            btnStopMonitor.visibility = View.VISIBLE
            layoutManualLight.visibility = View.GONE
            layoutCameraControl.visibility = View.VISIBLE
            layoutAutoSettings.visibility = View.VISIBLE
            fillSettingFields()
        } else {
            tvMonitorStatus.text = "监控已关闭"
            tvMonitorStatus.setTextColor(Color.parseColor("#F44336"))
            btnStartMonitor.visibility = View.VISIBLE
            btnStopMonitor.visibility = View.GONE
            layoutManualLight.visibility = View.VISIBLE
            layoutCameraControl.visibility = View.GONE
            layoutAutoSettings.visibility = View.GONE
        }

        if (isLightOn) {
            tvLightStatus.text = "路灯已开启"
            tvLightStatus.setTextColor(Color.parseColor("#FFC107"))
            ivLightIndicator.setImageResource(R.drawable.ic_light_bulb)
        } else {
            tvLightStatus.text = "路灯已关闭"
            tvLightStatus.setTextColor(Color.parseColor("#9E9E9E"))
            ivLightIndicator.setImageResource(R.drawable.ic_light_bulb_off)
        }
    }

    override fun surfaceCreated(holder: SurfaceHolder) {
        if (isMonitorOn) {
            connectCamera()
        }
    }

    override fun surfaceChanged(holder: SurfaceHolder, format: Int, width: Int, height: Int) {
        try {
            if (camera != null) {
                camera?.stopPreview()
                camera?.setPreviewDisplay(holder)
                camera?.startPreview()
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    override fun surfaceDestroyed(holder: SurfaceHolder) {
        disconnectCamera()
    }

    override fun onRequestPermissionsResult(requestCode: Int, permissions: Array<out String>, grantResults: IntArray) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults)
        if (requestCode == REQUEST_CAMERA_PERMISSION) {
            if (grantResults.isNotEmpty() && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
                connectCamera()
            } else {
                startSimulatedMonitor()
                Toast.makeText(this, "未获得摄像头权限，使用模拟监控画面", Toast.LENGTH_LONG).show()
            }
        }
    }

    override fun onResume() {
        super.onResume()
        loadSettings()
        if (isMonitorOn && camera == null && mediaPlayer == null) {
            connectCamera()
        }
    }

    override fun onPause() {
        super.onPause()
        if (isMonitorOn) {
            disconnectCamera()
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        isSimulated = false
        disconnectCamera()
    }
}
