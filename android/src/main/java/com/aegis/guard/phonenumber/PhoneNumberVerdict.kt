package com.aegis.guard.phonenumber

enum class ThreatTier {
    LEGITIMATE,
    UNKNOWN,
    SPAM,
    SCAM
}

enum class ConfidenceLevel {
    LOW,
    MEDIUM,
    HIGH
}

data class PhoneNumberVerdict(
    val rawNumber: String,
    val country: String,
    val riskScore: Int,
    val probability: Float,
    val tier: ThreatTier,
    val confidence: ConfidenceLevel,
    val isThreat: Boolean,
    val isAbstain: Boolean,
    val topReasonCodes: List<String>,
    val topExplanations: List<String>
)