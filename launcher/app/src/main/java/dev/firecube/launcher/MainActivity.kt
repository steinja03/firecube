package dev.firecube.launcher

import android.app.Activity
import android.app.AlertDialog
import android.content.Intent
import android.content.ActivityNotFoundException
import android.graphics.Color
import android.graphics.Typeface
import android.graphics.Bitmap
import android.graphics.Canvas
import android.util.LruCache
import android.graphics.drawable.GradientDrawable
import android.os.Bundle
import android.provider.Settings
import android.view.Gravity
import android.view.View
import android.widget.*
import android.text.InputFilter
import android.net.Uri
import java.util.concurrent.Executors
import org.json.JSONArray
import org.json.JSONObject

/** API 22 prototype: no network, background services, or usage access. */
class MainActivity : Activity() {
    private val prefs by lazy { getSharedPreferences("home", MODE_PRIVATE) }
    private var allApps = false
    private val artwork = object : LruCache<String, Bitmap>(4 * 1024 * 1024) {
        override fun sizeOf(key: String, value: Bitmap) = value.byteCount
    }
    private val loader = Executors.newSingleThreadExecutor()
    @Volatile private var generation = 0
    private var catalog: List<App> = emptyList()
    private var loading = false
    private var showingHidden = false
    private var visibleIds: List<String> = emptyList()
    private var focusedPackage: String? = null
    private var focusCaption: TextView? = null
    private data class Palette(val top: String, val bottom: String, val card: String,
        val focused: String, val accent: String)
    private val palettes = listOf(
        Palette("#111D35", "#070B15", "#19263D", "#263F61", "#A7D6FF"),
        Palette("#20362F", "#09140F", "#1D332B", "#2D5243", "#ADE8CD"),
        Palette("#35263A", "#110C19", "#302039", "#51375A", "#E6B8E8")
    )
    private fun palette() = palettes[prefs.getInt("theme", 0).coerceIn(0, palettes.lastIndex)]
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

    override fun onResume() {
        super.onResume()
        loading = true
        render()
        loader.execute {
            val result = try { discover() } catch (_: RuntimeException) { null }
            runOnUiThread {
                if (!isDestroyed) {
                    loading = false
                    if (result != null) catalog = result
                    else Toast.makeText(this, "Could not refresh apps", Toast.LENGTH_LONG).show()
                    render()
                }
            }
        }
    }

    override fun onDestroy() {
        generation++
        loader.shutdownNow()
        artwork.evictAll()
        super.onDestroy()
    }

    override fun onSaveInstanceState(state: Bundle) {
        state.putBoolean("allApps", allApps)
        state.putString("focused", focusedPackage)
        super.onSaveInstanceState(state)
    }

    private fun favorites(): Set<String> = prefs.getStringSet("favorites", initialFavorites)!!.toSet()
    private fun hidden(): Set<String> = prefs.getStringSet("hidden", emptySet())!!.toSet()
    private fun order(): List<String> = try {
        val array = JSONArray(prefs.getString("order", "[]"))
        (0 until array.length()).map { array.getString(it) }
    } catch (_: Exception) { emptyList() }

