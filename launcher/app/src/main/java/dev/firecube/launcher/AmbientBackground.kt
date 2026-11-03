package dev.firecube.launcher

import android.content.Context
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.LinearGradient
import android.graphics.Paint
import android.graphics.RadialGradient
import android.graphics.Shader
import android.view.View

/** Static vector backdrop: no image assets, network, blur buffers or frame loop. */
class AmbientBackground(context: Context, private val top: String, private val bottom: String,
                        private val accent: String) : View(context) {
    private val paint = Paint(Paint.ANTI_ALIAS_FLAG or Paint.DITHER_FLAG)
    private var base: Shader? = null
    private var glow: Shader? = null

    init {
        isFocusable = false
        importantForAccessibility = IMPORTANT_FOR_ACCESSIBILITY_NO
    }

    override fun onSizeChanged(w: Int, h: Int, oldw: Int, oldh: Int) {
        if (w <= 0 || h <= 0) return
        base = LinearGradient(0f, 0f, w.toFloat(), h.toFloat(),
            Color.parseColor(top), Color.parseColor(bottom), Shader.TileMode.CLAMP)
        val color = Color.parseColor(accent)
        glow = RadialGradient(w * 0.12f, h * 0.1f, w * 0.68f,
            Color.argb(24, Color.red(color), Color.green(color), Color.blue(color)),
            Color.TRANSPARENT, Shader.TileMode.CLAMP)
    }

    override fun onDraw(canvas: Canvas) {
        paint.shader = base; canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), paint)
        paint.shader = glow; canvas.drawRect(0f, 0f, width.toFloat(), height.toFloat(), paint)
        paint.shader = null
    }
}
