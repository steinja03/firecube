package dev.firecube.launcher

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.ActivityNotFoundException
import android.graphics.Color
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.*

/** API 22 prototype: no network, background services, or usage access. */
class MainActivity : Activity() {
    private val prefs by lazy { getSharedPreferences("home", MODE_PRIVATE) }
    private var allApps = false
    private var focusedPackage: String? = null
    private data class App(val id: String, val label: String, val intent: Intent)
    private val initialFavorites = setOf(
        "com.netflix.ninja", "com.amazon.firetv.youtube", "org.chromium.youtube_apk",
        "com.cbs.ott", "com.hulu.plus", "com.hbo.hbonow", "com.wbd.stream",
        "com.disney.disneyplus", "com.plexapp.android", "com.peacocktv.peacockandroid"
    )

    override fun onCreate(state: Bundle?) {
        super.onCreate(state)
        allApps = state?.getBoolean("allApps") ?: false
        focusedPackage = state?.getString("focused")
    }

    override fun onResume() { super.onResume(); render() }

    override fun onSaveInstanceState(state: Bundle) {
        state.putBoolean("allApps", allApps)
        state.putString("focused", focusedPackage)
        super.onSaveInstanceState(state)
    }

    private fun favorites(): Set<String> = prefs.getStringSet("favorites", initialFavorites)!!.toSet()

    private fun discover(): List<App> {
        val found = linkedMapOf<String, App>()
        for (category in listOf(Intent.CATEGORY_LEANBACK_LAUNCHER, Intent.CATEGORY_LAUNCHER)) {
            val query = Intent(Intent.ACTION_MAIN).addCategory(category)
            for (info in packageManager.queryIntentActivities(query, 0)) {
                val activity = info.activityInfo ?: continue
                if (activity.packageName == packageName || !activity.exported) continue
                val intent = Intent(Intent.ACTION_MAIN).addCategory(category)
                    .setClassName(activity.packageName, activity.name)
                    .addFlags(Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_RESET_TASK_IF_NEEDED)
                if (!found.containsKey(activity.packageName)) {
                    found[activity.packageName] = App(activity.packageName,
                        info.loadLabel(packageManager).toString(), intent)
                }
            }
        }
        return found.values.sortedBy { it.label.lowercase() }
    }

    private fun dp(value: Int) = (value * resources.displayMetrics.density).toInt()

    private fun button(text: String, action: () -> Unit): Button = Button(this).apply {
        this.text = text
        textSize = 18f
        isAllCaps = false
        setTextColor(Color.WHITE)
        minHeight = dp(64)
        setPadding(dp(12), dp(8), dp(12), dp(8))
        fun background(focus: Boolean) {
            background = GradientDrawable().apply {
                cornerRadius = dp(10).toFloat()
                setColor(Color.parseColor(if (focus) "#225C82" else "#243247"))
                setStroke(dp(if (focus) 3 else 1), if (focus) Color.CYAN else Color.DKGRAY)
            }
        }
        background(false)
        setOnFocusChangeListener { _, focus -> background(focus) }
        setOnClickListener { action() }
    }

    private fun render() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(40), dp(24), dp(40), dp(24))
            setBackgroundColor(Color.parseColor("#101925"))
        }
        root.addView(TextClock(this).apply {
            format12Hour = "h:mm a"; format24Hour = "HH:mm"
            textSize = 42f; setTextColor(Color.WHITE)
        })
        root.addView(TextView(this).apply {
            text = if (allApps) "All apps" else "Your streaming apps"
            textSize = 24f; setTextColor(Color.LTGRAY)
            setPadding(0, dp(8), 0, dp(12))
        })
        val actions = LinearLayout(this)
        actions.addView(button(if (allApps) "Favorites" else "All apps") {
            allApps = !allApps; render()
        })
        actions.addView(button("Device settings") {
            launch(Intent(Settings.ACTION_SETTINGS))
        })
        root.addView(actions)
        root.addView(TextView(this).apply {
            text = "Hold Select on an app to add or remove a favorite. Home button behavior is controlled by Fire OS."
            setTextColor(Color.LTGRAY); textSize = 14f
        })
        val scroll = ScrollView(this)
        val rows = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        val favoriteIds = favorites()
        val apps = discover().filter { allApps || it.id in favoriteIds }
        var remembered: View? = null
        var first: View? = null
        for (chunk in apps.chunked(3)) {
            val row = LinearLayout(this).apply { gravity = Gravity.START }
            for (app in chunk) {
                val tile = button(app.label) {
                    focusedPackage = app.id
                    launch(app.intent)
                }
                tile.setOnLongClickListener {
                    val selected = favorites().toMutableSet()
                    val remove = app.id in selected
                    AlertDialog.Builder(this)
                        .setTitle(app.label)
                        .setMessage(if (remove) "Remove from favorites?" else "Add to favorites?")
                        .setPositiveButton("Yes") { _, _ ->
                            if (remove) selected.remove(app.id) else selected.add(app.id)
                            prefs.edit().putStringSet("favorites", selected).apply()
                            focusedPackage = app.id; render()
                        }.setNegativeButton("Cancel", null).show()
                    true
                }
                row.addView(tile, LinearLayout.LayoutParams(0, dp(88), 1f).apply {
                    setMargins(dp(6), dp(8), dp(6), dp(8))
                })
                if (first == null) first = tile
                if (app.id == focusedPackage) remembered = tile
            }
            rows.addView(row)
        }
        if (apps.isEmpty()) rows.addView(TextView(this).apply {
            text = "No favorites installed. Open All apps to choose favorites."
            setTextColor(Color.WHITE); textSize = 20f
        })
        scroll.addView(rows)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        setContentView(root)
        (remembered ?: first)?.requestFocus()
    }

    private fun launch(intent: Intent) {
        try { startActivity(intent) }
        catch (_: ActivityNotFoundException) { Toast.makeText(this, "App unavailable", Toast.LENGTH_LONG).show() }
        catch (_: SecurityException) { Toast.makeText(this, "Fire OS blocked this action", Toast.LENGTH_LONG).show() }
    }

    @Deprecated("API 22 back navigation")
    override fun onBackPressed() {
        if (allApps) { allApps = false; render() } else super.onBackPressed()
    }
}