    private fun appMenu(app: App, favorite: Boolean) {
        val options = arrayOf(
            if (favorite) "Remove from favorites" else "Add to favorites",
            "Move earlier", "Move later",
            if (app.id in hidden()) "Show in Firecube" else "Hide in Firecube (does not disable app)",
            "App information"
        )
        AlertDialog.Builder(this).setTitle(app.label).setItems(options) { _, choice ->
            when (choice) {
                0 -> {
                    val selected = favorites().toMutableSet()
                    if (favorite) selected.remove(app.id) else selected.add(app.id)
                    prefs.edit().putStringSet("favorites", selected).apply()
                }
                1, 2 -> {
                    val ids = (order() + initialFavorites + catalog.map { it.id }).distinct().toMutableList()
                    val visibleIndex = visibleIds.indexOf(app.id)
                    val neighbor = if (choice == 1) visibleIndex - 1 else visibleIndex + 1
                    if (visibleIndex >= 0 && neighbor in visibleIds.indices) {
                        java.util.Collections.swap(ids, ids.indexOf(app.id), ids.indexOf(visibleIds[neighbor]))
                        prefs.edit().putString("order", JSONArray(ids).toString()).apply()
                    }
                }
                3 -> {
                    val selected = hidden().toMutableSet()
                    if (!selected.remove(app.id)) selected.add(app.id)
                    prefs.edit().putStringSet("hidden", selected).apply()
                }
                4 -> {
                    launch(Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS, Uri.parse("package:" + app.id)))
                    return@setItems
                }
            }
            focusedPackage = app.id; render()
        }.setNegativeButton("Cancel", null).show()
    }

    private fun settingsMenu() {
        val choices = arrayOf("Grid columns", "Toggle clock", "Toggle app labels", "Toggle focus animation",
            "Manage hidden apps", "Export settings", "Import settings", "Android home settings", "Device settings",
            "Color theme", "Home heading")
        AlertDialog.Builder(this).setTitle("Your home").setItems(choices) { _, choice ->
            when (choice) {
                0 -> AlertDialog.Builder(this).setTitle("Columns")
                    .setSingleChoiceItems(arrayOf("3", "4", "5"), prefs.getInt("columns", 4) - 3) { dialog, index ->
                        prefs.edit().putInt("columns", index + 3).apply(); dialog.dismiss(); render()
                    }.show()
                1, 2, 3 -> {
                    val key = arrayOf("clock", "labels", "animation")[choice - 1]
                    prefs.edit().putBoolean(key, !prefs.getBoolean(key, true)).apply(); render()
                }
                4 -> { showingHidden = !showingHidden; allApps = true; render() }
                5 -> launchDocument(Intent(Intent.ACTION_CREATE_DOCUMENT).setType("application/json")
                    .addCategory(Intent.CATEGORY_OPENABLE).putExtra(Intent.EXTRA_TITLE, "firecube-settings.json"), 50)
                6 -> launchDocument(Intent(Intent.ACTION_OPEN_DOCUMENT).setType("application/json")
                    .addCategory(Intent.CATEGORY_OPENABLE), 51)
                7 -> AlertDialog.Builder(this).setTitle("Home settings")
                    .setMessage("Fire OS may block default-home selection. Amazon home stays installed. Open Android's home settings?")
                    .setPositiveButton("Open") { _, _ -> launch(Intent(Settings.ACTION_HOME_SETTINGS)) }
                    .setNegativeButton("Cancel", null).show()
                8 -> launch(Intent(Settings.ACTION_SETTINGS))
                9 -> AlertDialog.Builder(this).setTitle("Color theme")
                    .setSingleChoiceItems(arrayOf("Midnight", "Forest", "Plum"), prefs.getInt("theme", 0)) { dialog, index ->
                        prefs.edit().putInt("theme", index).apply(); dialog.dismiss(); render()
                    }.setNegativeButton("Cancel", null).show()
                10 -> {
                    val input = EditText(this).apply {
                        setSingleLine(true); filters = arrayOf(InputFilter.LengthFilter(48))
                        setText(prefs.getString("heading", "Your home. Your way."))
                        setSelectAllOnFocus(true)
                    }
                    AlertDialog.Builder(this).setTitle("Home heading").setView(input)
                        .setPositiveButton("Save") { _, _ ->
                            val heading = input.text.toString().trim().take(48)
                            prefs.edit().putString("heading", heading.ifBlank { "Your home. Your way." }).apply(); render()
                        }.setNegativeButton("Cancel", null).show()
                }
            }
        }.setNegativeButton("Close", null).show()
    }

    private fun launchDocument(intent: Intent, request: Int) {
        try { startActivityForResult(intent, request) }
        catch (_: ActivityNotFoundException) { Toast.makeText(this, "File picker unavailable on this firmware", Toast.LENGTH_LONG).show() }
        catch (_: SecurityException) { Toast.makeText(this, "File access blocked", Toast.LENGTH_LONG).show() }
    }

    @Deprecated("API 22 document picker")
    override fun onActivityResult(request: Int, result: Int, data: Intent?) {
        super.onActivityResult(request, result, data)
        if (result != RESULT_OK || data?.data == null) return
        val uri = data.data!!
        try {
            if (request == 50) {
                val json = JSONObject().put("version", 1)
                    .put("favorites", JSONArray(favorites().toList())).put("hidden", JSONArray(hidden().toList()))
                    .put("order", JSONArray(order())).put("columns", prefs.getInt("columns", 4))
                    .put("theme", prefs.getInt("theme", 0)).put("heading", prefs.getString("heading", "Your home. Your way."))
                for (key in listOf("clock", "labels", "animation")) json.put(key, prefs.getBoolean(key, true))
                val output = contentResolver.openOutputStream(uri, "wt") ?: error("No output stream")
                output.bufferedWriter().use { it.write(json.toString(2)) }
                Toast.makeText(this, "Settings exported", Toast.LENGTH_SHORT).show()
            } else if (request == 51) {
                val input = contentResolver.openInputStream(uri) ?: error("No input stream")
                val text = input.bufferedReader().use { reader ->
                    val buffer = CharArray(65537)
                    var count = 0
                    while (count < buffer.size) {
                        val n = reader.read(buffer, count, buffer.size - count)
                        if (n < 0) break
                        count += n
                    }
                    require(count <= 65536) { "File too large" }; String(buffer, 0, count)
                }
                val json = JSONObject(text)
                require(json.get("version") == 1)
                fun ids(key: String): List<String> {
                    val values = json.getJSONArray(key); require(values.length() <= 500)
                    return (0 until values.length()).map {
                        val value = values.get(it); require(value is String && value.matches(Regex("[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)*")))
                        value
                    }.distinct()
                }
                val favorites = ids("favorites"); val hidden = ids("hidden"); val order = ids("order")
                val columns = json.get("columns"); require(columns is Int && columns in 3..5)
                val theme = if (json.has("theme")) json.get("theme") else 0
                require(theme is Int && theme in palettes.indices)
                val heading = if (json.has("heading")) json.get("heading") else "Your home. Your way."
                require(heading is String && heading.length <= 48 && heading.none { it.isISOControl() })
                val flags = listOf("clock", "labels", "animation").associateWith {
                    val value = json.get(it); require(value is Boolean); value
                }
                AlertDialog.Builder(this).setTitle("Import launcher settings?")
                    .setMessage("Replace local favorites, hidden apps, order and display options? Installed apps are unaffected.")
                    .setPositiveButton("Import") { _, _ ->
                        val edit = prefs.edit().putStringSet("favorites", favorites.toSet())
                            .putStringSet("hidden", hidden.toSet()).putString("order", JSONArray(order).toString())
                            .putInt("columns", columns)
                            .putInt("theme", theme).putString("heading", heading)
                        for ((key, value) in flags) edit.putBoolean(key, value)
                        edit.apply(); render()
                    }.setNegativeButton("Cancel", null).show()
            }
        } catch (_: Exception) { Toast.makeText(this, "Settings operation failed; existing settings retained", Toast.LENGTH_LONG).show() }
    }

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
        cornerRadius = dp(12).toFloat()
        val theme = palette()
        setColor(Color.parseColor(if (focus) theme.focused else theme.card))
        setStroke(dp(if (focus) 2 else 1), if (focus) Color.parseColor(theme.accent) else Color.argb(45, 200, 215, 240))
    }

    private fun label(value: String, size: Float, color: String = "#EFF4F8") = TextView(this).apply {
        text = value; textSize = size; setTextColor(Color.parseColor(color))
    }

    private fun button(text: String, selected: Boolean = false, action: () -> Unit): TextView = label(text, 14f).apply {
        gravity = Gravity.CENTER
        isFocusable = true; isClickable = true
        setPadding(dp(20), 0, dp(20), 0)
        background = surface(selected)
        setTextColor(Color.parseColor(if (selected) palette().accent else "#B7C2D6"))
        typeface = Typeface.create("sans-serif-medium", Typeface.NORMAL)
        setOnFocusChangeListener { _, focus -> background = surface(focus || selected) }
        setOnClickListener { action() }
    }

    private fun appTile(app: App, favorite: Boolean): View {
        val tile = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            isFocusable = true; isClickable = true; isLongClickable = true
            contentDescription = app.label; background = surface()
            setPadding(dp(5), dp(5), dp(5), dp(5)); clipToOutline = true
            elevation = dp(2).toFloat()
        }
        val image = ImageView(this).apply {
            scaleType = ImageView.ScaleType.FIT_CENTER
            importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
        }
        val revision = generation
        val cached = artwork.get(app.id)
        if (cached != null) image.setImageBitmap(cached)
        else loader.execute {
            if (revision == generation && !Thread.currentThread().isInterrupted) {
                val drawable = try { packageManager.getApplicationBanner(app.id)
                    ?: packageManager.getApplicationIcon(app.id) } catch (_: RuntimeException) { null }
                    catch (_: android.content.pm.PackageManager.NameNotFoundException) { null }
                val bitmap = drawable?.let { art ->
                    val width = art.intrinsicWidth.coerceAtLeast(1)
                    val height = art.intrinsicHeight.coerceAtLeast(1)
                    val scale = minOf(288f / width, 162f / height)
                    Bitmap.createBitmap((width * scale).toInt().coerceAtLeast(1),
                        (height * scale).toInt().coerceAtLeast(1), Bitmap.Config.ARGB_8888).also {
                        art.setBounds(0, 0, it.width, it.height)
                        art.draw(Canvas(it))
                    }
                }
                if (bitmap != null) runOnUiThread {
                    if (!isDestroyed && revision == generation) {
                        artwork.put(app.id, bitmap)
                        image.setImageBitmap(bitmap)
                    }
                }
            }
        }
        val labels = prefs.getBoolean("labels", true)
        tile.addView(image, LinearLayout.LayoutParams(-1, dp(if (labels) 82 else 110)))
        if (labels) tile.addView(label(app.label, 15f).apply {
            gravity = Gravity.CENTER; maxLines = 1
            ellipsize = android.text.TextUtils.TruncateAt.END
            setPadding(dp(4), dp(6), dp(4), 0)
        }, LinearLayout.LayoutParams(-1, dp(32)))
        tile.setOnFocusChangeListener { _, focus ->
            tile.background = surface(focus)
            val scale = if (focus && prefs.getBoolean("animation", true)) 1.035f else 1f
            tile.animate().scaleX(scale).scaleY(scale).setDuration(100).start()
            tile.translationZ = dp(if (focus) 6 else 0).toFloat()
            if (focus) {
                focusedPackage = app.id
                focusCaption?.text = app.label
            }
        }
        tile.setOnClickListener { focusedPackage = app.id; launch(app.intent) }
        tile.setOnLongClickListener {
            appMenu(app, favorite)
            true
        }
        return tile
    }

    private fun render() {
        generation++
        focusCaption = null
        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(dp(40), dp(28), dp(40), dp(18))
            background = GradientDrawable(GradientDrawable.Orientation.TL_BR,
                intArrayOf(Color.parseColor(palette().top), Color.parseColor(palette().bottom)))
        }
        val header = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL }
        val branding = LinearLayout(this).apply { orientation = LinearLayout.VERTICAL }
        branding.addView(label("F I R E C U B E", 10f, palette().accent))
        branding.addView(label(prefs.getString("heading", "Your home. Your way.")!!, 30f).apply {
            typeface = Typeface.create("sans-serif-light", Typeface.NORMAL)
            maxLines = 1; ellipsize = android.text.TextUtils.TruncateAt.END
            setPadding(0, dp(8), 0, dp(6))
        })
        header.addView(branding, LinearLayout.LayoutParams(0, -2, 1f))
        val time = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; gravity = Gravity.END
        }
        time.addView(TextClock(this).apply {
            format12Hour = "h:mm a"; format24Hour = "HH:mm"
            textSize = 30f; setTextColor(Color.WHITE)
            typeface = Typeface.create("sans-serif-light", Typeface.NORMAL)
        })
        time.addView(TextClock(this).apply {
            format12Hour = "EEEE, MMM d"; format24Hour = "EEEE, MMM d"
            textSize = 12f; setTextColor(Color.parseColor("#94A7B9"))
        })
        if (prefs.getBoolean("clock", true)) header.addView(time)
        root.addView(header)
        val actions = LinearLayout(this).apply { setPadding(0, dp(18), 0, dp(16)) }
        fun tab(text: String, selected: Boolean = false, action: () -> Unit) {
            actions.addView(button(text, selected, action), LinearLayout.LayoutParams(-2, dp(38)).apply {
                rightMargin = dp(10)
            })
        }
        tab("Favorites", !allApps) { allApps = false; showingHidden = false; focusedPackage = null; render() }
        tab("All apps", allApps && !showingHidden) { allApps = true; showingHidden = false; focusedPackage = null; render() }
        actions.addView(Space(this), LinearLayout.LayoutParams(0, 1, 1f))
        tab("Settings") { settingsMenu() }
        root.addView(actions)
        val favoriteIds = favorites()
        val hiddenIds = hidden()
        val order = (order() + initialFavorites).distinct()
        val apps = catalog.filter { (if (showingHidden) it.id in hiddenIds else it.id !in hiddenIds) && (allApps || it.id in favoriteIds) }.let { list ->
            list.sortedWith(compareBy<App> {
                val index = order.indexOf(it.id)
                if (index < 0) Int.MAX_VALUE else index
            }.thenBy { it.label.lowercase() })
        }
        visibleIds = apps.map { it.id }
        root.addView(label(if (loading) "REFRESHING APPS" else if (showingHidden) "HIDDEN APPS" else if (allApps) "ALL APPS  ·  "+apps.size else "YOUR FAVORITES  ·  "+apps.size, 10f, "#94A7B9").apply {
            setPadding(dp(6), 0, 0, dp(10))
        })
        val scroll = ScrollView(this).apply { clipChildren = false }
        val rows = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL; clipChildren = false
            setPadding(dp(6), dp(6), dp(6), dp(8))
        }
        var remembered: View? = null
        var first: View? = null
        val columns = prefs.getInt("columns", 4).coerceIn(3, 5)
        val restoreId = focusedPackage
        for (chunk in apps.chunked(columns)) {
            val row = LinearLayout(this).apply { clipChildren = false }
            for (app in chunk) {
                val tile = appTile(app, app.id in favoriteIds)
                row.addView(tile, LinearLayout.LayoutParams(0, dp(132), 1f).apply {
                    setMargins(dp(6), dp(6), dp(6), dp(6))
                })
                if (first == null) first = tile
                if (app.id == restoreId) remembered = tile
            }
            repeat(columns - chunk.size) {
                row.addView(Space(this), LinearLayout.LayoutParams(0, dp(132), 1f).apply {
                    setMargins(dp(6), dp(6), dp(6), dp(6))
                })
            }
            rows.addView(row)
        }
        if (apps.isEmpty()) rows.addView(label(if (loading) "Loading your apps…" else if (showingHidden) "No hidden apps." else "Choose favorites from All apps. Hold Select on any app.", 18f))
        scroll.addView(rows)
        root.addView(scroll, LinearLayout.LayoutParams(-1, 0, 1f))
        val footer = LinearLayout(this).apply { gravity = Gravity.CENTER_VERTICAL; setPadding(dp(6), dp(8), dp(6), 0) }
        focusCaption = label("Choose an app", 13f, palette().accent)
        footer.addView(focusCaption, LinearLayout.LayoutParams(0, -2, 1f))
        footer.addView(label("SELECT  Open    ·    HOLD SELECT  Organize", 10f, "#94A7B9"))
        root.addView(footer)
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
        if (allApps) { allApps = false; showingHidden = false; render() } else super.onBackPressed()
    }
}
