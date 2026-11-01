package dev.firecube.probe

import android.app.Activity
import android.os.Bundle
import android.widget.TextView

/** Disposable app for an explicitly approved disable/enable recovery test. */
class MainActivity : Activity() {
    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        setContentView(TextView(this).apply {
            text = "Firecube recovery test app\nNo permissions or background services.\nBack exits this screen."
            textSize = 26f
            setPadding(48, 48, 48, 48)
        })
    }
}
