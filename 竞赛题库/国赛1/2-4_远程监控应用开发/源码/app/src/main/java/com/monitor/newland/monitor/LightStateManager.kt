package com.monitor.newland.monitor

import android.content.Context

object LightStateManager {

    @Volatile
    var lightOn: Boolean = false
        private set

    fun setLightOn(context: Context, on: Boolean) {
        lightOn = on
        val prefs = context.getSharedPreferences("monitor_settings", Context.MODE_PRIVATE)
        prefs.edit().putBoolean("light_state", on).apply()
    }

    fun loadState(context: Context) {
        val prefs = context.getSharedPreferences("monitor_settings", Context.MODE_PRIVATE)
        lightOn = prefs.getBoolean("light_state", false)
    }
}
