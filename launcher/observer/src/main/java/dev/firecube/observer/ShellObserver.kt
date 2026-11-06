package dev.firecube.observer

import android.os.Build
import android.os.Process
import android.os.SystemClock
import android.system.Os
import org.json.JSONObject
import java.io.File
import java.io.FileOutputStream
import java.nio.channels.FileLock
import java.util.UUID
import java.util.concurrent.atomic.AtomicReference

/** Runs as existing ADB shell UID, never as an installed Android app or root. */
object ShellObserver {
    private val root = File("/data/local/tmp/firecube-observer")
    private val stopFile = File(root, "stop")
    private val statusFile = File(root, "status.json")
    @Volatile private var running = true
    @Volatile private var ready = false
    @Volatile private var reason = ""
    @Volatile private var redirects = 0
    @Volatile private var restarts = 0
    @Volatile private var lastForeground: String? = null
    @Volatile private var lastRedirect = 0L
    @Volatile private var currentStream: java.lang.Process? = null
    @Volatile private var lastStatus = 0L
    private val session = UUID.randomUUID().toString()
    private var started = 0L

    private fun setup() {
        require(Process.myUid() == 2000 && Build.DEVICE == "tank" && Build.VERSION.SDK_INT == 22 &&
            Build.FINGERPRINT == ObserverPolicy.FINGERPRINT) { "Unexpected UID/device/firmware" }
        require(root.exists() || root.mkdir()) { "Cannot create observer directory" }
        require(root.canonicalPath == root.path && root.isDirectory && Os.stat(root.path).st_uid == 2000) { "Invalid observer directory" }
        Os.chmod(root.path, 448) // 0700
    }

    @Synchronized private fun publish(state: String) {
        val value = JSONObject().put("schema_version", 1).put("session", session).put("state", state)
            .put("pid", Process.myPid()).put("uid", Process.myUid()).put("ready", ready)
            .put("uptime_ms", SystemClock.elapsedRealtime()).put("started_uptime_ms", started)
            .put("redirects", redirects).put("stream_restarts", restarts).put("reason", reason)
            .put("last_foreground", lastForeground ?: JSONObject.NULL).put("last_redirect_uptime_ms", lastRedirect)
            .put("pc_required_while_running", false).put("detached_session", true).put("reboot_autostart", false)
        val temp = File(root, "status.next")
        temp.writeText(value.toString())
        require(temp.renameTo(statusFile)) { "Cannot publish observer state" }
        lastStatus = SystemClock.elapsedRealtime()
    }

    private fun requestStop(message: String) {
        reason = message
        running = false
        ready = false
        currentStream?.destroy()
    }

    /** API22 compatible timeout, bounded capture, no shell interpolation. */
    private fun command(vararg args: String): String {
        val child = ProcessBuilder(*args).redirectErrorStream(true).start()
        val output = StringBuilder()
        val failure = AtomicReference<Throwable?>(null)
        val reader = Thread {
            try {
                child.inputStream.bufferedReader().use { input ->
                    input.forEachLine {
                        require(output.length + it.length < 1024 * 1024) { "Command output too large" }
                        output.append(it).append('\n')
                    }
                }
            } catch (error: Throwable) { failure.set(error) }
        }.apply { isDaemon = true; start() }
        val deadline = SystemClock.elapsedRealtime() + 12000
        try {
            var code: Int? = null
            while (code == null && SystemClock.elapsedRealtime() < deadline && running) {
                code = try { child.exitValue() } catch (_: IllegalThreadStateException) { null }
                if (code == null) Thread.sleep(50)
            }
            require(code != null) { "Command timed out or observer stopped" }
            reader.join(1000)
            require(!reader.isAlive && failure.get() == null && code == 0) { "Command failed: ${args.first()}" }
            return output.toString()
        } finally { child.destroy() }
    }

    private fun foreground(): String? = ObserverPolicy.foreground(command("/system/bin/dumpsys", "activity", "activities"))

    private fun redirect(budget: RedirectBudget) {
        lastForeground = foreground()
        if (!ObserverPolicy.isHome(lastForeground)) return // Do not act on stale Home events during playback.
        budget.accept(SystemClock.elapsedRealtime())
        publish("redirecting")
        val result = command("/system/bin/am", "start", "--user", "0", "-n", ObserverPolicy.TARGET, "-f", "0x10200000")
        require(!Regex("(?im)^\\s*(Error:|Exception|java\\..*Exception|Permission Denial)").containsMatchIn(result)) { "Firecube launch refused" }
        var seen = false
        for (attempt in 0 until 24) {
            if (!running) break
            lastForeground = foreground()
            if (ObserverPolicy.isFirecube(lastForeground)) { seen = true; break }
            Thread.sleep(250)
        }
        require(seen) { "Firecube foreground not verified; observer stopped" }
        redirects++
        lastRedirect = SystemClock.elapsedRealtime()
        publish("monitoring")
    }

