package com.aegis.guard.phonenumber

/**
 * Human-readable explainability reason codes for phone number pattern risk assessment.
 */
object ReasonCodes {
    const val WANGIRI_HIGH_COST_RANGE = "REASON_WANGIRI_HIGH_COST_RANGE"
    const val TELEMARKETING_SERIES = "REASON_TELEMARKETING_SERIES"
    const val LOW_ENTROPY_REPETITION = "REASON_LOW_ENTROPY_REPETITION"
    const val VOIP_VIRTUAL_RANGE = "REASON_VOIP_VIRTUAL_RANGE"
    const val INVALID_LENGTH_PADDING = "REASON_INVALID_LENGTH_PADDING"
    const val PREMIUM_RATE_SERVICE = "REASON_PREMIUM_RATE_SERVICE"
    const val LEGITIMATE_TOLLFREE_BANK = "REASON_LEGITIMATE_TOLLFREE_BANK"
    const val EMERGENCY_SERVICE = "REASON_EMERGENCY_SERVICE"
    const val INSUFFICIENT_STRUCTURAL_EVIDENCE = "REASON_INSUFFICIENT_STRUCTURAL_EVIDENCE"

    val DESCRIPTIONS = mapOf(
        WANGIRI_HIGH_COST_RANGE to "High-risk international premium-rate callback trap (Wangiri scam)",
        TELEMARKETING_SERIES to "Matches registered commercial telemarketing / automated dialer series",
        LOW_ENTROPY_REPETITION to "Unnatural repetitive or sequential digit pattern typical of automated robocallers",
        VOIP_VIRTUAL_RANGE to "Virtual cloud VoIP / unassigned exchange range prone to spoofing",
        INVALID_LENGTH_PADDING to "Number length violates standard international numbering plan constraints",
        PREMIUM_RATE_SERVICE to "High-charge premium rate number service",
        LEGITIMATE_TOLLFREE_BANK to "Verified legitimate customer care / banking institution toll-free line",
        EMERGENCY_SERVICE to "Recognized national emergency or public service line",
        INSUFFICIENT_STRUCTURAL_EVIDENCE to "Standard number structure. Digits alone provide insufficient evidence."
    )
}