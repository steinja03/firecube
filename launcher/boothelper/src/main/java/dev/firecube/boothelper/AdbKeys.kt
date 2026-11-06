package dev.firecube.boothelper

import java.math.BigInteger
import java.nio.ByteBuffer
import java.nio.ByteOrder
import java.security.interfaces.RSAPublicKey
import javax.crypto.Cipher

/** RSA structure and signing adapted from Cameron Gutman's BSD AdbLib.
 * Copyright (c) 2013, Cameron Gutman. See assets/AdbLib-LICENSE.txt. */
object AdbKeys {
    fun publicBytes(key: RSAPublicKey): ByteArray {
        val base = BigInteger.ONE.shiftLeft(32)
        val modulus = key.modulus
        val rr = BigInteger.ONE.shiftLeft(2048).modPow(BigInteger.valueOf(2), modulus)
        val buffer = ByteBuffer.allocate(524).order(ByteOrder.LITTLE_ENDIAN)
        buffer.putInt(64).putInt(modulus.remainder(base).modInverse(base).negate().toInt())
        for (index in 0 until 64) buffer.putInt(modulus.shiftRight(index * 32).toInt())
        for (index in 0 until 64) buffer.putInt(rr.shiftRight(index * 32).toInt())
        buffer.putInt(key.publicExponent.toInt())
        return buffer.array()
    }
    fun sign(privateKey: java.security.PrivateKey, token: ByteArray): ByteArray {
        require(token.size == 20)
        val digestHeader = byteArrayOf(0x30,0x21,0x30,0x09,0x06,0x05,0x2b,0x0e,0x03,0x02,0x1a,0x05,0x00,0x04,0x14)
        val block = ByteArray(256) { 0xff.toByte() }
        block[0] = 0; block[1] = 1
        val offset = 256 - digestHeader.size - token.size
        block[offset - 1] = 0
        digestHeader.copyInto(block, offset); token.copyInto(block, offset + digestHeader.size)
        return Cipher.getInstance("RSA/ECB/NoPadding").apply { init(Cipher.ENCRYPT_MODE, privateKey) }.doFinal(block)
    }
}
