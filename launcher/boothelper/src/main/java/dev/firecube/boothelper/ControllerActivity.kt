package dev.firecube.boothelper

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.Gravity
import android.widget.*
import java.util.concurrent.Executors

class ControllerActivity : Activity() {
    private val worker = Executors.newSingleThreadExecutor()
    private lateinit var status: TextView
    private lateinit var boot: Switch
    private val prefs by lazy { getSharedPreferences("controller", MODE_PRIVATE) }
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val layout = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL; setPadding(48,24,48,24); setBackgroundColor(Color.rgb(15,24,40)) }
        fun text(value: String, size: Float) = TextView(this).apply { text = value; textSize = size; setTextColor(Color.WHITE); setPadding(0,8,0,8) }
        layout.addView(text("Firecube Home Controller", 28f))
        layout.addView(text("Pair once with this Stick’s local ADB. Approving its key grants this helper shell access. It connects only to 127.0.0.1:5555 and keeps its key private. Boot start defaults off.", 16f))
        status = text(prefs.getString("last", "Run PC setup, then pair here. Keep the TV’s ADB authorization prompt visible and approve only this request.")!!, 16f)
        val row = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val buttons = ArrayList<Button>()
        fun action(label: String, mode: String, pairing: Boolean = false) {
            val button = Button(this).apply { text = label }
            buttons.add(button); row.addView(button, LinearLayout.LayoutParams(0, 80, 1f))
            button.setOnClickListener {
                if (mode == "stop") {
                    prefs.edit().putBoolean("enabled", false).apply()
                    boot.isChecked = false
                }
                buttons.forEach { it.isEnabled = false }
                status.text = if (pairing) "Connecting locally. Approve the Firecube ADB key on your TV if prompted; allow up to 60 seconds." else "Working…"
                worker.execute {
                    val message = try { BootControl.execute(this, mode, pairing) } catch (error: Exception) {
                        "Not verified: ${error.message}".also { prefs.edit().putString("last", it).apply() }
                    }
                    runOnUiThread { if (!isDestroyed) { status.text = message; buttons.forEach { it.isEnabled = true } } }
                }
            }
        }
        action("Pair / Start", "start", true); action("Status", "status"); action("Stop", "stop")
        layout.addView(row)
        boot = Switch(this).apply { text = "Start Home observer after reboot"; textSize = 19f; setTextColor(Color.WHITE); isChecked = prefs.getBoolean("enabled", false) }
        boot.setOnCheckedChangeListener { _, checked ->
            if (checked && !prefs.getBoolean("paired", false)) {
                boot.isChecked = false; status.text = "Pair / Start successfully before enabling boot start."
            } else {
                prefs.edit().putBoolean("enabled", checked).apply()
                status.text = if (checked) "Boot start requested. Reboot behavior still needs testing on this firmware." else "Boot start off. Use Stop to end the current observer."
            }
        }
        layout.addView(boot)
        layout.addView(status)
        layout.addView(text("No Alexa or package disabling. If Home misbehaves: turn boot start off, then Stop. PC Stop is also available. If needed, force-stop this controller in Fire OS settings before rebooting.", 15f))
        setContentView(ScrollView(this).apply { addView(layout) })
    }
    override fun onDestroy() { worker.shutdownNow(); super.onDestroy() }
}
