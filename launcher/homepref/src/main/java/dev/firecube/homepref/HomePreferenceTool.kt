package dev.firecube.homepref

import android.content.ComponentName
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ResolveInfo
import android.os.Build
import android.os.Process
import android.system.Os
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.lang.reflect.InvocationTargetException

/** Only the fixed Firecube Home preference may be written; never package state. */
object HomePreferenceTool {
    private lateinit var service: Any
    private val target = ComponentName.unflattenFromString(HomePreferencePolicy.TARGET)!!

    private fun call(name: String, vararg args: Any?): Any? {
        require(name in setOf("getHomeActivities", "getPreferredActivities", "resolveIntent",
            "checkUidPermission", "replacePreferredActivity", "clearPackagePreferredActivities"))
        val methods = service.javaClass.methods.filter { m ->
            m.name == name && m.parameterTypes.size == args.size && m.parameterTypes.zip(args).all { (type, arg) ->
                if (arg == null) !type.isPrimitive else if (type == Integer.TYPE) arg is Int else type.isInstance(arg)
            }
        }
        require(methods.size == 1) { "No unambiguous compatible $name interface" }
        return methods.single().apply { isAccessible = true }.invoke(service, *args)
    }

    private fun exactHome(filter: IntentFilter): Boolean = filter.countActions() == 1 &&
        filter.hasAction(Intent.ACTION_MAIN) && filter.countCategories() == 2 &&
        filter.hasCategory(Intent.CATEGORY_HOME) && filter.hasCategory(Intent.CATEGORY_DEFAULT) &&
        filter.countDataTypes() == 0 && filter.countDataSchemes() == 0 &&
        filter.countDataAuthorities() == 0 && filter.countDataPaths() == 0

    private data class State(val json: JSONObject, val candidates: Array<ComponentName>, val targetEnabled: Boolean)

