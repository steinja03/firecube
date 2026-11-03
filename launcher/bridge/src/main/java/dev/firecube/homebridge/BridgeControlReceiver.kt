package dev.firecube.homebridge

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent

/** Controls only this optional app's pause preference; never writes system settings. */
class BridgeControlReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != "dev.firecube.homebridge.SET_PAUSED" || !intent.hasExtra("paused")) {
            resultCode = 0
            return
        }
        val written = context.getSharedPreferences("bridge", Context.MODE_PRIVATE).edit()
            .putBoolean("paused", intent.getBooleanExtra("paused", true)).commit()
        resultCode = if (written) 1 else 0
    }
}
