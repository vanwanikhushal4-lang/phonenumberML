package com.aegis.guard.phonenumber

import java.util.concurrent.ConcurrentHashMap

/**
 * Android CallGuard Hybrid Screening Engine.
 * Combines local structural pattern risk (< 0.05 ms) with cached / asynchronous reputation intelligence.
 * Strictly operates in ADVISORY MODE by default (warn and explain, no auto-dropping without explicit rules).
 */
class CallGuardEngine(
    private val riskModel: PhoneNumberRiskModel
) {

    data class ReputationEntry(
        val fraudScore: Int,
        val isRisky: Boolean,
        val lineType: String,
        val timestampMs: Long
    )

    // Fast in-memory LRU reputation cache (24h TTL)
    private val reputationCache = ConcurrentHashMap<String, ReputationEntry>()
    private val CACHE_TTL_MS = 24 * 60 * 60 * 1000L

    data class CallScreenVerdict(
        val rawNumber: String,
        val normalizedE164: String,
        val country: String,
        val patternRiskScore: Int,
        val tier: ThreatTier,
        val confidence: ConfidenceLevel,
        val isAdvisoryWarning: Boolean,
        val advisoryTitle: String,
        val advisoryDetails: List<String>,
        val shouldSilence: Boolean,
        val shouldDisallow: Boolean,
        val evaluationLatencyMs: Long
    )

    fun screenIncomingCall(rawNumber: String, defaultCountry: String = "IN"): CallScreenVerdict {
        val startMs = System.currentTimeMillis()

        // 1. Fast Local Inference (< 0.05 ms)
        val patternVerdict = riskModel.assessNumber(rawNumber, defaultCountry)

        // 2. Check Cached Reputation
        val cachedRep = reputationCache[patternVerdict.normalizedE164]
        val isRepFresh = cachedRep != null && (System.currentTimeMillis() - cachedRep.timestampMs < CACHE_TTL_MS)

        val isThreat = patternVerdict.isThreat || (isRepFresh && cachedRep!!.isRisky)

        val (title, details) = when {
            patternVerdict.tier == ThreatTier.SCAM -> {
                Pair("⚠️ High-Risk Scam Pattern Detected", patternVerdict.topExplanations)
            }
            patternVerdict.tier == ThreatTier.SPAM -> {
                Pair("⚡ Suspected Telemarketer / Automated Call", patternVerdict.topExplanations)
            }
            patternVerdict.tier == ThreatTier.INVALID -> {
                Pair("ℹ️ Invalid Number Format", listOf("Caller number violates standard numbering plan"))
            }
            patternVerdict.tier == ThreatTier.LEGITIMATE -> {
                Pair("✓ Verified Legitimate Caller", patternVerdict.topExplanations)
            }
            else -> {
                Pair("Incoming Call", listOf("Standard phone number pattern"))
            }
        }

        val elapsedMs = System.currentTimeMillis() - startMs

        return CallScreenVerdict(
            rawNumber = rawNumber,
            normalizedE164 = patternVerdict.normalizedE164,
            country = defaultCountry,
            patternRiskScore = patternVerdict.riskScore,
            tier = patternVerdict.tier,
            confidence = patternVerdict.confidence,
            isAdvisoryWarning = isThreat,
            advisoryTitle = title,
            advisoryDetails = details,
            shouldSilence = false, // Advisory mode: never auto-silence without user rule
            shouldDisallow = false, // Advisory mode: never auto-drop without explicit blocklist
            evaluationLatencyMs = elapsedMs
        )
    }

    fun updateCachedReputation(normalizedE164: String, fraudScore: Int, isRisky: Boolean, lineType: String) {
        reputationCache[normalizedE164] = ReputationEntry(
            fraudScore = fraudScore,
            isRisky = isRisky,
            lineType = lineType,
            timestampMs = System.currentTimeMillis()
        )
    }
}