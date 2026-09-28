package com.forest.newland.fire

import android.media.AudioManager
import android.media.ToneGenerator
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.os.Vibrator
import android.support.v4.content.ContextCompat
import android.support.v7.app.AppCompatActivity
import android.view.View
import android.view.animation.AlphaAnimation
import android.widget.Toast
import kotlinx.android.synthetic.main.activity_main.*

class MainActivity : AppCompatActivity() {

    private companion object {
        const val PREFS = "forest_settings"
        const val KEY_SERVER = "server_url"
        const val KEY_TAG = "sensor_tag"
        const val KEY_INTERVAL = "refresh_interval"
        const val KEY_THRESHOLD = "threshold"
        const val KEY_MODE = "mode"
        const val DEFAULT_SERVER = "https://api.nlecloud.com"
        const val DEFAULT_TAG = "m_A-Q2"
        const val DEFAULT_ACCOUNT = "13329262958"
        const val DEFAULT_THRESHOLD = 50.0
    }

    private val mainHandler = Handler(Looper.getMainLooper())

    private var client: CloudClient? = null
    private var pollInterval = 5000L
    private var threshold = DEFAULT_THRESHOLD
    private var sensorTag = DEFAULT_TAG
    private var isLoggedIn = false
    private var pollingStarted = false
    private var isAlarmActive = false
    private var toneGenerator: ToneGenerator? = null
    private var alarmThread: Thread? = null
    private var alarmRunning = false

    private val pollTask = object : Runnable {
        override fun run() {
            if (isLoggedIn) {
                refreshData()
                mainHandler.postDelayed(this, pollInterval)
            }
        }
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        loadSettings()
        bindViews()

        if (savedInstanceState != null && savedInstanceState.getBoolean("logged_in", false)) {
            et_account.setText(savedInstanceState.getString("account") ?: "")
            et_password.setText(savedInstanceState.getString("password") ?: "")
            val account = et_account.text.toString().trim()
            val pwd = et_password.text.toString().trim()
            loginInternal(account, pwd, quiet = true)
        } else {
            showLogin()
        }
    }

    override fun onSaveInstanceState(outState: Bundle) {
        super.onSaveInstanceState(outState)
        outState.putBoolean("logged_in", isLoggedIn)
        outState.putString("account", et_account.text.toString().trim())
        outState.putString("password", et_password.text.toString().trim())
    }

    override fun onDestroy() {
        super.onDestroy()
        stopPolling()
        stopAlarm()
    }

    private fun bindViews() {
        btn_login.setOnClickListener { doLogin() }
        btn_settings.setOnClickListener {
            fillSettingsFields()
            overlay_settings.visibility = View.VISIBLE
        }
        btn_save_settings.setOnClickListener { saveSettings() }
        btn_logout.setOnClickListener { doLogout() }
    }

