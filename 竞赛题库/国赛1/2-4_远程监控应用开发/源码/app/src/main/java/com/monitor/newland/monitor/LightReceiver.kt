package com.monitor.newland.monitor

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

class LightReceiver : BroadcastReceiver() {

    companion object {
        const val ACTION_LIGHT_ON = "com.monitor.newland.monitor.LIGHT_ON"
        const val ACTION_LIGHT_OFF = "com.monitor.newland.monitor.LIGHT_OFF"
    }

    override fun onReceive(context: Context, intent: Intent) {
        when (intent.action) {
            ACTION_LIGHT_ON -> {
                LightStateManager.setLightOn(context, true)
            }
            ACTION_LIGHT_OFF -> {
                LightStateManager.setLightOn(context, false)
            }
        }
    }
}
