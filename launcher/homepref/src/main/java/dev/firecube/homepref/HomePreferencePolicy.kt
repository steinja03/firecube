package dev.firecube.homepref

/** Narrow policy for this observed baseline: no existing Home or Firecube defaults. */
object HomePreferencePolicy {
    const val TARGET = "dev.firecube.launcher/.MainActivity"
    const val PACKAGE = "dev.firecube.launcher"

    fun requireBaseline(preferred: String?, homePreferences: Int, ownPreferences: Int,
                        targetEnabled: Boolean, permission: Int) {
        require(permission == 0) { "Preferred-app permission not granted" }
        require(preferred == null && homePreferences == 0) { "Existing Home preference; trial refuses to overwrite it" }
        require(ownPreferences == 0) { "Firecube has existing defaults; exact rollback is not established" }
        require(targetEnabled) { "Firecube is not an enabled/exported Home candidate" }
    }

    fun requireOwnedClear(ownPreferences: Int, exactOwnedHomePreferences: Int) {
        require(ownPreferences == 1 && exactOwnedHomePreferences == 1) {
            "Unexpected Firecube defaults; refusing a broad clear"
        }
    }
}
