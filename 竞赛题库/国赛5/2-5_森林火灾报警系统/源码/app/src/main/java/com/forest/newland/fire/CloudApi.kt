package com.forest.newland.fire

import org.json.JSONArray
import org.json.JSONObject
import java.io.BufferedReader
import java.io.DataOutputStream
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder

/**
 * 物联网云服务系统 (NL-Cloud) RESTful API 客户端。
 */

data class SensorData(
    val value: Double,
    val time: String,
    val deviceId: Any? = null,
    val deviceName: String? = null
)

object JsonUtil {

    fun get(root: JSONObject, key: String): Any? {
        val keys = root.keys()
        while (keys.hasNext()) {
            val k = keys.next()
            if (k.equals(key, true)) {
                return root.opt(k)
            }
        }
        return null
    }

    fun getObj(root: JSONObject, key: String): JSONObject? = get(root, key) as? JSONObject

    fun getString(root: JSONObject, key: String): String? {
        val v = get(root, key) ?: return null
        return if (v is String) v else v.toString()
    }

    fun getDouble(root: JSONObject, key: String): Double? {
        val v = get(root, key) ?: return null
        return when (v) {
            is Number -> v.toDouble()
            is String -> v.toDoubleOrNull()
            else -> null
        }
    }

    fun getInt(root: JSONObject, key: String): Int? {
        val v = get(root, key) ?: return null
        return when (v) {
            is Number -> v.toInt()
            is String -> v.toIntOrNull()
            else -> null
        }
    }

    fun getArray(root: JSONObject, key: String): JSONArray? = get(root, key) as? JSONArray
}

object HttpUtil {

    private const val TIMEOUT_MS = 10000

    fun postJson(url: String, payload: String, headers: Map<String, String> = emptyMap()): String? {
        return request("POST", url, headers, payload)
    }

    fun get(url: String, headers: Map<String, String> = emptyMap(), params: Map<String, String> = emptyMap()): String? {
        val sb = StringBuilder(url)
        if (params.isNotEmpty()) {
            sb.append(if (url.contains("?")) "&" else "?")
            var first = true
            params.forEach { (k, v) ->
                if (!first) sb.append("&")
                first = false
                sb.append(URLEncoder.encode(k, "UTF-8"))
                    .append("=")
                    .append(URLEncoder.encode(v, "UTF-8"))
            }
        }
        return request("GET", sb.toString(), headers, null)
    }

    private fun request(method: String, url: String, headers: Map<String, String>, body: String?): String? {
        var conn: HttpURLConnection? = null
        return try {
            conn = URL(url).openConnection() as HttpURLConnection
            conn.requestMethod = method
            conn.connectTimeout = TIMEOUT_MS
            conn.readTimeout = TIMEOUT_MS
            conn.useCaches = false
            headers.forEach { (k, v) -> conn.setRequestProperty(k, v) }
            if (method == "POST") {
                conn.doOutput = true
                conn.setRequestProperty("Content-Type", "application/json; charset=UTF-8")
                if (body != null) {
                    DataOutputStream(conn.outputStream).use { it.write(body.toByteArray(Charsets.UTF_8)) }
                }
            }
            val code = conn.responseCode
            val stream = if (code in 200..299) conn.inputStream else conn.errorStream
            val text = stream?.bufferedReader(Charsets.UTF_8)?.use(BufferedReader::readText) ?: ""
            text
        } catch (e: Exception) {
            null
        } finally {
            conn?.disconnect()
        }
    }
}

interface CloudClient {
    fun login(account: String, pwd: String): Boolean
    fun fetchSensor(tag: String): SensorData?
    val lastError: String
}

