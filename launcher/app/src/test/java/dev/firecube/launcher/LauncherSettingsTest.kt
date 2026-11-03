package dev.firecube.launcher

import org.junit.Assert.*
import org.junit.Test
import org.json.JSONObject

class LauncherSettingsTest {
    private fun sample() = LauncherSettings(setOf("com.netflix.ninja", "com.plexapp.android"),
        setOf("com.example.hidden"), listOf("com.plexapp.android", "com.netflix.ninja"),
        columns = 5, theme = 2, heading = "My home", clock = false, labels = true, animation = false)

    @Test fun roundTripPreservesPreferencesAndAppOrder() {
        val settings = sample()
        assertEquals(settings, LauncherSettings.decode(settings.encode()))
    }

    @Test fun olderExportsKeepSafeDefaultsForNewFields() {
        val old = JSONObject(sample().encode())
        old.remove("theme"); old.remove("heading")
        val restored = LauncherSettings.decode(old.toString())
        assertEquals(0, restored.theme)
        assertEquals("Your home. Your way.", restored.heading)
        assertEquals(sample().favorites, restored.favorites)
    }

    @Test fun rejectsInvalidTypesAndRanges() {
        for ((key, value) in listOf("columns" to 99, "columns" to "4", "clock" to "true",
                "theme" to -1, "heading" to "Line\nbreak", "version" to 2)) {
            val text = JSONObject(sample().encode()).put(key, value).toString()
            assertThrows(Exception::class.java) { LauncherSettings.decode(text) }
        }
    }

    @Test fun rejectsOversizedInputAndCommandLikeIdentifiers() {
        assertThrows(Exception::class.java) { LauncherSettings.decode(" ".repeat(65537)) }
        val text = JSONObject(sample().encode()).put("favorites", org.json.JSONArray(listOf("com.app; reboot"))).toString()
        assertThrows(Exception::class.java) { LauncherSettings.decode(text) }
    }

    @Test fun duplicateEntriesAreDeduplicatedWithoutReordering() {
        val text = JSONObject(sample().encode()).put("order",
            org.json.JSONArray(listOf("com.plexapp.android", "com.netflix.ninja", "com.plexapp.android"))).toString()
        assertEquals(sample().order, LauncherSettings.decode(text).order)
    }
}
