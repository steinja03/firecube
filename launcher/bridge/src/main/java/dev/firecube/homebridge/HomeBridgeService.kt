package dev.firecube.homebridge

import android.accessibilityservice.AccessibilityService
import android.content.Intent
import android.content.ActivityNotFoundException
import android.os.SystemClock
import android.view.accessibility.AccessibilityEvent

/** Optional window-only redirect; never reads content, filters keys or disables packages. */
class HomeBridgeService : AccessibilityService() {
    private var lastRedirect = -2000L

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        if (event?.eventType != AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED ||
            event.packageName?.toString() != "com.amazon.tv.launcher") return
        val name = event.className?.toString() ?: return
        if (name != "com.amazon.tv.launcher.ui.HomeActivity_vNext" &&
            name != "com.amazon.tv.launcher.ui.HomeActivity") return
        val prefs = getSharedPreferences("bridge", MODE_PRIVATE)
        if (prefs.getBoolean("paused", true)) return
        val now = SystemClock.elapsedRealtime()
        if (now - lastRedirect < 1500) return
        lastRedirect = now
        try {
            startActivity(Intent().setClassName("dev.firecube.launcher", "dev.firecube.launcher.MainActivity")
                .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED))
            prefs.edit().putString("last_result", "Redirect requested; verify on TV").apply()
        } catch (_: ActivityNotFoundException) {
            prefs.edit().putBoolean("paused", true).putString("last_result", "Firecube unavailable; bridge paused").apply()
        } catch (_: SecurityException) {
            prefs.edit().putBoolean("paused", true).putString("last_result", "Launch blocked; bridge paused").apply()
        }
    }

    override fun onInterrupt() { }
}
