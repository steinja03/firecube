package dev.firecube.boothelper

import android.content.Context
import android.util.Base64
import android.system.Os
import java.security.interfaces.RSAPrivateKey
import java.io.File
import java.net.InetAddress
import java.net.InetSocketAddress
import java.net.Socket
import java.security.KeyFactory
import java.security.KeyPair
import java.security.KeyPairGenerator
import java.security.interfaces.RSAPublicKey
import java.security.spec.PKCS8EncodedKeySpec
import java.security.spec.X509EncodedKeySpec

/** Fixed IPv4 loopback only. Never connects to a LAN host or uploads the private key. */
class LocalAdb(context: Context) {
    private val keys: KeyPair
    init {
        Os.chmod(context.filesDir.path, 448) // Private key directory, owner only.
        val privateFile = File(context.filesDir, "adb-private.pk8")
        val publicFile = File(context.filesDir, "adb-public.der")
        keys = if (privateFile.exists() && publicFile.exists()) {
            val factory = KeyFactory.getInstance("RSA")
            KeyPair(factory.generatePublic(X509EncodedKeySpec(publicFile.readBytes())),
                factory.generatePrivate(PKCS8EncodedKeySpec(privateFile.readBytes())))
        } else {
            KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair().also {
                privateFile.writeBytes(it.private.encoded); publicFile.writeBytes(it.public.encoded)
            }
        }
        Os.chmod(privateFile.path, 384); Os.chmod(publicFile.path, 384)
        require((keys.private as RSAPrivateKey).modulus == (keys.public as RSAPublicKey).modulus) {
            "Local ADB key files do not match"
        }
    }
    fun shell(mode: String, pairing: Boolean = false): String {
        val command = LocalCommands.command(mode) // Validate before opening any socket.
        Socket().use { socket ->
            socket.connect(InetSocketAddress(InetAddress.getByAddress(byteArrayOf(127,0,0,1)), 5555), 5000)
            socket.soTimeout = if (pairing) 60000 else 15000
            socket.tcpNoDelay = true
            val input = socket.getInputStream(); val output = socket.getOutputStream()
            AdbWire.write(output, AdbWire.CNXN, 0x01000000, 4096, "host::\u0000".toByteArray())
            var signed = false
            var offered = false
            var connected = false
            for (step in 0 until 4) {
                val packet = AdbWire.read(input)
                if (packet.command == AdbWire.CNXN) { connected = true; break }
                require(packet.command == AdbWire.AUTH && packet.arg0 == 1) { "Unexpected ADB handshake" }
                if (!signed) { AdbWire.write(output, AdbWire.AUTH, 2, 0, AdbKeys.sign(keys.private, packet.data)); signed = true }
                else {
                    require(pairing && !offered) { "Local ADB key is not authorized; pair in the controller" }
                    val key = Base64.encodeToString(AdbKeys.publicBytes(keys.public as RSAPublicKey), Base64.NO_WRAP) + " firecube-home@localhost\u0000"
                    AdbWire.write(output, AdbWire.AUTH, 3, 0, key.toByteArray()); offered = true
                }
            }
            require(connected) { "Local ADB authorization was not completed" }
            AdbWire.write(output, AdbWire.OPEN, 1, 0, ("shell:$command\u0000").toByteArray())
            val result = StringBuilder()
            var remote = 0
            for (step in 0 until 128) {
                val packet = AdbWire.read(input)
                require(packet.arg1 == 1) { "Unexpected ADB stream" }
                when (packet.command) {
                    AdbWire.OKAY -> { require(remote == 0); remote = packet.arg0 }
                    AdbWire.WRTE -> {
                        require(remote != 0 && packet.arg0 == remote && result.length < 32768)
                        result.append(packet.data.toString(Charsets.UTF_8))
                        AdbWire.write(output, AdbWire.OKAY, 1, remote)
                    }
                    AdbWire.CLSE -> {
                        if (remote != 0) AdbWire.write(output, AdbWire.CLSE, 1, remote)
                        require(result.length <= 32768) { "Local response too large" }
                        return result.toString()
                    }
                    else -> error("Unexpected ADB stream packet")
                }
            }
            error("ADB packet limit reached")
        }
    }
}
