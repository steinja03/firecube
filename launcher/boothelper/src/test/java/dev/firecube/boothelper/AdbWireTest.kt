package dev.firecube.boothelper

import org.junit.Assert.*
import org.junit.Test
import java.io.ByteArrayInputStream
import java.io.ByteArrayOutputStream

class AdbWireTest {
    @Test fun framesPreserveUnsignedChecksumsAndArguments() {
        val output = ByteArrayOutputStream()
        val data = byteArrayOf(0,127,-1,-128)
        AdbWire.write(output, AdbWire.WRTE, 7, 9, data)
        val packet = AdbWire.read(ByteArrayInputStream(output.toByteArray()))
        assertEquals(AdbWire.WRTE, packet.command); assertEquals(7, packet.arg0); assertEquals(9, packet.arg1)
        assertArrayEquals(data, packet.data)
    }
    @Test fun corruptedFramesAreRejected() {
        val output = ByteArrayOutputStream(); AdbWire.write(output, AdbWire.WRTE, 1, 2, byteArrayOf(5))
        val data = output.toByteArray(); data[24] = 6
        try { AdbWire.read(ByteArrayInputStream(data)); fail("Bad checksum accepted") } catch (_: IllegalArgumentException) { }
        data[20] = (data[20].toInt() xor 1).toByte()
        try { AdbWire.read(ByteArrayInputStream(data)); fail("Bad magic accepted") } catch (_: IllegalArgumentException) { }
    }
    @Test fun onlyFixedObserverCommandsAreAllowed() {
        assertTrue(LocalCommands.command("start").startsWith("sh /data/local/tmp/firecube-observer/"))
        for (mode in listOf("root", "start; reboot", "shell", "")) {
            try { LocalCommands.command(mode); fail("Unexpected command allowed") } catch (_: IllegalStateException) { }
        }
    }
    @Test fun staleReadyStateFromBeforeRebootNeverCountsAsNewSession() {
        assertFalse(ControllerPolicy.newSessionReady(true, "old", "old"))
        assertFalse(ControllerPolicy.newSessionReady(true, null, "old"))
        assertFalse(ControllerPolicy.newSessionReady(false, "new", "old"))
        assertTrue(ControllerPolicy.newSessionReady(true, "new", "old"))
    }
}
