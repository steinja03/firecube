package dev.firecube.homepref

import org.junit.Assert.*
import org.junit.Test

class HomePreferencePolicyTest {
    @Test fun acceptsOnlyEmptyObservedBaselineWithGrantedPermission() {
        HomePreferencePolicy.requireBaseline(null, 0, 0, true, 0)
        assertThrows(IllegalArgumentException::class.java) { HomePreferencePolicy.requireBaseline("other/.Home", 1, 0, true, 0) }
        assertThrows(IllegalArgumentException::class.java) { HomePreferencePolicy.requireBaseline(null, 0, 1, true, 0) }
        assertThrows(IllegalArgumentException::class.java) { HomePreferencePolicy.requireBaseline(null, 0, 0, false, 0) }
        assertThrows(IllegalArgumentException::class.java) { HomePreferencePolicy.requireBaseline(null, 0, 0, true, -1) }
    }

    @Test fun cannotClearUnrelatedFirecubeDefaults() {
        HomePreferencePolicy.requireOwnedClear(1, 1)
        assertThrows(IllegalArgumentException::class.java) { HomePreferencePolicy.requireOwnedClear(2, 1) }
        assertThrows(IllegalArgumentException::class.java) { HomePreferencePolicy.requireOwnedClear(1, 0) }
    }
}
