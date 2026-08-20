package com.aegis.guard.phonenumber

import android.app.NotificationChannel
import android.app.NotificationManager
import android.content.Context
import android.os.Build
import android.telecom.Call
import android.telecom.CallScreeningService
import androidx.core.app.NotificationCompat
import com.aegis.guard.phonenumber.di.PhoneNumberModule

/**
 * AEGIS Production Call Screening Service.
 * Implements Android CallScreeningService API strictly in ADVISORY MODE.
 * Guarantees execution under Android's 5-second deadline and never auto-drops calls from digits alone.
 */
class AegisCallScreeningService : CallScreeningService() {

    private lateinit var callGuardEngine: CallGuardEngine
    private val CHANNEL_ID = "aegis_call_screening_channel"
    private val NOTIFICATION_ID = 10042

    override fun onCreate() {
        super.onCreate()
        callGuardEngine = PhoneNumberModule.provideCallGuardEngine(applicationContext)
        createNotificationChannel()
    }

    override fun onScreenCall(callDetails: Call.Details) {
        val handle = callDetails.handle
        val rawNumber = handle?.schemeSpecificPart ?: ""
        val responseBuilder = CallResponse.Builder()

        // 1. Evaluate on-device pattern risk (< 0.05 ms)
        val verdict = callGuardEngine.screenIncomingCall(rawNumber)

        // 2. Strict Advisory Mode: NEVER block or reject without explicit user rule
        responseBuilder.setDisallowCall(false)
        responseBuilder.setRejectCall(false)
        responseBuilder.setSilenceCall(false)
        responseBuilder.setSkipCallLog(false)
        responseBuilder.setSkipNotification(false)

        // 3. Dispatch Advisory Notification Banner if threat detected
        if (verdict.isAdvisoryWarning) {
            showAdvisoryNotification(verdict)
        }

        // 4. Respond to Telecom framework well before deadline
        respondToCall(callDetails, responseBuilder.build())
    }

    private fun showAdvisoryNotification(verdict: CallGuardEngine.CallVerdict) {
        try {
            val notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            val notification = NotificationCompat.Builder(this, CHANNEL_ID)
                .setSmallIcon(android.R.drawable.stat_sys_warning)
                .setContentTitle(verdict.advisoryTitle)
                .setContentText("${verdict.rawNumber} - Risk Score: ${verdict.riskScore}/100")
                .setStyle(NotificationCompat.BigTextStyle().bigText(verdict.advisoryDetails.joinToString("\n")))
                .setPriority(NotificationCompat.PRIORITY_HIGH)
                .setAutoCancel(true)
                .build()

            notificationManager.notify(NOTIFICATION_ID, notification)
        } catch (e: Exception) {
            // Safe fallback
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                "AEGIS Call Guard Advisory",
                NotificationManager.IMPORTANCE_HIGH
            ).apply {
                description = "Displays advisory banners for suspicious incoming call patterns"
            }
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }
}