class NLECloudClient(
    private val baseUrl: String = "",
    private var username: String = "",
    private var password: String = ""
) : CloudClient {
    private var token: String? = null
    override var lastError: String = ""
        private set

    private val authHeaders: Map<String, String>
        get() {
            val t = token
            return if (t != null) mapOf("AccessToken" to t) else emptyMap()
        }

    override fun login(account: String, pwd: String): Boolean {
        username = account
        password = pwd
        if (baseUrl.isBlank()) {
            lastError = "未配置云服务地址"
            return false
        }
        if (username.isBlank() || password.isBlank()) {
            lastError = "用户名或密码不能为空"
            return false
        }
        val payload = JSONObject()
            .put("Account", username)
            .put("Password", password)
            .put("IsRememberMe", true)
        val text = HttpUtil.postJson(baseUrl.trimEnd('/') + "/users/login", payload.toString())
            ?: run {
                lastError = "登录请求失败: 无法连接云服务系统"
                return false
            }
        val root = try {
            JSONObject(text)
        } catch (e: Exception) {
            lastError = "登录响应解析失败"
            return false
        }
        val result = JsonUtil.getObj(root, "ResultObj")
        val accessToken = result?.let { JsonUtil.getString(it, "AccessToken") }
        if (!accessToken.isNullOrBlank()) {
            token = accessToken
            lastError = ""
            return true
        }
        lastError = JsonUtil.getString(root, "ResultMessage")
            ?: JsonUtil.getString(root, "Msg")
            ?: "登录失败"
        return false
    }

    private fun queryDevices(): List<JSONObject> {
        val params = mutableMapOf("PageSize" to "100", "PageIndex" to "1")
        if (baseUrl.contains("nlecloud")) {
            params["StartDate"] = "2015-01-01"
        }
        val text = HttpUtil.get(
            baseUrl.trimEnd('/') + "/Devices",
            authHeaders,
            params
        ) ?: return emptyList()
        val root = try {
            JSONObject(text)
        } catch (e: Exception) {
            return emptyList()
        }
        val result = JsonUtil.getObj(root, "ResultObj")
        val pageSet = result?.let { JsonUtil.getArray(it, "PageSet") } ?: return emptyList()
        val list = mutableListOf<JSONObject>()
        for (i in 0 until pageSet.length()) {
            pageSet.optJSONObject(i)?.let { list.add(it) }
        }
        return list
    }

    private fun getDevice(deviceId: Any): JSONObject? {
        val text = HttpUtil.get(
            baseUrl.trimEnd('/') + "/Devices/" + deviceId,
            authHeaders
        ) ?: return null
        val root = try {
            JSONObject(text)
        } catch (e: Exception) {
            return null
        }
        return JsonUtil.getObj(root, "ResultObj")
    }

    private fun getLatestDatas(deviceIds: List<Any>): List<JSONObject> {
        if (deviceIds.isEmpty()) return emptyList()
        val ids = deviceIds.distinct().joinToString(",") { it.toString() }
        val text = HttpUtil.get(
            baseUrl.trimEnd('/') + "/Devices/Datas",
            authHeaders,
            mapOf("devIds" to ids)
        ) ?: return emptyList()
        val root = try {
            JSONObject(text)
        } catch (e: Exception) {
            return emptyList()
        }
        val arr = JsonUtil.getArray(root, "ResultObj") ?: return emptyList()
        val list = mutableListOf<JSONObject>()
        for (i in 0 until arr.length()) {
            arr.optJSONObject(i)?.let { list.add(it) }
        }
        return list
    }

    private fun extractDatas(devs: List<JSONObject>): List<JSONObject> {
        val out = mutableListOf<JSONObject>()
        for (dev in devs) {
            val d = JsonUtil.getArray(dev, "Datas") ?: continue
            for (i in 0 until d.length()) {
                d.optJSONObject(i)?.let { out.add(it) }
            }
        }
        return out
    }

    override fun fetchSensor(tag: String): SensorData? {
        if (token == null) {
            lastError = "尚未登录"
            return null
        }
        val devices = queryDevices()
        val devIds = devices.mapNotNull { JsonUtil.getInt(it, "DeviceID") }
        var devs = getLatestDatas(devIds)
        if (devs.isEmpty()) {
            devs = mutableListOf()
            for (id in devIds) {
                getDevice(id)?.let { devs.add(it) }
            }
        }
        for (sensor in extractDatas(devs)) {
            val apiTag = JsonUtil.getString(sensor, "ApiTag") ?: continue
            if (apiTag.equals(tag, true)) {
                val value = JsonUtil.getDouble(sensor, "Value") ?: continue
                val time = JsonUtil.getString(sensor, "RecordTime") ?: ""
                return SensorData(value, time, JsonUtil.getInt(sensor, "DeviceID"), null)
            }
        }
        lastError = "未获取到传感器($tag)数据"
        return null
    }
}

class SimulatedCloudClient(
    private val baseUrl: String = "",
    username: String = "",
    password: String = ""
) : CloudClient {
    override var lastError: String = ""
        private set

    override fun login(account: String, pwd: String): Boolean {
        lastError = ""
        return true
    }

    override fun fetchSensor(tag: String): SensorData {
        val now = System.currentTimeMillis()
        val value = Math.round((20.0 + 40.0 * Math.sin(now / 8000.0)) * 10.0) / 10.0
        val time = java.text.SimpleDateFormat("yyyy-MM-dd HH:mm:ss").format(java.util.Date(now))
        return SensorData(value, time, 1, "模拟火灾网关")
    }
}

fun createClient(mode: String, baseUrl: String, username: String, password: String): CloudClient {
    return if (mode == "demo") {
        SimulatedCloudClient(baseUrl, username, password)
    } else {
        NLECloudClient(baseUrl, username, password)
    }
}