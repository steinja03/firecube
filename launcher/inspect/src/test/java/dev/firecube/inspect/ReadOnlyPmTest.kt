package dev.firecube.inspect

import org.junit.Assert.*
import org.junit.Test

class ReadOnlyPmTest {
    class Fake {
        var writes = 0
        fun checkUidPermission(permission: String, uid: Int): Int = if (permission == "test" && uid == 2000) 0 else -1
        fun getHomeActivities(output: MutableList<String>): String { output.add("test/.Home"); return "test/.Home" }
        fun replacePreferredActivity() { writes++ }
        fun clearPackagePreferredActivities() { writes++ }
        fun setApplicationEnabledSetting() { writes++ }
    }

    @Test fun canQueryHomesAndHandlePrimitiveArguments() {
        val pm = ReadOnlyPm(Fake())
        val homes = ArrayList<String>()
        assertEquals("test/.Home", pm.invoke("getHomeActivities", homes))
        assertEquals(listOf("test/.Home"), homes)
        assertEquals(0, pm.invoke("checkUidPermission", "test", 2000))
    }

    @Test fun refusesMutatorsEvenIfServiceExposesThem() {
        val service = Fake()
        val pm = ReadOnlyPm(service)
        for (name in listOf("replacePreferredActivity", "clearPackagePreferredActivities", "setApplicationEnabledSetting")) {
            assertThrows(IllegalArgumentException::class.java) { pm.invoke(name) }
        }
        assertEquals(0, service.writes)
    }

    @Test fun listingSignaturesNeverCallsThem() {
        val service = Fake()
        assertTrue(ReadOnlyPm(service).signatures(setOf("replacePreferredActivity")).isNotEmpty())
        assertEquals(0, service.writes)
    }
}
