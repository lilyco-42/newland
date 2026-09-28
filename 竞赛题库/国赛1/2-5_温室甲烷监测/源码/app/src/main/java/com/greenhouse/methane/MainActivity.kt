package com.greenhouse.methane

import android.app.AlertDialog
import android.content.Context
import android.content.SharedPreferences
import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.support.v7.app.AppCompatActivity
import android.view.LayoutInflater
import android.view.View
import android.view.animation.Animation
import android.view.animation.LinearInterpolator
import android.view.animation.RotateAnimation
import android.widget.Button
import android.widget.EditText
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import android.widget.Toast
import kotlin.concurrent.thread

/**
 * 子任务2-5 温室培育甲烷气体监测系统 主界面。
 *
 * 界面结构（单 Activity + 登录遮罩 + 主界面）：
 *   - 图1 登录页：模态遮罩覆盖在主界面之上；右上角设置按钮 -> 图3 设置弹窗；
 *     点击“登录”用云服务用户名密码验证，成功后关闭遮罩显示图2 主界面。
 *   - 图2 主界面：显示甲烷实时值与阈值；风扇图片在超标时旋转(动画)、
 *     低于阈值时停止；支持 自动/手动 两种模式控制风扇；可注销退出，
 *     再次进入主界面需要重新登录。
 */
class MainActivity : AppCompatActivity() {

    private lateinit var prefs: SharedPreferences
    private lateinit var cloud: CloudApi
    private val handler = Handler(Looper.getMainLooper())

    // 主界面控件
    private lateinit var tvMethane: TextView
    private lateinit var tvThreshold: TextView
    private lateinit var tvMode: TextView
    private lateinit var ivFan: ImageView
    private lateinit var btnMode: Button
    private lateinit var btnFanOn: Button
    private lateinit var btnFanOff: Button
    private lateinit var btnLogout: Button

    // 登录遮罩控件
    private lateinit var loginMask: LinearLayout
    private lateinit var etUser: EditText
    private lateinit var etPass: EditText
    private lateinit var btnLogin: Button
    private lateinit var btnOpenSettings: Button

    // 运行状态
    private var logged = false
    private var autoMode = true          // 默认自动
    private var fanOn = false
    private var fanRotAnim: RotateAnimation? = null
    private var pollRunnable: Runnable? = null

    // 配置项（SharedPreferences 持久化）
    private var serverUrl = "http://192.168.0.138"
    private var threshold = 25.0
    private var sensorTag = "m_Methane1"
    private var fanTag = "z_fan"          // 风扇执行器标识，按工位实际配置
    private var devId = 0

    companion object {
        const val PREFS = "greenhouse_prefs"
        const val POLL_MS = 3000L         // 甲烷数据刷新周期
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)
        prefs = getSharedPreferences(PREFS, Context.MODE_PRIVATE)
        loadConfig()
        cloud = CloudApi(serverUrl)

