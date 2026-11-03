package dev.firecube.homebridge

import android.app.Activity
import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.graphics.Color
import android.widget.*

class MainActivity : Activity() {
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        val prefs = getSharedPreferences("bridge", MODE_PRIVATE)
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(64, 48, 64, 32)
            setBackgroundColor(Color.rgb(12, 20, 34))
        }
        root.addView(TextView(this).apply {
            text = "Firecube Home Bridge — experimental"
            textSize = 26f; setTextColor(Color.WHITE)
        })
        val status = TextView(this).apply { textSize = 18f; setTextColor(Color.LTGRAY) }
        fun refresh() {
            status.text = "Redirect: " + (if (prefs.getBoolean("paused", true)) "paused" else "enabled in app") +
                "\nAndroid accessibility activation is also required.\n" +
                "Amazon home stays installed and may appear briefly. Alexa is unchanged.\n" +
                "No screen content, microphone, network or key filtering is requested."
        }
        refresh(); root.addView(status)
        root.addView(Button(this).apply {
            text = "Pause / resume redirect"
            setOnClickListener { prefs.edit().putBoolean("paused", !prefs.getBoolean("paused", true)).apply(); refresh() }
        })
        root.addView(Button(this).apply {
            text = "Android accessibility settings"
            setOnClickListener {
                try { startActivity(Intent(Settings.ACTION_ACCESSIBILITY_SETTINGS)) }
                catch (_: Exception) { Toast.makeText(this@MainActivity, "Accessibility settings unavailable", Toast.LENGTH_LONG).show() }
            }
        })
        setContentView(root)
    }
}
