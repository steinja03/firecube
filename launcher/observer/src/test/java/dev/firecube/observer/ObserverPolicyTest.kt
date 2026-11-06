package dev.firecube.observer

import org.junit.Assert.*
import org.junit.Test

class ObserverPolicyTest {
    private val home = "com.amazon.tv.launcher/.ui.HomeActivity_vNext"
    @Test fun onlyExactUserZeroHomeEventsAreEligible() {
        val line = "11-06 13:00:00.000 1 2 I am_resume_activity: [0,42,7,$home]"
        assertTrue(ObserverPolicy.homeEvent(line))
        assertFalse(ObserverPolicy.homeEvent(line.replace("[0,", "[10,")))
        assertFalse(ObserverPolicy.homeEvent(line.replace(home, ObserverPolicy.TARGET)))
        assertFalse(ObserverPolicy.homeEvent(line.replace(home, home + "Other")))
        assertFalse(ObserverPolicy.homeEvent(line.replace("am_resume_activity", "am_on_resume_called")))
    }
    @Test fun foregroundMustBeUnambiguousAndUserZero() {
        val line = "mResumedActivity: ActivityRecord{abc u0 $home t1}"
        assertEquals(home, ObserverPolicy.foreground(line))
        assertNull(ObserverPolicy.foreground(line.replace("u0", "u10")))
        assertNull(ObserverPolicy.foreground("$line\n$line"))
        assertNull(ObserverPolicy.foreground("mResumedActivity: null"))
    }
    @Test fun rapidLoopIsRejectedButOrdinaryRepeatedHomeWorks() {
        val budget = RedirectBudget()
        budget.accept(10000)
        try { budget.accept(11000); fail("Loop accepted") } catch (_: IllegalArgumentException) { }
        budget.accept(13000)
        budget.accept(23000)
    }
    @Test fun sustainedBurstIsRejected() {
        val budget = RedirectBudget()
        for (index in 0..5) budget.accept(index * 1500L)
        try { budget.accept(9000); fail("Burst accepted") } catch (_: IllegalArgumentException) { }
        budget.accept(11000)
    }
}