    private fun state(): State {
        val homes = ArrayList<ResolveInfo>()
        val preferred = call("getHomeActivities", homes) as? ComponentName
        val components = homes.mapNotNull { it.activityInfo?.let { info -> ComponentName(info.packageName, info.name) } }.distinct().toTypedArray()
        val enabled = homes.any { it.activityInfo?.let { info ->
            ComponentName(info.packageName, info.name) == target && info.enabled && info.exported
        } == true }
        val allFilters = ArrayList<IntentFilter>(); val allActivities = ArrayList<ComponentName>()
        call("getPreferredActivities", allFilters, allActivities, null)
        val homeEntries = JSONArray()
        for (index in 0 until minOf(allFilters.size, allActivities.size)) {
            val filter = allFilters[index]
            if (filter.hasAction(Intent.ACTION_MAIN) && filter.hasCategory(Intent.CATEGORY_HOME)) {
                homeEntries.put(JSONObject().put("component", allActivities[index].flattenToShortString())
                    .put("exact_home_filter", exactHome(filter)))
            }
        }
        val ownFilters = ArrayList<IntentFilter>(); val ownActivities = ArrayList<ComponentName>()
        call("getPreferredActivities", ownFilters, ownActivities, HomePreferencePolicy.PACKAGE)
        val ownExact = ownFilters.indices.count { index ->
            index < ownActivities.size && ownActivities[index] == target && exactHome(ownFilters[index])
        }
        val resolved = call("resolveIntent", Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME), null, 0, 0) as? ResolveInfo
        val resolvedName = resolved?.activityInfo?.let { ComponentName(it.packageName, it.name).flattenToShortString() }
        val permission = call("checkUidPermission", "android.permission.SET_PREFERRED_APPLICATIONS", 2000) as Int
        val json = JSONObject().put("preferred", preferred?.flattenToShortString() ?: JSONObject.NULL)
            .put("resolved", resolvedName ?: JSONObject.NULL).put("home_preferences", homeEntries)
            .put("own_preference_count", ownFilters.size).put("own_exact_home_count", ownExact)
            .put("permission", permission).put("target_enabled", enabled)
            .put("candidates", JSONArray(components.map { it.flattenToShortString() }))
        return State(json, components, enabled)
    }

    private fun verifyBaseline(before: JSONObject) {
        HomePreferencePolicy.requireBaseline(if (before.isNull("preferred")) null else before.getString("preferred"),
            before.getJSONArray("home_preferences").length(), before.getInt("own_preference_count"),
            before.getBoolean("target_enabled"), before.getInt("permission"))
    }

    private fun restore(backup: JSONObject, onClearIntent: () -> Unit = {}): JSONObject {
        require(backup.getInt("schema_version") == 1 && backup.getString("device_identity") == Build.SERIAL &&
            backup.getString("fingerprint") == Build.FINGERPRINT) { "Backup belongs to another device or build" }
        val before = backup.getJSONObject("before")
        verifyBaseline(before)
        var current = state().json
        val own = current.getInt("own_preference_count")
        if (own != 0) {
            HomePreferencePolicy.requireOwnedClear(own, current.getInt("own_exact_home_count"))
            require(current.getInt("permission") == 0) { "Restore permission is not granted" }
            onClearIntent()
            call("clearPackagePreferredActivities", HomePreferencePolicy.PACKAGE)
        }
        current = state().json
        val restored = current.getInt("own_preference_count") == 0 &&
            current.getJSONArray("home_preferences").length() == 0 && current.isNull("preferred") &&
            current.opt("resolved") == before.opt("resolved")
        return JSONObject().put("restored", restored).put("clear_attempted", own != 0).put("after", current)
    }

    @JvmStatic fun main(args: Array<String>) {
        val output = JSONObject().put("schema_version", 1).put("uid", Process.myUid())
            .put("stock_launcher_disabled", false).put("accessibility_changed", false)
            .put("backup_written", false).put("mutation_attempted", false).put("rollback_attempted", false)
        try {
            require(Process.myUid() == 2000 && Build.DEVICE == "tank" && Build.VERSION.SDK_INT == 22 &&
                Build.FINGERPRINT.endsWith("/288.6.8.8_user_688806320:user/release-keys")) { "Unexpected UID, device or firmware" }
            require(Build.SERIAL.isNotBlank() && Build.SERIAL != "unknown") { "No stable device identity" }
            require(args.size in 1..2 && args[0] in setOf("inspect", "apply", "restore"))
            output.put("mode", args[0])
            val getter = Class.forName("android.app.AppGlobals").getDeclaredMethod("getPackageManager")
            getter.isAccessible = true; service = getter.invoke(null) ?: error("No package service")
            if (args[0] == "inspect") {
                output.put("state", state().json).put("ok", true)
            } else {
                require(args.size == 2 && args[1].matches(Regex("/data/local/tmp/firecube-homepref-backup-[0-9a-f]{16}\\.json"))) { "Invalid backup path" }
                val file = File(args[1])
                output.put("backup_path", file.path)
                if (args[0] == "restore") {
                    require(file.length() in 1..65536) { "Missing or invalid backup" }
                    val restored = restore(JSONObject(file.readText())) { output.put("mutation_attempted", true) }
                    output.put("rollback", restored).put("ok", restored.getBoolean("restored"))
                } else {
                    val current = state()
                    verifyBaseline(current.json)
                    require(!current.json.isNull("resolved")) { "Original fallback Home is unknown" }
                    val backup = JSONObject().put("schema_version", 1).put("device_identity", Build.SERIAL)
                        .put("fingerprint", Build.FINGERPRINT).put("before", current.json)
                    require(file.createNewFile()) { "Backup already exists; refusing overwrite" }
                    Os.chmod(file.path, 384) // 0600, own temporary backup only
                    FileOutputStream(file).use { stream ->
                        stream.write(backup.toString().toByteArray(Charsets.UTF_8)); stream.fd.sync()
                    }
                    output.put("backup_written", true).put("before", current.json)
                    val fresh = state()
                    require(fresh.json.toString() == current.json.toString()) { "Home state changed during backup" }
                    val filter = IntentFilter(Intent.ACTION_MAIN).apply {
                        addCategory(Intent.CATEGORY_HOME); addCategory(Intent.CATEGORY_DEFAULT)
                    }
                    output.put("mutation_attempted", true)
                    call("replacePreferredActivity", filter, IntentFilter.MATCH_CATEGORY_EMPTY, current.candidates, target, 0)
                    val after = state().json
                    val observed = after.getInt("own_preference_count") == 1 && after.getInt("own_exact_home_count") == 1 &&
                        after.optString("resolved") == HomePreferencePolicy.TARGET
                    output.put("after", after).put("preference_observed", observed).put("ok", observed)
                    if (!observed) {
                        output.put("rollback_attempted", true)
                        output.put("rollback", restore(backup) { output.put("rollback_write_attempted", true) })
                    }
                }
            }
        } catch (error: Exception) {
            val cause = if (error is InvocationTargetException) error.targetException else error
            output.put("ok", false).put("error", cause.toString())
        }
        println(output.toString())
    }
}
