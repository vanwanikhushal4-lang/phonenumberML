package com.aegis.guard.phonenumber

/**
 * Human-readable explainability reason codes for phone number pattern risk assessment.
 */
object ReasonCodes {
    const val WANGIRI_HIGH_COST_RANGE = "risk_wangiri_high_cost_prefix"
    const val TELEMARKETING_SERIES = "risk_telemarketing_series"
    const val LOW_ENTROPY_REPETITION = "digit_max_repeat_run"
    const val PREMIUM_RATE_SERVICE = "plan_is_premium_rate"
    const val LEGITIMATE_TOLLFREE_BANK = "hard_neg_legitimate_bank_support"
    const val EMERGENCY_SERVICE = "hard_neg_emergency_service"
    const val INVALID_NUMBER_SYNTAX = "num_is_valid_e164"
    const val STANDARD_ENTROPY_STRUCTURE = "standard_entropy_structure"

    val DESCRIPTIONS = mapOf(
        WANGIRI_HIGH_COST_RANGE to "High-risk international revenue-sharing callback trap (Wangiri scam)",
        TELEMARKETING_SERIES to "Matches registered commercial telemarketing / automated dialer series",
        LOW_ENTROPY_REPETITION to "Unnatural low-entropy repetitive or sequential digit pattern typical of automated robocallers",
        PREMIUM_RATE_SERVICE to "High-charge premium rate number service",
        LEGITIMATE_TOLLFREE_BANK to "Verified legitimate customer care / banking institution toll-free line",
        EMERGENCY_SERVICE to "Recognized national emergency or public service line",
        INVALID_NUMBER_SYNTAX to "Invalid number syntax violating standard international numbering plan",
        STANDARD_ENTROPY_STRUCTURE to "Standard number structure. Digits alone provide insufficient evidence."
    )
}