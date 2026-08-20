package com.aegis.guard.phonenumber

import org.json.JSONObject
import java.io.BufferedReader
import java.io.InputStreamReader
import java.net.HttpURLConnection
import java.net.URL
import java.net.URLEncoder
import java.util.concurrent.TimeUnit

/**
 * Android Client for AEGIS Backend Reputation Proxy.
 * Connects securely to self-hosted Aegis backend with timeouts, authentication, and structured UNAVAILABLE handling.
 */
class IpqsReputationClient(
    private val baseUrl: String = "https://api.aegis-guard.internal",
    private val clientApiKey: String = ""
) {

    data class ReputationResult(
        val status: String, // SUCCESS, CACHED, UNAVAILABLE, RATE_LIMITED
        val isRisky: Boolean?,
        val fraudScore: Int?,
        val lineType: String?,
        val carrier: String?,
        val message: String
    )

    fun queryReputation(normalizedE164: String, country: String = "IN"): ReputationResult {
        return try {
            val endpoint = "$baseUrl/reputation/ipqs"
            val url = URL(endpoint)
            val conn = url.openConnection() as HttpURLConnection
            conn.requestMethod = "POST"
            conn.connectTimeout = 1500 // 1.5s max connect timeout
            conn.readTimeout = 1500    // 1.5s max read timeout
            conn.doOutput = true
            conn.setRequestProperty("Content-Type", "application/json")
            if (clientApiKey.isNotEmpty()) {
                conn.setRequestProperty("X-AEGIS-API-KEY", clientApiKey)
            }

            val body = JSONObject().apply {
                put("normalized_e164", normalizedE164)
                put("country", country)
            }.toString()

            conn.outputStream.use { os ->
                os.write(body.toByteArray(Charsets.UTF_8))
            }

            val code = conn.responseCode
            if (code == 200) {
                val responseText = BufferedReader(InputStreamReader(conn.inputStream)).readText()
                val json = JSONObject(responseText)
                val status = json.optString("status", "UNAVAILABLE")
                val isRisky = if (json.isNull("is_risky")) null else json.optBoolean("is_risky")
                val fraudScore = if (json.isNull("fraud_score")) null else json.optInt("fraud_score")
                val lineType = json.optString("line_type", null)
                val carrier = json.optString("carrier", null)
                val message = json.optString("message", "OK")

                ReputationResult(
                    status = status,
                    isRisky = isRisky,
                    fraudScore = fraudScore,
                    lineType = lineType,
                    carrier = carrier,
                    message = message
                )
            } else {
                ReputationResult(
                    status = "UNAVAILABLE",
                    isRisky = null,
                    fraudScore = null,
                    lineType = null,
                    carrier = null,
                    message = "Backend proxy returned HTTP $code"
                )
            }
        } catch (e: Exception) {
            ReputationResult(
                status = "UNAVAILABLE",
                isRisky = null,
                fraudScore = null,
                lineType = null,
                carrier = null,
                message = "Reputation proxy connection timed out or network offline"
            )
        }
    }
}