        bindViews()
        setupListeners()
        buildFanAnimation()
        showLogin()                       // 启动即显示登录遮罩（图1）
    }

    private fun bindViews() {
        tvMethane = findViewById(R.id.tv_methane)
        tvThreshold = findViewById(R.id.tv_threshold)
        tvMode = findViewById(R.id.tv_mode)
        ivFan = findViewById(R.id.iv_fan)
        btnMode = findViewById(R.id.btn_mode)
        btnFanOn = findViewById(R.id.btn_fan_on)
        btnFanOff = findViewById(R.id.btn_fan_off)
        btnLogout = findViewById(R.id.btn_logout)

        loginMask = findViewById(R.id.login_mask)
        etUser = findViewById(R.id.et_user)
        etPass = findViewById(R.id.et_pass)
        btnLogin = findViewById(R.id.btn_login)
        btnOpenSettings = findViewById(R.id.btn_open_settings)
    }

    private fun setupListeners() {
        btnLogin.setOnClickListener { doLogin() }
        btnOpenSettings.setOnClickListener { showSettingsDialog() }
        btnLogout.setOnClickListener { doLogout() }
        btnMode.setOnClickListener { toggleMode() }
        btnFanOn.setOnClickListener { manualFan(true) }
        btnFanOff.setOnClickListener { manualFan(false) }
    }

    // ---------------- 配置读写 ---------------- //

    private fun loadConfig() {
        serverUrl = prefs.getString("server_url", serverUrl) ?: serverUrl
        threshold = prefs.getString("threshold", threshold.toString())?.toDoubleOrNull() ?: 25.0
        sensorTag = prefs.getString("sensor_tag", sensorTag) ?: sensorTag
        fanTag = prefs.getString("fan_tag", fanTag) ?: fanTag
        etUser?.setText(prefs.getString("username", "") ?: "")
    }

    private fun saveConfig() {
        prefs.edit()
            .putString("server_url", serverUrl)
            .putString("threshold", threshold.toString())
            .putString("sensor_tag", sensorTag)
            .putString("fan_tag", fanTag)
            .apply()
        tvThreshold.text = "甲烷报警阈值: $threshold %"
    }

    // ---------------- 登录 / 注销 ---------------- //

    private fun showLogin() {
        logged = false
        stopPoll()
        loginMask.visibility = View.VISIBLE
        loginMask.alpha = 0.96f            // 背景遮罩
    }

    private fun doLogin() {
        val user = etUser.text.toString().trim()
        val pass = etPass.text.toString().trim()
        if (user.isEmpty() || pass.isEmpty()) {
            Toast.makeText(this, "请输入用户名和密码", Toast.LENGTH_SHORT).show()
            return
        }
        btnLogin.isEnabled = false
        Toast.makeText(this, "正在登录云服务系统...", Toast.LENGTH_SHORT).show()
        thread {
            val ok = cloud.login(user, pass)
            handler.post {
                btnLogin.isEnabled = true
                if (ok) {
                    prefs.edit().putString("username", user).apply()
                    logged = true
                    loginMask.visibility = View.GONE
                    Toast.makeText(this, "登录成功", Toast.LENGTH_SHORT).show()
                    startPoll()
                } else {
                    Toast.makeText(this, "登录失败，请检查账号密码", Toast.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun doLogout() {
        stopPoll()
        setFan(false)
        logged = false
        cloud = CloudApi(serverUrl)
        showLogin()
        Toast.makeText(this, "已注销，请重新登录", Toast.LENGTH_SHORT).show()
    }

    // ---------------- 设置弹窗（图3） ---------------- //

    private fun showSettingsDialog() {
        val v = LayoutInflater.from(this).inflate(R.layout.dialog_settings, null)
        val etServer = v.findViewById<EditText>(R.id.et_server)
        val etThreshold = v.findViewById<EditText>(R.id.et_threshold)
        val etSensor = v.findViewById<EditText>(R.id.et_sensor_tag)
        val etFan = v.findViewById<EditText>(R.id.et_fan_tag)

        etServer.setText(serverUrl)
        etThreshold.setText(threshold.toString())
        etSensor.setText(sensorTag)
        etFan.setText(fanTag)

        AlertDialog.Builder(this)
            .setTitle("设置")
            .setView(v)
            .setPositiveButton("保存") { _, _ ->
                serverUrl = etServer.text.toString().trim()
                threshold = etThreshold.text.toString().trim().toDoubleOrNull() ?: threshold
                sensorTag = etSensor.text.toString().trim().ifEmpty { sensorTag }
                fanTag = etFan.text.toString().trim().ifEmpty { fanTag }
                cloud.setBase(serverUrl)
                saveConfig()
                Toast.makeText(this, "设置已保存", Toast.LENGTH_SHORT).show()
            }
            .setNegativeButton("取消", null)
            .show()
    }

    // ---------------- 风扇动画 ---------------- //

    private fun buildFanAnimation() {
        fanRotAnim = RotateAnimation(
            0f, 360f,
            Animation.RELATIVE_TO_SELF, 0.5f,
            Animation.RELATIVE_TO_SELF, 0.5f
        ).apply {
            duration = 800
            repeatCount = Animation.INFINITE
            interpolator = LinearInterpolator()
        }
    }

    private fun setFan(on: Boolean) {
        fanOn = on
        if (on) {
            ivFan.startAnimation(fanRotAnim)
        } else {
            ivFan.clearAnimation()
        }
    }

    // ---------------- 模式切换 / 手动控制 ---------------- //

    private fun toggleMode() {
        autoMode = !autoMode
        tvMode.text = if (autoMode) "当前模式: 自动" else "当前模式: 手动"
        btnFanOn.isEnabled = !autoMode
        btnFanOff.isEnabled = !autoMode
        if (autoMode) {
            Toast.makeText(this, "已切换到自动模式", Toast.LENGTH_SHORT).show()
        } else {
            Toast.makeText(this, "已切换到手动模式", Toast.LENGTH_SHORT).show()
        }
    }

    private fun manualFan(on: Boolean) {
        if (autoMode) {
            Toast.makeText(this, "当前为自动模式，请先切换到手动", Toast.LENGTH_SHORT).show()
            return
        }
        setFan(on)
        sendFanCommand(on)
        Toast.makeText(this, if (on) "手动开启风扇" else "手动关闭风扇", Toast.LENGTH_SHORT).show()
    }

    private fun sendFanCommand(on: Boolean) {
        if (devId <= 0) return
        val value = if (on) 1 else 0
        thread { cloud.sendCommand(devId, fanTag, value) }
    }

    // ---------------- 数据轮询 ---------------- //

    private fun startPoll() {
        stopPoll()
        pollRunnable = object : Runnable {
            override fun run() {
                refreshMethane()
                handler.postDelayed(this, POLL_MS)
            }
        }
        handler.post(pollRunnable!!)
    }

    private fun stopPoll() {
        pollRunnable?.let { handler.removeCallbacks(it) }
        pollRunnable = null
    }

    private fun refreshMethane() {
        if (!logged) return
        thread {
            if (devId <= 0) devId = cloud.queryFirstDeviceId()
            val value = cloud.fetchSensorValue(devId, sensorTag)
            handler.post {
                if (value == null) {
                    tvMethane.text = "甲烷: -- %"
                    return@post
                }
                tvMethane.text = "甲烷: %.1f %".format(value)
                // 自动模式：甲烷大于阈值开风扇(动画)，小于阈值关风扇(停动画)
                if (autoMode) {
                    val shouldOn = value > threshold
                    if (shouldOn != fanOn) {
                        setFan(shouldOn)
                        sendFanCommand(shouldOn)
                    }
                }
            }
        }
    }

    override fun onDestroy() {
        super.onDestroy()
        stopPoll()
    }
}
