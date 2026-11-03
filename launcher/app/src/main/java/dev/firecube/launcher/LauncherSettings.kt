package dev.firecube.launcher

import org.json.JSONArray
import org.json.JSONObject

/** Portable, validated preference format. Never carries Android package commands. */
data class LauncherSettings(
    val favorites: Set<String>, val hidden: Set<String>, val order: List<String>,
    val columns: Int = 4, val theme: Int = 0,
    val heading: String = "Your home. Your way.",
    val clock: Boolean = true, val labels: Boolean = true, val animation: Boolean = true
) {
    fun encode(): String = JSONObject().put("version", 1)
        .put("favorites", JSONArray(favorites.toList())).put("hidden", JSONArray(hidden.toList()))
        .put("order", JSONArray(order)).put("columns", columns).put("theme", theme)
        .put("heading", heading).put("clock", clock).put("labels", labels)
        .put("animation", animation).toString(2)

    companion object {
        fun decode(text: String): LauncherSettings {
            require(text.length <= 65536) { "Settings exceed 64 KiB character limit" }
            val json = JSONObject(text)
            require(json.get("version") == 1) { "Unsupported settings version" }
            fun ids(key: String): List<String> {
                val values = json.getJSONArray(key)
                require(values.length() <= 500) { "Too many app entries" }
                return (0 until values.length()).map {
                    val value = values.get(it)
                    require(value is String && value.length <= 255 && value.matches(Regex("[A-Za-z0-9_]+(\\.[A-Za-z0-9_]+)*"))) {
                        "Invalid app identifier"
                    }
                    value
                }.distinct()
            }
            val favorites = ids("favorites"); val hidden = ids("hidden"); val order = ids("order")
            val columns = json.get("columns")
            require(columns is Int && columns in 3..5) { "Columns must be 3, 4 or 5" }
            val theme = if (json.has("theme")) json.get("theme") else 0
            require(theme is Int && theme in 0..2) { "Unknown theme" }
            val heading = if (json.has("heading")) json.get("heading") else "Your home. Your way."
            require(heading is String && heading.length <= 48 && heading.none { it.isISOControl() }) { "Invalid heading" }
            fun flag(key: String): Boolean {
                val value = json.get(key); require(value is Boolean) { "Invalid display option" }; return value
            }
            return LauncherSettings(favorites.toSet(), hidden.toSet(), order, columns, theme,
                heading, flag("clock"), flag("labels"), flag("animation"))
        }
    }
}
