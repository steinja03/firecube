package dev.firecube.boothelper

import org.junit.Assert.*
import org.junit.Test
import java.math.BigInteger
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.KeyPairGenerator
import java.security.interfaces.RSAPublicKey
import javax.crypto.Cipher

class AdbKeysTest {
    @Test fun publicStructureMatchesRsaKeyAndMontgomeryParameters() {
        val keys = KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()
        val pub = keys.public as RSAPublicKey
        val data = AdbKeys.publicBytes(pub)
        assertEquals(524, data.size)
        val buffer = ByteBuffer.wrap(data).order(ByteOrder.LITTLE_ENDIAN)
        assertEquals(64, buffer.int)
        val inverse = buffer.int.toLong() and 0xffffffffL
        val base = BigInteger.ONE.shiftLeft(32)
        assertEquals(BigInteger.ZERO, pub.modulus.multiply(BigInteger.valueOf(inverse)).add(BigInteger.ONE).mod(base))
        var modulus = BigInteger.ZERO; var rr = BigInteger.ZERO
        for (index in 0 until 64) modulus = modulus.or(BigInteger.valueOf(buffer.int.toLong() and 0xffffffffL).shiftLeft(index * 32))
        for (index in 0 until 64) rr = rr.or(BigInteger.valueOf(buffer.int.toLong() and 0xffffffffL).shiftLeft(index * 32))
        assertEquals(pub.modulus, modulus)
        assertEquals(BigInteger.ONE.shiftLeft(4096).mod(modulus), rr)
        assertEquals(pub.publicExponent.toInt(), buffer.int)
    }
    @Test fun signatureIsPkcs1Sha1DigestInfoWithoutHashingTokenAgain() {
        val keys = KeyPairGenerator.getInstance("RSA").apply { initialize(2048) }.generateKeyPair()
        val token = ByteArray(20) { it.toByte() }
        val signed = AdbKeys.sign(keys.private, token)
        val decoded = Cipher.getInstance("RSA/ECB/PKCS1Padding").apply { init(Cipher.DECRYPT_MODE, keys.public) }.doFinal(signed)
        assertEquals(35, decoded.size)
        assertArrayEquals(token, decoded.copyOfRange(15,35))
        assertArrayEquals(byteArrayOf(0x30,0x21,0x30,0x09,0x06,0x05,0x2b,0x0e,0x03,0x02,0x1a,0x05,0,0x04,0x14), decoded.copyOfRange(0,15))
        try { AdbKeys.sign(keys.private, byteArrayOf(1)); fail("Short token accepted") } catch (_: IllegalArgumentException) { }
    }
}
