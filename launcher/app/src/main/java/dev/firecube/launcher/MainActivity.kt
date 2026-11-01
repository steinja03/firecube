package dev.firecube.launcher

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.ActivityNotFoundException
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.drawable.Drawable
import android.util.LruCache
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
    private val artwork = LruCache<String, Drawable>(32)
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

    private fun surface(focus: Boolean = false) = GradientDrawable().apply {
        cornerRadius = dp(10).toFloat()
        setColor(Color.parseColor(if (focus) "#254652" else "#172536"))
        setStroke(dp(if (focus) 2 else 1), Color.parseColor(if (focus) "#D0F3E8" else "#263749"))
    }

    private fun label(value: String, size: Float, color: String = "#EFF4F8") = TextView(this).apply {
        text = value; textSize = size; setTextColor(Color.parseColor(color))
    }

    private fun button(text: String, action: () -> Unit): TextView = label(text, 15f).apply {
        gravity = Gravity.CENTER
        isFocusable = true; isClickable = true
        setPadding(dp(20), 0, dp(20), 0)
        background = surface()
        setOnFocusChangeListener { _, focus -> background = surface(focus) }
        setOnClickListener { action() }
    }

    private fun appTile(app: App, favorite: Boolean): View {
        val tile = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            isFocusable = true; isClickable = true; isLongClickable = true
            contentDescription = app.label; background = surface()
            setPadding(dp(8), dp(8), dp(8), dp(8)); clipToOutline = true
        }
        val image = ImageView(this).apply {
            scaleType = ImageView.ScaleType.FIT_CENTER
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        }
        var drawable = artwork.get(app.id)
        if (drawable == null) {
            try {
                drawable = packageManager.getApplicationBanner(app.id)
                    ?: packageManager.getApplicationIcon(app.id)
                artwork.put(app.id, drawable)
            } catch (_: android.content.pm.PackageManager.NameNotFoundException) { }
        }
        image.setImageDrawable(drawable)
        tile.addView(image, LinearLayout.LayoutParams(-1, dp(82)))
        tile.addView(label(app.label, 15f).apply {
            gravity = Gravity.CENTER; maxLines = 1
            ellipsize = android.text.TextUtils.TruncateAt.END
            setPadding(dp(4), dp(6), dp(4), 0)
        }, LinearLayout.LayoutParams(-1, dp(32)))
        tile.setOnFocusChangeListener { _, focus ->
            tile.background = surface(focus)
            tile.animate().scaleX(if (focus) 1.035f else 1f)
                .scaleY(if (focus) 1.035f else 1f).setDuration(100).start()
            if (focus) focusedPackage = app.id
        }
        tile.setOnClickListener { focusedPackage = app.id; launch(app.intent) }
        tile.setOnLongClickListener {
            AlertDialog.Builder(this).setTitle(app.label)
                .setMessage(if (favorite) "Remove from favorites?" else "Add to favorites?")
                .setPositiveButton("Yes") { _, _ ->
                    val selected = favorites().toMutableSet()
                    if (favorite) selected.remove(app.id) else selected.add(app.id)
                    prefs.edit().putStringSet("favorites", selected).apply()
                    focusedPackage = app.id; render()
                }.setNegativeButton("Cancel", null).show()
            true
        }
        return tile
    }

    private fun render() {
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(40), dp(24), dp(40), dp(16))
            background = GradientDrawable(GradientDrawable.Orientation.TL_BR,
                intArrayOf(Color.parseColor("#152B38"), Color.parseColor("#0B121E")))
        }
        val header = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val branding = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        branding.addView(label("F I R E C U B E", 11f, "#94C7BD"))
        branding.addView(label("Make yourself at home.", 28f).apply {
            typeface = Typeface.create("sans-serif-light", Typeface.NORMAL)
            setPadding(0, dp(8), 0, dp(6))
        })
        header.addView(branding, LinearLayout.LayoutParams(0, -2, 1f))
        val time = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.RIGHT
        }
        time.addView(TextClock(this).apply {
            format12Hour = "h:mm a"; format24Hour = "HH:mm"
            textSize = 26f; setTextColor(Color.WHITE)
            typeface = Typeface.create("sans-serif-light", Typeface.NORMAL)
        })
        time.addView(TextClock(this).apply {
            format12Hour = "EEEE, MMM d"; format24Hour = "EEEE, MMM d"
            textSize = 12f; setTextColor(Color.parseColor("#94A7B9"))
        })
        header.addView(time); root.addView(header)
        val actions = LinearLayout(this).apply { setPadding(0, dp(18), 0, dp(16)) }
        fun tab(text: String, action: () -> Unit) {
            actions.addView(button(text, action), LinearLayout.LayoutParams(-2, dp(40)).apply {
                rightMargin = dp(10)
            })
        }
        tab("Favorites") { allApps = false; focusedPackage = null; render() }
        tab("All apps") { allApps = true; focusedPackage = null; render() }
        actions.addView(Space(this), LinearLayout.LayoutParams(0, 1, 1f))
        tab("Settings") { launch(Intent(Settings.ACTION_SETTINGS)) }
        root.addView(actions)
        val favoriteIds = favorites()
        val order = initialFavorites.toList()
        val apps = discover().filter { allApps || it.id in favoriteIds }.let { list ->
            if (allApps) list else list.sortedWith(compareBy<App> {
                val index = order.indexOf(it.id)
                if (index < 0) Int.MAX_VALUE else index
            }.thenBy { it.label.lowercase() })
        }
        root.addView(label(if (allApps) "YOUR APPS  /  "+apps.size else "READY WHEN YOU ARE", 11f, "#94A7B9").apply {
            setPadding(dp(6), 0, 0, dp(10))
        })
        val scroll = ScrollView(this).apply { clipChildren = false }
        val rows = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; clipChildren = false
            setPadding(dp(6), dp(6), dp(6), dp(8))
        }
        var remembered: View? = null
        var first: View? = null
        for (chunk in apps.chunked(4)) {
            val row = LinearLayout(this).apply { clipChildren = false }
            for (app in chunk) {
                val tile = appTile(app, app.id in favoriteIds)
                row.addView(tile, LinearLayout.LayoutParams(0, dp(132), 1f).apply {
                    setMargins(dp(6), dp(6), dp(6), dp(6))
                })
                if (first == null) first = tile
                if (app.id == focusedPackage) remembered = tile
            }
            repeat(4 - chunk.size) {
                row.addView(Space(this), LinearLayout.LayoutParams(0, dp(132), 1f).apply {
                    setMargins(dp(6), dp(6), dp(6), dp(6))
                })
            }
            rows.addView(row)
        }
        if (apps.isEmpty()) rows.addView(label("Choose favorites from All apps. Hold Select on any app.", 18f))
        scroll.addView(rows)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        root.addView(label("Hold Select to edit favorites", 11f, "#94A7B9").apply {
            setPadding(dp(6), dp(8), 0, 0)
        })
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
