package com.greenhouse.methane

import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStream
import java.io.InputStreamReader
import java.io.OutputStream
import java.net.HttpURLConnection
import java.net.URL

/**
 * 物联网云服务系统（NLECloud / 新大陆云平台）RESTful 简易客户端。
 *
 * 接口：
 *   1. POST {base}/users/login            登录，返回 AccessToken
 *   2. GET  {base}/Devices                模糊查询设备
 *   3. GET  {base}/Devices/Datas?devIds=.. 批量查询设备传感器最新数据
 *   4. POST {base}/Devices/{id}/Cmds       向执行器(风扇)下发开关指令
 *
 * 除登录外，请求头需携带 AccessToken。
 * 本类全部为同步阻塞方法，务必在子线程调用。
 */
class CloudApi(private var baseUrl: String) {

    var token: String? = null
        private set

    fun setBase(url: String) {
        baseUrl = url.trim().trimEnd('/')
        token = null
    }

    /** 登录。成功返回 true，并保存 token。 */
    fun login(account: String, password: String): Boolean {
        val payload = JSONObject().apply {
            put("Account", account)
            put("Password", password)
            put("IsRememberMe", true)
        }
        val conn = openPost("$baseUrl/users/login", null, payload.toString())
        return try {
            val body = readStream(conn.inputStream)
            val json = JSONObject(body)
            val obj = json.optJSONObject("ResultObj") ?: return false
            val t = obj.optString("AccessToken")
            if (t.isNotEmpty()) {
                token = t
                true
            } else {
                false
            }
        } catch (e: Exception) {
            e.printStackTrace()
            false
        } finally {
            conn.disconnect()
        }
    }

    /** 查询账号下所有设备，取第一个网关设备的 DeviceID。 */
    fun queryFirstDeviceId(): Int {
        val conn = openGet("$baseUrl/Devices?PageSize=100&PageIndex=1")
        return try {
            val body = readStream(conn.inputStream)
            val json = JSONObject(body)
            val obj = json.optJSONObject("ResultObj")
            val set = obj?.optJSONArray("PageSet")
            if (set != null && set.length() > 0) {
                set.getJSONObject(0).optInt("DeviceID")
            } else {
                0
            }
        } catch (e: Exception) {
            -1
        } finally {
            conn.disconnect()
        }
    }

    /**
     * 读取指定传感器标识(ApiTag)的最新值。
     * 找到返回数值，找不到或失败返回 null。
     */
    fun fetchSensorValue(devId: Int, apiTag: String): Double? {
        if (devId <= 0) return null
        val conn = openGet("$baseUrl/Devices/Datas?devIds=$devId")
        return try {
            val body = readStream(conn.inputStream)
            val json = JSONObject(body)
            val arr = json.optJSONArray("ResultObj") ?: return null
            var value: Double? = null
            for (i in 0 until arr.length()) {
                val dev = arr.getJSONObject(i)
                val datas = dev.optJSONArray("Datas") ?: continue
                for (j in 0 until datas.length()) {
                    val s = datas.getJSONObject(j)
                    if (s.optString("ApiTag").equals(apiTag, ignoreCase = true)) {
                        value = s.optDouble("Value", Double.NaN)
                        if (value.isNaN()) value = null
                    }
                }
            }
            value
        } catch (e: Exception) {
            e.printStackTrace()
            null
        } finally {
            conn.disconnect()
        }
    }

    /**
     * 向执行器下发指令（开关风扇）。value: 1=开, 0=关。
     * 返回 true 表示云平台受理成功。
     */
    fun sendCommand(devId: Int, apiTag: String, value: Int): Boolean {
        if (devId <= 0) return false
        val payload = JSONObject().apply {
            put("apikey", token ?: "")
            put("apitag", apiTag)
            put("value", value)
        }
        val conn = openPost("$baseUrl/Devices/$devId/Cmds", token, payload.toString())
        return try {
            val body = readStream(conn.inputStream)
            val json = JSONObject(body)
            val sc = json.optInt("StatusCode", -1)
            sc == 1 || sc == 2
        } catch (e: Exception) {
            e.printStackTrace()
            false
        } finally {
            conn.disconnect()
        }
    }

    // ---------------- 底层 HTTP 工具 ---------------- //

    private fun openGet(urlStr: String): HttpURLConnection {
        val conn = URL(urlStr).openConnection() as HttpURLConnection
        conn.requestMethod = "GET"
        conn.connectTimeout = 8000
        conn.readTimeout = 8000
        if (!token.isNullOrEmpty()) conn.setRequestProperty("AccessToken", token)
        return conn
    }

    private fun openPost(urlStr: String, token: String?, body: String): HttpURLConnection {
        val conn = URL(urlStr).openConnection() as HttpURLConnection
        conn.requestMethod = "POST"
        conn.connectTimeout = 8000
        conn.readTimeout = 8000
        conn.doOutput = true
        conn.setRequestProperty("Content-Type", "application/json")
        if (!token.isNullOrEmpty()) conn.setRequestProperty("AccessToken", token)
        val os: OutputStream = conn.outputStream
        os.write(body.toByteArray(Charsets.UTF_8))
        os.flush()
        os.close()
        return conn
    }

    private fun readStream(stream: InputStream): String {
        val sb = StringBuilder()
        val reader = BufferedReader(InputStreamReader(stream, "UTF-8"))
        var line = reader.readLine()
        while (line != null) {
            sb.append(line)
            line = reader.readLine()
        }
        reader.close()
        return sb.toString()
    }
}