    private fun loadSettings() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        pollInterval = (prefs.getInt(KEY_INTERVAL, 5).coerceAtLeast(2)) * 1000L
        threshold = prefs.getFloat(KEY_THRESHOLD, DEFAULT_THRESHOLD.toFloat()).toDouble()
        sensorTag = prefs.getString(KEY_TAG, DEFAULT_TAG) ?: DEFAULT_TAG
    }

    private fun fillSettingsFields() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        et_server.setText(prefs.getString(KEY_SERVER, DEFAULT_SERVER) ?: DEFAULT_SERVER)
        et_sensor_tag.setText(prefs.getString(KEY_TAG, DEFAULT_TAG) ?: DEFAULT_TAG)
        et_interval.setText((pollInterval / 1000).toString())
        et_threshold.setText(threshold.toString())
        if (prefs.getString(KEY_MODE, "cloud") == "demo") {
            rb_mode_demo.isChecked = true
        } else {
            rb_mode_cloud.isChecked = true
        }
    }

    private fun saveSettings() {
        val server = et_server.text.toString().trim()
        val tag = et_sensor_tag.text.toString().trim()
        val interval = et_interval.text.toString().trim().toIntOrNull() ?: 5
        val th = et_threshold.text.toString().trim().toDoubleOrNull() ?: threshold
        val mode = if (rb_mode_demo.isChecked) "demo" else "cloud"

        getSharedPreferences(PREFS, MODE_PRIVATE)
            .edit()
            .putString(KEY_SERVER, server)
            .putString(KEY_TAG, tag)
            .putInt(KEY_INTERVAL, interval.coerceAtLeast(2))
            .putFloat(KEY_THRESHOLD, th.toFloat())
            .putString(KEY_MODE, mode)
            .apply()

        pollInterval = interval.coerceAtLeast(2) * 1000L
        threshold = th
        sensorTag = tag
        overlay_settings.visibility = View.GONE
        Toast.makeText(this, "设置已保存", Toast.LENGTH_SHORT).show()

        if (isLoggedIn) {
            refreshData()
        }
    }

    private fun showLogin() {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        val lastAccount = prefs.getString("last_account", "")
        et_account.setText(
            if (lastAccount.isNullOrBlank() || lastAccount == "demo") DEFAULT_ACCOUNT else lastAccount
        )
        et_password.setText("")
        overlay_login.visibility = View.VISIBLE
    }

    private fun doLogin() {
        val account = et_account.text.toString().trim()
        val pwd = et_password.text.toString().trim()
        if (account.isEmpty() || pwd.isEmpty()) {
            Toast.makeText(this, "请输入用户名和密码", Toast.LENGTH_SHORT).show()
            return
        }
        loginInternal(account, pwd, quiet = false)
    }

    private fun loginInternal(account: String, pwd: String, quiet: Boolean) {
        val prefs = getSharedPreferences(PREFS, MODE_PRIVATE)
        val server = prefs.getString(KEY_SERVER, DEFAULT_SERVER) ?: DEFAULT_SERVER
        val mode = prefs.getString(KEY_MODE, "cloud") ?: "cloud"

        val newClient = createClient(mode, server, account, pwd)
        pb_loading.visibility = View.VISIBLE
        btn_login.isEnabled = false

        Thread {
            val ok = newClient.login(account, pwd)
            mainHandler.post {
                pb_loading.visibility = View.GONE
                btn_login.isEnabled = true
                if (ok) {
                    client = newClient
                    isLoggedIn = true
                    overlay_login.visibility = View.GONE
                    tv_user.text = getString(R.string.user_label) + "：" + account +
                            if (mode == "demo") "（模拟测试）" else ""
                    getSharedPreferences(PREFS, MODE_PRIVATE)
                        .edit().putString("last_account", account).apply()
                    Toast.makeText(this, "登录成功", Toast.LENGTH_SHORT).show()
                    startPolling()
                } else {
                    if (quiet) {
                        isLoggedIn = false
                        showLogin()
                    }
                    Toast.makeText(this, "登录失败：" + newClient.lastError, Toast.LENGTH_LONG).show()
                }
            }
        }.start()
    }

    private fun doLogout() {
        stopPolling()
        stopAlarm()
        client = null
        isLoggedIn = false
        setNormalState()
        tv_smoke.text = "--"
        tv_time.text = getString(R.string.collect_time_label) + "：--"
        showLogin()
        Toast.makeText(this, "已注销，请重新登录", Toast.LENGTH_SHORT).show()
    }

    private fun startPolling() {
        if (!pollingStarted) {
            pollingStarted = true
            mainHandler.post(pollTask)
        }
    }

    private fun stopPolling() {
        pollingStarted = false
        mainHandler.removeCallbacks(pollTask)
    }

    private fun refreshData() {
        val currentClient = client ?: return
        val tag = sensorTag
        Thread {
            val data = currentClient.fetchSensor(tag)
            mainHandler.post {
                if (!isLoggedIn) return@post
                if (data != null) {
                    tv_smoke.text = String.format("%.1f", data.value)
                    tv_time.text = getString(R.string.collect_time_label) + "：" + data.time
                    if (data.value >= threshold) {
                        triggerAlarm()
                    } else {
                        setNormalState()
                    }
                } else {
                    val err = currentClient.lastError
                    val msg = if (err.contains("未获取到传感器")) "暂无 $tag 数据" else "读取失败"
                    tv_time.text = getString(R.string.collect_time_label) + "：" + msg
                }
            }
        }.start()
    }

    private fun triggerAlarm() {
        if (isAlarmActive) return

        isAlarmActive = true
        tv_fire_status.text = getString(R.string.fire_status_alarm)
        tv_fire_status.setTextColor(ContextCompat.getColor(this, R.color.fire_alarm))
        main_bg.background = ContextCompat.getDrawable(this, R.drawable.bg_forest_fire)
        tv_fire_icon.text = "🔥"
        tv_big_status.setTextColor(ContextCompat.getColor(this, R.color.fire_alarm))
        tv_big_status.text = getString(R.string.fire_status_alarm)

        tv_led.text = getString(R.string.led_text_alarm)
        tv_led.setTextColor(ContextCompat.getColor(this, R.color.led_text_alarm))
        tv_led.requestFocus()

        val blink = AlphaAnimation(0.15f, 1f)
        blink.duration = 300
        blink.repeatMode = android.view.animation.Animation.REVERSE
        blink.repeatCount = android.view.animation.Animation.INFINITE
        tv_led.startAnimation(blink)

        tv_alarm_status.text = getString(R.string.alarm_active)
        tv_alarm_status.setTextColor(ContextCompat.getColor(this, R.color.fire_alarm))

        startAlarmSound()
        vibrateRepeatedly()
    }

    private fun setNormalState() {
        if (!isAlarmActive) return

        isAlarmActive = false
        stopAlarm()
        tv_led.clearAnimation()
        tv_fire_status.text = getString(R.string.fire_status_normal)
        tv_fire_status.setTextColor(ContextCompat.getColor(this, R.color.fire_ok))
        main_bg.background = ContextCompat.getDrawable(this, R.drawable.bg_forest_normal)
        tv_fire_icon.text = "🌲"
        tv_big_status.setTextColor(ContextCompat.getColor(this, R.color.fire_ok))
        tv_big_status.text = getString(R.string.fire_status_normal)

        tv_led.text = getString(R.string.led_text_normal)
        tv_led.setTextColor(ContextCompat.getColor(this, R.color.led_text))

        tv_alarm_status.text = getString(R.string.no_alarm_status)
        tv_alarm_status.setTextColor(ContextCompat.getColor(this, R.color.fire_ok))
    }

    private fun startAlarmSound() {
        stopAlarm()
        alarmRunning = true
        toneGenerator = ToneGenerator(AudioManager.STREAM_ALARM, 90)
        alarmThread = Thread {
            try {
                while (alarmRunning) {
                    toneGenerator?.startTone(ToneGenerator.TONE_CDMA_ALERT_CALL_GUARD, 500)
                    Thread.sleep(700)
                }
            } catch (e: Exception) {
                e.printStackTrace()
            }
        }.apply { start() }
    }

    private fun vibrateRepeatedly() {
        val vibrator = getSystemService(VIBRATOR_SERVICE) as Vibrator
        try {
            vibrator.vibrate(longArrayOf(0, 500, 400), 2)
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    private fun stopAlarm() {
        alarmRunning = false
        alarmThread?.interrupt()
        alarmThread = null
        try {
            toneGenerator?.release()
        } catch (e: Exception) {
            e.printStackTrace()
        }
        toneGenerator = null
    }

    override fun onResume() {
        super.onResume()
        if (isLoggedIn && !pollingStarted) {
            startPolling()
        }
    }
}