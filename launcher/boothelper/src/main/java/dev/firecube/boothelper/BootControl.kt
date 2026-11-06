package dev.firecube.boothelper

import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.os.IBinder
import org.json.JSONObject

object BootControl {
    @Synchronized fun execute(context: Context, action: String, pairing: Boolean = false): String {
        val prefs = context.getSharedPreferences("controller", Context.MODE_PRIVATE)
        if (action == "stop") prefs.edit().putBoolean("enabled", false).apply()
        require(Build.DEVICE == "tank" && Build.VERSION.SDK_INT == 22 &&
            Build.FINGERPRINT == "Amazon/full_tank/tank:5.1.1/LVY48F/288.6.8.8_user_688806320:user/release-keys") {
            "Controller is scoped to the inspected tank/build 688806320"
        }
        val adb = LocalAdb(context)
        fun status(): JSONObject {
            val lines = adb.shell("status", pairing).lines().filter { it.trimStart().startsWith("{") }
            require(lines.size == 1) { "Observer response missing. Run PC setup first." }
            val result = JSONObject(lines.single())
            require(result.optBoolean("ok") && result.optInt("uid") == 2000 && result.optString("mode") == "status") { result.optString("error", "Observer unavailable") }
            return result.getJSONObject("status")
        }
        fun ready(value: JSONObject) = value.optBoolean("alive") && value.optJSONObject("snapshot")?.let {
            it.optBoolean("ready") && it.optString("state") == "monitoring"
        } == true
        val text = when (action) {
            "start" -> {
                val before = status()
                val oldSession = before.optJSONObject("snapshot")?.optString("session")
                if (!ready(before)) {
                    require(!before.optBoolean("alive")) { "Observer is active but not ready. Stop and review it first." }
                    adb.shell("start")
                    var seen: JSONObject? = null
                    for (attempt in 0 until 30) {
                        val current = status()
                        if (ControllerPolicy.newSessionReady(ready(current), current.optJSONObject("snapshot")?.optString("session"), oldSession)) { seen = current; break }
                        Thread.sleep(500)
                    }
                    require(seen != null) { "Observer readiness not verified. Check PC status." }
                }
                prefs.edit().putBoolean("paired", true).apply()
                "Observer is ready. Test remote Home from a streaming app."
            }
            "stop" -> {
                // Disable future boot starts even if ADB is currently unavailable.
                prefs.edit().putBoolean("enabled", false).apply()
                adb.shell("stop")
                var stopped = false
                for (attempt in 0 until 30) {
                    if (!status().optBoolean("alive")) { stopped = true; break }
                    Thread.sleep(500)
                }
                require(stopped) { "Stop not verified. Use PC Stop or reboot." }
                "Observer stopped; boot start is off."
            }
            "status" -> status().toString(2)
            else -> error("Unknown controller action")
        }
        prefs.edit().putString("last", text).apply()
        return text
    }
}

class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action == Intent.ACTION_BOOT_COMPLETED && context.getSharedPreferences("controller", 0).getBoolean("enabled", false)) {
            context.startService(Intent(context, BootService::class.java))
        }
    }
}

class BootService : Service() {
    private var worker: Thread? = null
    override fun onBind(intent: Intent?): IBinder? = null
    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (worker?.isAlive == true) return START_NOT_STICKY
        worker = Thread {
            val prefs = getSharedPreferences("controller", MODE_PRIVATE)
            try {
                for (attempt in 0 until 6) {
                    if (!prefs.getBoolean("enabled", false)) break
                    try { BootControl.execute(this, "start"); break }
                    catch (error: Exception) {
                        prefs.edit().putString("last", "Boot attempt ${attempt + 1}: ${error.message}").apply()
                        if (attempt < 5) Thread.sleep(5000)
                    }
                }
            } finally { stopSelf() }
        }.apply { start() }
        return START_NOT_STICKY
    }
}
