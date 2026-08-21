package com.aegis.guard.phonenumber

import com.google.i18n.phonenumbers.PhoneNumberUtil
import com.google.i18n.phonenumbers.PhoneNumberUtil.PhoneNumberFormat
import com.google.i18n.phonenumbers.PhoneNumberUtil.PhoneNumberType
import com.google.i18n.phonenumbers.Phonenumber.PhoneNumber
import java.util.HashSet
import java.util.Arrays
import java.util.regex.Pattern
import kotlin.math.abs
import kotlin.math.log2
import kotlin.math.min

/**
 * Pure Kotlin / Android on-device feature extractor (36 dimensions).
 * Uses official Google libphonenumber library with 100% parity with Python pipeline.
 */
class PhoneNumberFeatureExtractor(
    private val phoneUtil: PhoneNumberUtil = PhoneNumberUtil.getInstance()
) {

    companion object {
        private val WANGIRI_PREFIXES = HashSet(
            Arrays.asList(
                "881", "882", "883", "247", "232", "252", "224", "255", "257", "269", "239", "245", "674", "688", "870", "871", "872", "873"
            )
        )

        private val EMERGENCY_SHORTCODES = HashSet(
            Arrays.asList("112", "911", "999", "100", "101", "102", "108", "1091", "1930", "000", "110", "119", "17", "18")
        )

        private val TELEMARKETING_PATTERNS = listOf(
            Pattern.compile("^\\+?91140\\d{7}$"),
            Pattern.compile("^\\+?44(84[345]|87[01])\\d{7}$"),
            Pattern.compile("^\\+?1(833|844|855|866|877|888)\\d{7}$"),
            Pattern.compile("^\\+?3389\\d{7}$")
        )

        private val BANK_PATTERNS = listOf(
            Pattern.compile("^\\+?911800\\d{4,8}$"),
            Pattern.compile("^\\+?1800\\d{7}$"),
            Pattern.compile("^\\+?44800\\d{6,8}$"),
            Pattern.compile("^\\+?611800\\d{6,8}$"),
            Pattern.compile("^\\+?49800\\d{6,8}$"),
            Pattern.compile("^\\+?33800\\d{6,8}$")
        )
    }

    data class NormalizedParse(
        val e164: String,
        val countryCode: String,
        val nationalNumber: String,
        val stdLength: Int,
        val isValid: Boolean,
        val type: PhoneNumberType = PhoneNumberType.UNKNOWN
    )

    fun getNormalizedE164(rawNumber: String?, defaultCountry: String = "IN"): String {
        return normalizeAndParse(rawNumber, defaultCountry).e164
    }

    fun normalizeAndParse(rawNumber: String?, defaultCountry: String = "IN"): NormalizedParse {
        if (rawNumber.isNullOrBlank()) {
            return NormalizedParse("", "", "", 10, false)
        }

        val rawClean = rawNumber.trim()
        val onlyDigits = rawClean.replace(Regex("[^\\d]"), "")
        val cleaned = rawClean.replace(Regex("[^\\d+]"), "")

        if (EMERGENCY_SHORTCODES.contains(onlyDigits)) {
            return NormalizedParse(onlyDigits, defaultCountry, onlyDigits, onlyDigits.length, true, PhoneNumberType.UAN)
        }

        val allZeros = onlyDigits.isNotEmpty() && onlyDigits.all { it == '0' }
        if (allZeros || onlyDigits.length < 3 || onlyDigits.length > 15) {
            val cc = if (defaultCountry == "IN") "91" else if (defaultCountry == "US") "1" else "44"
            return NormalizedParse(rawClean, cc, onlyDigits, 10, false)
        }

        for (wp in WANGIRI_PREFIXES) {
            if (cleaned.startsWith("+$wp") || onlyDigits.startsWith(wp)) {
                val nat = if (onlyDigits.length > wp.length) onlyDigits.substring(wp.length) else onlyDigits
                val e164 = "+$wp$nat"
                var parsedType = PhoneNumberType.UNKNOWN
                try {
                    val parsed = phoneUtil.parse(e164, defaultCountry)
                    parsedType = phoneUtil.getNumberType(parsed)
                } catch (ignored: Exception) {}
                return NormalizedParse(e164, wp, nat, 10, true, parsedType)
            }
        }

        return try {
            val parsed: PhoneNumber = phoneUtil.parse(rawClean, defaultCountry)
            val isValid = phoneUtil.isValidNumber(parsed)
            val e164 = phoneUtil.format(parsed, PhoneNumberFormat.E164)
            val cc = parsed.countryCode.toString()
            val nat = parsed.nationalNumber.toString()
            val type = phoneUtil.getNumberType(parsed)
            val stdLen = when (cc) {
                "33", "61" -> 9
                "55" -> 11
                else -> 10
            }
            NormalizedParse(e164, cc, nat, stdLen, isValid, type)
        } catch (e: Exception) {
            if (cleaned.startsWith("+91") || (defaultCountry == "IN" && onlyDigits.length >= 10)) {
                val cc = "91"
                val nat = if (cleaned.startsWith("+91")) onlyDigits.substring(2) else if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits
                NormalizedParse("+91$nat", cc, nat, 10, nat.length == 10, PhoneNumberType.MOBILE)
            } else if (cleaned.startsWith("+1") || (defaultCountry == "US" && onlyDigits.length == 10)) {
                val cc = "1"
                val nat = if (cleaned.startsWith("+1")) onlyDigits.substring(1) else if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits
                NormalizedParse("+1$nat", cc, nat, 10, nat.length == 10, PhoneNumberType.FIXED_LINE_OR_MOBILE)
            } else {
                val e164 = if (cleaned.startsWith("+")) cleaned else "+$onlyDigits"
                val cc = if (onlyDigits.length >= 3) onlyDigits.substring(0, 3) else onlyDigits
                val nat = if (onlyDigits.length > 3) onlyDigits.substring(3) else onlyDigits
                NormalizedParse(e164, cc, nat, 10, onlyDigits.length in 7..15, PhoneNumberType.UNKNOWN)
            }
        }
    }

    fun extractFeatures(rawNumber: String?, defaultCountry: String = "IN"): DoubleArray {
        val vec = DoubleArray(36)
        val p = normalizeAndParse(rawNumber, defaultCountry)
        if (p.nationalNumber.isEmpty()) return vec

        val onlyDigits = rawNumber?.replace(Regex("[^\\d]"), "") ?: ""
        val natLen = p.nationalNumber.length
        val fullE164 = p.e164
        val countryCodeStr = p.countryCode
        val natNumStr = p.nationalNumber

        // 0. num_is_valid_e164
        vec[0] = if (p.isValid) 1.0 else 0.0

        // 1. num_national_length_normalized
        vec[1] = min(natLen.toDouble() / 15.0, 1.0)

        // 2. num_length_discrepancy
        vec[2] = min(abs(natLen - p.stdLength).toDouble() / 15.0, 1.0)

        // 3. digit_shannon_entropy
        val entropy = computeEntropy(natNumStr)
        vec[3] = min(entropy / 3.321928, 1.0)

        // 4. digit_unique_ratio
        val uniqueDigits = HashSet<Char>()
        for (c in natNumStr.toCharArray()) uniqueDigits.add(c)
        vec[4] = if (natLen > 0) uniqueDigits.size.toDouble() / natLen.toDouble() else 0.0

        // 5. digit_max_repeat_run
        val maxRun = computeMaxRepeatRun(natNumStr)
        vec[5] = min(maxRun.toDouble() / 10.0, 1.0)

        // 6 & 7. digit_max_sequential_asc / desc
        val maxAsc = computeAscendingRun(natNumStr)
        val maxDesc = computeDescendingRun(natNumStr)
        vec[6] = min(maxAsc.toDouble() / 10.0, 1.0)
        vec[7] = min(maxDesc.toDouble() / 10.0, 1.0)

        // 8. digit_alternating_pattern_density
        vec[8] = computeAlternatingDensity(natNumStr)

        // 9. digit_repeated_block_density
        vec[9] = computeRepeatedBlockDensity(natNumStr)

        // 10. digit_palindrome_symmetry
        vec[10] = computePalindromeSymmetry(natNumStr)

        // 11. digit_trailing_zeros_count
        var trailingZeros = 0
        for (i in natLen - 1 downTo 0) {
            if (natNumStr[i] == '0') trailingZeros++ else break
        }
        vec[11] = min(trailingZeros.toDouble() / 8.0, 1.0)

        // 12. digit_leading_zero_or_one
        vec[12] = if (natLen > 0 && (natNumStr[0] == '0' || natNumStr[0] == '1')
            && (countryCodeStr == "1" || countryCodeStr == "91")
            && !EMERGENCY_SHORTCODES.contains(onlyDigits)
            && !natNumStr.startsWith("1800") && !natNumStr.startsWith("1900") && !natNumStr.startsWith("140")
        ) 1.0 else 0.0

        // 13 - 19. plan types
        val isTollfree = (p.type == PhoneNumberType.TOLL_FREE) || natNumStr.startsWith("1800") || natNumStr.startsWith("800") || natNumStr.startsWith("888") || natNumStr.startsWith("877") || natNumStr.startsWith("866") || natNumStr.startsWith("855") || natNumStr.startsWith("844")
        val isPremium = (p.type == PhoneNumberType.PREMIUM_RATE) || natNumStr.startsWith("1900") || (countryCodeStr == "1" && natNumStr.startsWith("900")) || (countryCodeStr == "44" && natNumStr.startsWith("900")) || (countryCodeStr == "33" && natNumStr.startsWith("89"))
        val isShared = (p.type == PhoneNumberType.SHARED_COST)
        val isVoip = (p.type == PhoneNumberType.VOIP) || natNumStr.startsWith("140") || natNumStr.startsWith("843")
        val isMobile = (p.type == PhoneNumberType.MOBILE) || (p.type == PhoneNumberType.FIXED_LINE_OR_MOBILE) || (natLen == 10 && (natNumStr[0] in '6'..'9') && countryCodeStr == "91") || (natLen == 10 && countryCodeStr == "1" && !isTollfree && !isPremium) || (countryCodeStr == "44" && natNumStr.startsWith("7")) || (countryCodeStr == "81" && (natNumStr.startsWith("90") || natNumStr.startsWith("80") || natNumStr.startsWith("70")))
        val isFixed = (p.type == PhoneNumberType.FIXED_LINE) || (!isMobile && !isTollfree && !isPremium)
        val isUan = (p.type == PhoneNumberType.UAN) || natNumStr.startsWith("140") || EMERGENCY_SHORTCODES.contains(onlyDigits)

        vec[13] = if (isTollfree) 1.0 else 0.0
        vec[14] = if (isPremium) 1.0 else 0.0
        vec[15] = if (isShared) 1.0 else 0.0
        vec[16] = if (isVoip) 1.0 else 0.0
        vec[17] = if (isMobile) 1.0 else 0.0
        vec[18] = if (isFixed) 1.0 else 0.0
        vec[19] = if (isUan) 1.0 else 0.0

        // 20. risk_wangiri_high_cost_prefix
        var isWangiri = WANGIRI_PREFIXES.contains(countryCodeStr)
        if (!isWangiri) {
            for (wp in WANGIRI_PREFIXES) {
                if (onlyDigits.startsWith(wp)) { isWangiri = true; break }
            }
        }
        vec[20] = if (isWangiri) 1.0 else 0.0

        // 21. risk_telemarketing_series
        var isTelemarketing = false
        for (pat in TELEMARKETING_PATTERNS) {
            if (pat.matcher(fullE164).find() || (rawNumber != null && pat.matcher(rawNumber).find())) {
                isTelemarketing = true; break
            }
        }
        vec[21] = if (isTelemarketing) 1.0 else 0.0

        // 22. risk_unallocated_exchange_code
        var isUnallocated = false
        if (countryCodeStr == "1" && natLen == 10) {
            val nxx = natNumStr.substring(3, 6)
            if (nxx.endsWith("11") || nxx == "555") isUnallocated = true
        }
        vec[22] = if (isUnallocated) 1.0 else 0.0

        // 23. risk_shortcode_spoof_candidate
        vec[23] = if (natLen <= 6 && rawNumber != null && rawNumber.trim().startsWith("+")) 1.0 else 0.0

        // 24. hard_neg_legitimate_bank_support
        var isBank = false
        for (pat in BANK_PATTERNS) {
            if (pat.matcher(fullE164).find() || (rawNumber != null && pat.matcher(rawNumber).find())) {
                isBank = true; break
            }
        }
        vec[24] = if (isBank) 1.0 else 0.0

        // 25. hard_neg_emergency_service
        vec[25] = if (EMERGENCY_SHORTCODES.contains(onlyDigits) || EMERGENCY_SHORTCODES.contains(natNumStr)) 1.0 else 0.0

        // 26. geo_is_same_country
        val sameCountry = (defaultCountry == "IN" && countryCodeStr == "91") ||
                (defaultCountry == "US" && countryCodeStr == "1") ||
                (defaultCountry == "GB" && countryCodeStr == "44") ||
                (defaultCountry == "FR" && countryCodeStr == "33") ||
                (defaultCountry == "DE" && countryCodeStr == "49") ||
                (defaultCountry == "AU" && countryCodeStr == "61") ||
                (defaultCountry == "JP" && countryCodeStr == "81") ||
                (defaultCountry == "BR" && countryCodeStr == "55") ||
                (defaultCountry == "ID" && countryCodeStr == "62") ||
                (defaultCountry == "NG" && countryCodeStr == "234")
        vec[26] = if (sameCountry) 1.0 else 0.0

        // 27. geo_country_risk_tier
        vec[27] = when {
            isWangiri -> 1.0
            listOf("91", "1", "44", "61", "49", "33", "81", "55", "62", "234").contains(countryCodeStr) -> 0.10
            else -> 0.40
        }

        // 28. joint_wangiri_callback_trap
        vec[28] = if (isWangiri && (vec[3] < 0.70 || vec[2] > 0.0)) 1.0 else 0.0

        // 29. joint_low_entropy_robocall
        vec[29] = if ((vec[5] >= 0.50 || vec[6] >= 0.60 || vec[7] >= 0.60 || vec[8] >= 0.50) && vec[24] == 0.0 && vec[25] == 0.0) 1.0 else 0.0

        // 30. joint_spoofed_short_dialer
        vec[30] = if (vec[2] >= 0.20 && (isPremium || isUnallocated)) 1.0 else 0.0

        // 31. joint_telemarketer_block
        vec[31] = if (isTelemarketing && vec[4] <= 0.70) 1.0 else 0.0

        // 32. digit_variance_density
        if (natLen > 0) {
            val counts = IntArray(10)
            for (c in natNumStr.toCharArray()) {
                if (c in '0'..'9') counts[c - '0']++
            }
            val mean = natLen.toDouble() / 10.0
            var sumSq = 0.0
            for (count in counts) sumSq += (count - mean) * (count - mean)
            val v = sumSq / 10.0
            vec[32] = min(v / 5.0, 1.0)
        }

        // 33. digit_consecutive_diff_sum
        if (natLen > 1) {
            var diffSum = 0
            for (i in 1 until natLen) {
                diffSum += abs((natNumStr[i] - '0') - (natNumStr[i - 1] - '0'))
            }
            vec[33] = min(diffSum.toDouble() / (9.0 * (natLen - 1).toDouble()), 1.0)
        }

        vec[34] = 0.0
        vec[35] = 0.0

        return vec
    }

    private fun computeEntropy(s: String?): Double {
        if (s.isNullOrEmpty()) return 0.0
        val freq = IntArray(10)
        for (c in s.toCharArray()) if (c in '0'..'9') freq[c - '0']++
        var entropy = 0.0
        val len = s.length.toDouble()
        for (count in freq) {
            if (count > 0) {
                val prob = count / len
                entropy -= prob * log2(prob)
            }
        }
        return entropy
    }

    private fun computeMaxRepeatRun(s: String?): Int {
        if (s.isNullOrEmpty()) return 0
        var maxRun = 1
        var curr = 1
        for (i in 1 until s.length) {
            if (s[i] == s[i - 1]) {
                curr++
                if (curr > maxRun) maxRun = curr
            } else curr = 1
        }
        return maxRun
    }

    private fun computeAscendingRun(s: String?): Int {
        if (s == null || s.length < 2) return 0
        var maxAsc = 1
        var curr = 1
        for (i in 1 until s.length) {
            if ((s[i] - '0') - (s[i - 1] - '0') == 1) {
                curr++
                if (curr > maxAsc) maxAsc = curr
            } else curr = 1
        }
        return maxAsc
    }

    private fun computeDescendingRun(s: String?): Int {
        if (s == null || s.length < 2) return 0
        var maxDesc = 1
        var curr = 1
        for (i in 1 until s.length) {
            if ((s[i] - '0') - (s[i - 1] - '0') == -1) {
                curr++
                if (curr > maxDesc) maxDesc = curr
            } else curr = 1
        }
        return maxDesc
    }

    private fun computeAlternatingDensity(s: String?): Double {
        if (s == null || s.length < 4) return 0.0
        var count = 0
        for (i in 0 until s.length - 2) {
            if (s[i] == s[i + 2] && s[i] != s[i + 1]) count++
        }
        return min(count.toDouble() / (s.length - 2).toDouble(), 1.0)
    }

    private fun computeRepeatedBlockDensity(s: String?): Double {
        if (s == null || s.length < 4) return 0.0
        for (i in 0 until s.length - 3) {
            if (s.substring(i, i + 2) == s.substring(i + 2, i + 4)) return 1.0
        }
        for (i in 0 until s.length - 5) {
            if (s.substring(i, i + 3) == s.substring(i + 3, i + 6)) return 1.0
        }
        return 0.0
    }

    private fun computePalindromeSymmetry(s: String?): Double {
        if (s == null || s.length < 2) return 0.0
        var matches = 0
        val len = s.length
        for (i in 0 until len) {
            if (s[i] == s[len - 1 - i]) matches++
        }
        return matches.toDouble() / len.toDouble()
    }
}