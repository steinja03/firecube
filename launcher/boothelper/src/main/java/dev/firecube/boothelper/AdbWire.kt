package dev.firecube.boothelper

import java.io.DataInputStream
import java.io.InputStream
import java.io.OutputStream
import java.nio.ByteBuffer
import java.nio.ByteOrder

/** ADB v1 framing. Authentication/key layout adapted from Cameron Gutman's BSD AdbLib.
 * See assets/AdbLib-LICENSE.txt. Only one fixed local shell stream is supported. */
object AdbWire {
    const val CNXN = 0x4e584e43
    const val AUTH = 0x48545541
    const val OPEN = 0x4e45504f
    const val OKAY = 0x59414b4f
    const val WRTE = 0x45545257
    const val CLSE = 0x45534c43
    data class Packet(val command: Int, val arg0: Int, val arg1: Int, val data: ByteArray)
    fun write(output: OutputStream, command: Int, arg0: Int, arg1: Int, data: ByteArray = byteArrayOf()) {
        require(data.size <= 4096)
        val header = ByteBuffer.allocate(24).order(ByteOrder.LITTLE_ENDIAN)
            .putInt(command).putInt(arg0).putInt(arg1).putInt(data.size)
            .putInt(data.sumOf { it.toInt() and 255 }).putInt(command.inv()).array()
        output.write(header); output.write(data); output.flush()
    }
    fun read(input: InputStream): Packet {
        val stream = DataInputStream(input)
        val header = ByteArray(24); stream.readFully(header)
        val values = ByteBuffer.wrap(header).order(ByteOrder.LITTLE_ENDIAN)
        val command = values.int; val arg0 = values.int; val arg1 = values.int
        val length = values.int; val checksum = values.int; val magic = values.int
        require(magic == command.inv() && length in 0..4096) { "Invalid ADB frame" }
        val data = ByteArray(length); stream.readFully(data)
        require(data.sumOf { it.toInt() and 255 } == checksum) { "Invalid ADB checksum" }
        return Packet(command, arg0, arg1, data)
    }
}

object LocalCommands {
    private const val TOOL = "CLASSPATH=/data/local/tmp/firecube-shell-observer-0.1.0.apk app_process /system/bin dev.firecube.observer.ShellObserver "
    val allowed = mapOf("status" to TOOL + "status", "stop" to TOOL + "stop",
        "start" to "sh /data/local/tmp/firecube-observer/start.sh")
    fun command(mode: String): String = allowed[mode] ?: error("Unapproved local ADB command")
}

object ControllerPolicy {
    fun newSessionReady(currentReady: Boolean, session: String?, previous: String?) =
        currentReady && !session.isNullOrBlank() && session != previous
}
