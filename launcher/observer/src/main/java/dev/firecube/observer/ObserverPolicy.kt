package dev.firecube.observer

object ObserverPolicy {
    const val TARGET = "dev.firecube.launcher/.MainActivity"
    const val FINGERPRINT = "Amazon/full_tank/tank:5.1.1/LVY48F/288.6.8.8_user_688806320:user/release-keys"
    private val homes = setOf("com.amazon.tv.launcher/.ui.HomeActivity_vNext", "com.amazon.tv.launcher/.ui.HomeActivity",
        "com.amazon.tv.launcher/com.amazon.tv.launcher.ui.HomeActivity_vNext", "com.amazon.tv.launcher/com.amazon.tv.launcher.ui.HomeActivity")
    fun isHome(component: String?) = component in homes
    fun isFirecube(component: String?) = component == TARGET || component == "dev.firecube.launcher/dev.firecube.launcher.MainActivity"
    fun homeEvent(line: String): Boolean {
        val match = Regex("\\bam_resume_activity\\s*:\\s*\\[([^]]+)\\]\\s*$").find(line) ?: return false
        val fields = match.groupValues[1].split(',').map { it.trim() }
        return fields.size == 4 && fields[0] == "0" && isHome(fields[3])
    }
    fun foreground(text: String): String? {
        val lines = text.lines().filter { "mResumedActivity" in it }
        if (lines.size != 1) return null
        return Regex("\\bu0\\s+([A-Za-z0-9_.]+/[A-Za-z0-9_.$]+)").find(lines.single())?.groupValues?.get(1)
    }
}

class RedirectBudget {
    private val recent = ArrayList<Long>()
    fun accept(now: Long) {
        require(recent.isEmpty() || now - recent.last() >= 1500) { "Rapid Home loop; observer stopped" }
        recent.removeAll { now - it >= 10000 }
        require(recent.size < 6) { "Home redirect burst; observer stopped" }
        recent.add(now)
    }
}