    private fun serve() {
        Os.setsid() // Separate the observer from the launching ADB shell session/process group.
        FileOutputStream(File(root, "session.lock"), true).channel.use { channel ->
            val lock: FileLock = channel.tryLock() ?: error("Observer already running")
            try {
                stopFile.delete()
                started = SystemClock.elapsedRealtime()
                publish("starting")
                val watchdog = Thread {
                    try {
                        while (running) {
                            if (stopFile.exists()) { requestStop("Stopped by user"); break }
                            if (SystemClock.elapsedRealtime() - lastStatus >= 30000) publish(if (ready) "monitoring" else "reconnecting")
                            Thread.sleep(500)
                        }
                    } catch (_: Exception) { requestStop("Watchdog failed") }
                }.apply { isDaemon = true; start() }
                val failures = ArrayList<Long>()
                val budget = RedirectBudget()
                try {
                    while (running) {
                        ready = false
                        val marker = UUID.randomUUID().toString()
                        val stream = ProcessBuilder("/system/bin/logcat", "-b", "main", "-b", "events", "-v", "threadtime",
                            "am_resume_activity:I", "FirecubeObserver:I", "*:S").redirectErrorStream(true).start()
                        currentStream = stream
                        val markerDeadline = SystemClock.elapsedRealtime() + 10000
                        val guard = Thread {
                            try {
                                while (running && !ready && SystemClock.elapsedRealtime() < markerDeadline) Thread.sleep(100)
                                if (!ready) stream.destroy()
                            } catch (_: InterruptedException) { /* Stream finished or marker was observed. */ }
                        }.apply { isDaemon = true; start() }
                        try {
                            command("/system/bin/log", "-p", "i", "-t", "FirecubeObserver", marker)
                            stream.inputStream.bufferedReader().use { input ->
                                while (running) {
                                    val line = input.readLine() ?: break
                                    if (!ready) {
                                        if (Regex("\\bFirecubeObserver\\s*:\\s*" + Regex.escape(marker) + "\\s*$").containsMatchIn(line)) {
                                            ready = true; reason = ""; publish("initializing")
                                            // A boot may already be sitting on Amazon Home before fresh logs begin.
                                            // Reconcile only the current Home foreground; never interrupt another app.
                                            try {
                                                if (ObserverPolicy.isHome(foreground())) redirect(budget)
                                                if (running) publish("monitoring")
                                            } catch (error: Exception) { requestStop(error.message ?: "Initial Home check failed") }
                                        }
                                    } else if (ObserverPolicy.homeEvent(line)) {
                                        try { redirect(budget) } catch (error: Exception) { requestStop(error.message ?: "Redirect failed") }
                                    }
                                }
                            }
                        } catch (error: Exception) {
                            if (running) reason = "Event stream interrupted: ${error.javaClass.simpleName}"
                        } finally { stream.destroy(); currentStream = null; guard.interrupt() }
                        if (!running) break
                        ready = false
                        val now = SystemClock.elapsedRealtime()
                        failures.removeAll { now - it >= 60000 }; failures.add(now)
                        restarts++
                        if (failures.size >= 5) { requestStop("Repeated log stream failures; observer stopped"); break }
                        publish("reconnecting")
                        Thread.sleep(1000L * failures.size)
                    }
                } finally {
                    running = false; ready = false; currentStream?.destroy()
                    watchdog.join(1500)
                    publish("stopped")
                }
            } finally { lock.release() }
        }
    }

    private fun status(): JSONObject {
        var alive = false
        FileOutputStream(File(root, "session.lock"), true).channel.use { channel ->
            val lock = channel.tryLock()
            if (lock == null) alive = true else lock.release()
        }
        return JSONObject().put("alive", alive).put("snapshot", if (statusFile.exists()) JSONObject(statusFile.readText()) else JSONObject.NULL)
    }

    @JvmStatic fun main(args: Array<String>) {
        val result = JSONObject().put("schema_version", 1).put("uid", Process.myUid())
        try {
            setup()
            require(args.size == 1 && args[0] in setOf("serve", "status", "stop")) { "Invalid command" }
            result.put("mode", args[0])
            when (args[0]) {
                "serve" -> serve()
                "status" -> result.put("status", status())
                "stop" -> {
                    if (status().getBoolean("alive")) stopFile.writeText("stop\n")
                    result.put("stop_requested", true)
                }
            }
            result.put("ok", true)
        } catch (error: Exception) { result.put("ok", false).put("error", error.toString()) }
        println(result.toString())
    }
}
