package dev.firecube.inspect

import android.content.ComponentName
import android.content.Intent
import android.content.IntentFilter
import android.content.pm.ResolveInfo
import android.os.Build
import android.os.Process
import org.json.JSONArray
import org.json.JSONObject
import java.lang.reflect.InvocationTargetException

/** app_process entry point. No Activity, app install, input events or setters. */
object HomeInspector {
    @JvmStatic fun main(args: Array<String>) {
        val output = JSONObject().put("schema_version", 1).put("read_only", true)
            .put("mode", "inspect").put("uid", Process.myUid())
            .put("device", Build.DEVICE).put("sdk", Build.VERSION.SDK_INT)
            .put("fingerprint", Build.FINGERPRINT)
        try {
            require(args.contentEquals(arrayOf("inspect"))) { "Only inspect mode is supported" }
            require(Build.DEVICE == "tank" && Build.VERSION.SDK_INT == 22) { "Scoped to tank/API 22" }
            require(Process.myUid() == 2000) { "Expected ordinary ADB shell UID 2000" }
            val globals = Class.forName("android.app.AppGlobals")
            val getter = globals.getDeclaredMethod("getPackageManager")
            getter.isAccessible = true
            val pm = ReadOnlyPm(getter.invoke(null) ?: error("No package-manager service"))

            fun query(key: String, block: () -> Any?) {
                try { output.put(key, JSONObject().put("ok", true).put("result", block() ?: JSONObject.NULL)) }
                catch (error: Exception) {
                    val cause = if (error is InvocationTargetException) error.targetException else error
                    output.put(key, JSONObject().put("ok", false).put("error", cause.toString()))
                }
            }

            output.put("method_signatures", JSONArray(pm.signatures(setOf(
                "getHomeActivities", "getPreferredActivities", "replacePreferredActivity", "resolveIntent"))))
            query("permission_checks") {
                val permissions = JSONObject()
                for (permission in listOf("SET_PREFERRED_APPLICATIONS", "WRITE_SECURE_SETTINGS", "CHANGE_COMPONENT_ENABLED_STATE")) {
                    permissions.put(permission, pm.invoke("checkUidPermission", "android.permission." + permission, 2000))
                }
                permissions
            }
            query("home_candidates_and_preferred") {
                val homes = ArrayList<ResolveInfo>()
                val preferred = pm.invoke("getHomeActivities", homes) as? ComponentName
                val candidates = JSONArray()
                for (home in homes) {
                    val info = home.activityInfo ?: continue
                    candidates.put(JSONObject().put("component", ComponentName(info.packageName, info.name).flattenToShortString())
                        .put("exported", info.exported).put("enabled", info.enabled)
                        .put("permission", info.permission ?: JSONObject.NULL))
                }
                JSONObject().put("preferred", preferred?.flattenToShortString() ?: JSONObject.NULL)
                    .put("candidates", candidates)
            }
            query("resolved_home") {
                val intent = Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_HOME)
                val resolved = pm.invoke("resolveIntent", intent, null, 0, 0) as? ResolveInfo
                resolved?.activityInfo?.let { ComponentName(it.packageName, it.name).flattenToShortString() }
            }
            query("existing_home_preferences") {
                val filters = ArrayList<IntentFilter>()
                val activities = ArrayList<ComponentName>()
                pm.invoke("getPreferredActivities", filters, activities, null)
                val entries = JSONArray()
                for (index in 0 until minOf(filters.size, activities.size)) {
                    val filter = filters[index]
                    if (filter.hasAction(Intent.ACTION_MAIN) && filter.hasCategory(Intent.CATEGORY_HOME)) {
                        entries.put(JSONObject().put("component", activities[index].flattenToShortString())
                            .put("actions", JSONArray((0 until filter.countActions()).map { filter.getAction(it) }))
                            .put("categories", JSONArray((0 until filter.countCategories()).map { filter.getCategory(it) })))
                    }
                }
                entries
            }
            output.put("limitations", "Queries and exposed methods do not verify write permission, physical Home handling or recovery. No write method was invoked.")
        } catch (error: Exception) {
            val cause = if (error is InvocationTargetException) error.targetException else error
            output.put("fatal_error", cause.toString())
        }
        println(output.toString())
    }
}
