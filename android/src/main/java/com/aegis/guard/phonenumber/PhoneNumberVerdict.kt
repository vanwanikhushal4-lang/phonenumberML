package com.aegis.guard.phonenumber

enum class ThreatTier {
    LEGITIMATE,
    UNKNOWN,
    SPAM,
    SCAM,
    INVALID
}

enum class ConfidenceLevel {
    LOW,
    MEDIUM,
    HIGH
}

data class PhoneNumberVerdict(
    val rawNumber: String,
    val normalizedE164: String,
    val country: String,
    val riskScore: Int,
    val rawLogit: Float,
    val calibratedProbability: Float,
    val tier: ThreatTier,
    val confidence: ConfidenceLevel,
    val isThreat: Boolean,
    val isAbstain: Boolean,
    val isInvalid: Boolean,
    val topReasonCodes: List<String>,
    val topExplanations: List<String>
)