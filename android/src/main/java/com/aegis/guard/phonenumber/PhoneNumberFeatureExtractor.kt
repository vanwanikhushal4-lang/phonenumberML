package com.aegis.guard.phonenumber

import java.util.HashSet
import java.util.Arrays
import kotlin.math.abs
import kotlin.math.log2
import kotlin.math.min

/**
 * Pure Kotlin / Android on-device feature extractor (36 dimensions).
 * 100% End-to-End Deterministic Parity with Python AEGIS-PNP2 Feature Extractor.
 */
class PhoneNumberFeatureExtractor {

    companion object {
        private val WANGIRI_PREFIXES = HashSet(
            Arrays.asList(
                "881", "882", "883", "247", "232", "252", "224", "255", "257", "269", "239", "245", "674", "688", "870", "871", "872", "873"
            )
        )

        private val EMERGENCY_SHORTCODES = HashSet(
            Arrays.asList("112", "911", "999", "100", "101", "102", "108", "1091", "1930", "000", "110", "119", "17", "18")
        )

        private val TELEMARKETING_REGEXES = listOf(
            Regex("^\\+?91140\\d{7}$"),
            Regex("^\\+?4484[345]\\d{7}$"),
            Regex("^\\+?1(844|855|866)\\d{7}$"),
            Regex("^\\+?3389\\d{7}$")
        )

        private val BANK_REGEXES = listOf(
            Regex("^\\+?911800\\d{4,8}$"),
            Regex("^\\+?1800\\d{7}$"),
            Regex("^\\+?44800\\d{6,8}$"),
            Regex("^\\+?611800\\d{6,8}$"),
            Regex("^\\+?49800\\d{6,8}$"),
            Regex("^\\+?33800\\d{6,8}$")
        )
    }

    data class NormalizedParse(
        val e164: String,
        val countryCode: String,
        val nationalNumber: String,
        val stdLength: Int,
        val isValid: Boolean
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
            return NormalizedParse(onlyDigits, defaultCountry, onlyDigits, onlyDigits.length, true)
        }

        val allZeros = onlyDigits.isNotEmpty() && onlyDigits.all { it == '0' }
        if (allZeros || onlyDigits.length < 3 || onlyDigits.length > 15) {
            val cc = if (defaultCountry == "IN") "91" else if (defaultCountry == "US") "1" else "44"
            return NormalizedParse(rawClean, cc, onlyDigits, 10, false)
        }

        for (wp in WANGIRI_PREFIXES) {
            if (cleaned.startsWith("+$wp") || onlyDigits.startsWith(wp)) {
                val nat = if (onlyDigits.length > wp.length) onlyDigits.substring(wp.length) else onlyDigits
                return NormalizedParse("+$wp$nat", wp, nat, 10, true)
            }
        }

        if (cleaned.startsWith("+91") || (defaultCountry == "IN" && onlyDigits.length >= 10)) {
            val cc = "91"
            val nat = if (cleaned.startsWith("+91") || (onlyDigits.startsWith("91") && onlyDigits.length >= 12)) onlyDigits.substring(2) else if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits
            val isV = nat.length in 10..11 && !nat.all { it == '0' }
            return NormalizedParse("+91$nat", cc, nat, 10, isV)
        } else if (cleaned.startsWith("+1") || (defaultCountry == "US" && onlyDigits.length == 10)) {
            val cc = "1"
            val nat = if (cleaned.startsWith("+1") || (onlyDigits.startsWith("1") && onlyDigits.length == 11)) onlyDigits.substring(1) else if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits
            return NormalizedParse("+1$nat", cc, nat, 10, nat.length == 10)
        } else if (cleaned.startsWith("+44") || defaultCountry == "GB") {
            val cc = "44"
            val nat = if (cleaned.startsWith("+44") || (onlyDigits.startsWith("44") && onlyDigits.length >= 11)) onlyDigits.substring(2) else if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits
            return NormalizedParse("+44$nat", cc, nat, 10, nat.length in 9..11)
        } else if (cleaned.startsWith("+33") || defaultCountry == "FR") {
            val cc = "33"
            val nat = if (cleaned.startsWith("+33") || (onlyDigits.startsWith("33") && onlyDigits.length >= 10)) onlyDigits.substring(2) else if (onlyDigits.length >= 9) onlyDigits.substring(onlyDigits.length - 9) else onlyDigits
            return NormalizedParse("+33$nat", cc, nat, 9, nat.length == 9)
        } else if (cleaned.startsWith("+49") || defaultCountry == "DE") {
            val cc = "49"
            val nat = if (cleaned.startsWith("+49") || (onlyDigits.startsWith("49") && onlyDigits.length >= 11)) onlyDigits.substring(2) else if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits
            return NormalizedParse("+49$nat", cc, nat, 10, true)
        } else if (cleaned.startsWith("+61") || defaultCountry == "AU") {
            val cc = "61"
            val nat = if (cleaned.startsWith("+61") || (onlyDigits.startsWith("61") && onlyDigits.length >= 10)) onlyDigits.substring(2) else if (onlyDigits.length >= 9) onlyDigits.substring(onlyDigits.length - 9) else onlyDigits
            return NormalizedParse("+61$nat", cc, nat, 9, true)
        } else if (cleaned.startsWith("+81") || defaultCountry == "JP") {
            val cc = "81"
            val nat = if (cleaned.startsWith("+81") || (onlyDigits.startsWith("81") && onlyDigits.length >= 11)) onlyDigits.substring(2) else if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits
            return NormalizedParse("+81$nat", cc, nat, 10, true)
        } else {
            val cc = if (onlyDigits.length >= 3) onlyDigits.substring(0, 3) else onlyDigits
            val nat = if (onlyDigits.length > 3) onlyDigits.substring(3) else onlyDigits
            return NormalizedParse("+$cc$nat", cc, nat, 10, onlyDigits.length in 7..15)
        }
    }

    fun extractFeatures(rawNumber: String?, defaultCountry: String = "IN"): FloatArray {
        val vec = FloatArray(36)
        val parse = normalizeAndParse(rawNumber, defaultCountry)
        if (parse.nationalNumber.isEmpty()) return vec

        val onlyDigits = rawNumber?.trim()?.replace(Regex("[^\\d]"), "") ?: ""
        val natLen = parse.nationalNumber.length
        val fullE164 = parse.e164
        val countryCodeStr = parse.countryCode
        val natNumStr = parse.nationalNumber

        // 0. Validity
        vec[0] = if (parse.isValid) 1.0f else 0.0f

        // 1. National length normalized
        vec[1] = min(natLen.toFloat() / 15.0f, 1.0f)

        // 2. Length discrepancy
        vec[2] = min(abs(natLen - parse.stdLength).toFloat() / 15.0f, 1.0f)

        // 3. Shannon Entropy
        val entropy = computeEntropy(natNumStr)
        vec[3] = min(entropy / 3.321928f, 1.0f)

        // 4. Unique ratio
        val uniqueDigits = HashSet<Char>()
        for (c in natNumStr.toCharArray()) uniqueDigits.add(c)
        vec[4] = if (natLen > 0) (uniqueDigits.size.toFloat() / natLen.toFloat()) else 0.0f

        // 5. Max repeat run
        val maxRun = computeMaxRepeatRun(natNumStr)
        vec[5] = min(maxRun.toFloat() / 10.0f, 1.0f)

        // 6 & 7. Sequential asc / desc
        val maxAsc = computeAscendingRun(natNumStr)
        val maxDesc = computeDescendingRun(natNumStr)
        vec[6] = min(maxAsc.toFloat() / 10.0f, 1.0f)
        vec[7] = min(maxDesc.toFloat() / 10.0f, 1.0f)

        // 8. Alternating density
        vec[8] = computeAlternatingDensity(natNumStr)

        // 9. Repeated block density
        vec[9] = computeRepeatedBlockDensity(natNumStr)

        // 10. Palindrome symmetry
        vec[10] = computePalindromeSymmetry(natNumStr)

        // 11. Trailing zeros
        var trailingZeros = 0
        for (i in natLen - 1 downTo 0) {
            if (natNumStr[i] == '0') trailingZeros++ else break
        }
        vec[11] = min(trailingZeros.toFloat() / 8.0f, 1.0f)

        // 12. Leading digit distribution anomaly
        if (natLen > 0 && (natNumStr[0] == '0' || natNumStr[0] == '1') && (countryCodeStr == "1" || countryCodeStr == "91") && !EMERGENCY_SHORTCODES.contains(onlyDigits) && !natNumStr.startsWith("1800") && !natNumStr.startsWith("1900") && !natNumStr.startsWith("140")) {
            vec[12] = 1.0f
        } else {
            vec[12] = 0.0f
        }

        // 13 - 19. Number Types
        val isTollfree = natNumStr.startsWith("1800") || natNumStr.startsWith("800") || natNumStr.startsWith("888") || natNumStr.startsWith("877") || natNumStr.startsWith("866") || natNumStr.startsWith("855") || natNumStr.startsWith("844")
        val isPremium = (natNumStr.startsWith("1900") || (countryCodeStr == "1" && natNumStr.startsWith("900")) || (countryCodeStr == "44" && natNumStr.startsWith("900")) || (countryCodeStr == "33" && natNumStr.startsWith("89")))
        val isVoip = natNumStr.startsWith("140") || natNumStr.startsWith("843")
        val isMobile = (natLen == 10 && (natNumStr[0] in listOf('6', '7', '8', '9')) && countryCodeStr == "91") || (natLen == 10 && countryCodeStr == "1" && !isTollfree && !isPremium) || (countryCodeStr == "44" && natNumStr.startsWith("7")) || (countryCodeStr == "81" && (natNumStr.startsWith("90") || natNumStr.startsWith("80") || natNumStr.startsWith("70")))
        val isFixed = !isMobile && !isTollfree && !isPremium
        val isUan = natNumStr.startsWith("140") || EMERGENCY_SHORTCODES.contains(onlyDigits)

        vec[13] = if (isTollfree) 1.0f else 0.0f
        vec[14] = if (isPremium) 1.0f else 0.0f
        vec[15] = 0.0f
        vec[16] = if (isVoip) 1.0f else 0.0f
        vec[17] = if (isMobile) 1.0f else 0.0f
        vec[18] = if (isFixed) 1.0f else 0.0f
        vec[19] = if (isUan) 1.0f else 0.0f

        // 20. Wangiri High Cost Prefix
        var isWangiri = WANGIRI_PREFIXES.contains(countryCodeStr)
        if (!isWangiri) {
            for (wp in WANGIRI_PREFIXES) {
                if (onlyDigits.startsWith(wp)) { isWangiri = true; break }
            }
        }
        vec[20] = if (isWangiri) 1.0f else 0.0f

        // 21. Telemarketing series
        val isTelemarketing = TELEMARKETING_REGEXES.any { it.containsMatchIn(fullE164) || it.containsMatchIn(rawNumber ?: "") }
        vec[21] = if (isTelemarketing) 1.0f else 0.0f

        // 22. Unallocated exchange code
        var isUnallocated = false
        if (countryCodeStr == "1" && natLen == 10) {
            val nxx = natNumStr.substring(3, 6)
            if (nxx.endsWith("11") || nxx == "555") isUnallocated = true
        }
        vec[22] = if (isUnallocated) 1.0f else 0.0f

        // 23. Shortcode spoof
        vec[23] = if (natLen <= 6 && (rawNumber?.trim()?.startsWith("+") == true)) 1.0f else 0.0f

        // 24. Hard Negative Bank
        var isBank = isTollfree
        if (!isBank) {
            isBank = BANK_REGEXES.any { it.containsMatchIn(fullE164) || it.containsMatchIn(rawNumber ?: "") }
        }
        vec[24] = if (isBank) 1.0f else 0.0f

        // 25. Hard Negative Emergency
        vec[25] = if (EMERGENCY_SHORTCODES.contains(onlyDigits) || EMERGENCY_SHORTCODES.contains(natNumStr)) 1.0f else 0.0f

        // 26. Same country
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
        vec[26] = if (sameCountry) 1.0f else 0.0f

        // 27. Country risk tier
        if (isWangiri) vec[27] = 1.0f
        else if (countryCodeStr in listOf("91", "1", "44", "61", "49", "33", "81", "55", "62", "234")) vec[27] = 0.10f
        else vec[27] = 0.40f

        // 28. Joint: Wangiri Trap
        vec[28] = if (isWangiri && (vec[3] < 0.70f || vec[2] > 0.0f)) 1.0f else 0.0f

        // 29. Joint: Low-Entropy Robocall
        vec[29] = if ((vec[5] >= 0.50f || vec[6] >= 0.60f || vec[7] >= 0.60f || vec[8] >= 0.50f) && vec[24] == 0.0f && vec[25] == 0.0f) 1.0f else 0.0f

        // 30. Joint: Spoofed Short Dialer
        vec[30] = if (vec[2] >= 0.20f && (isPremium || isUnallocated)) 1.0f else 0.0f

        // 31. Joint: Telemarketer Block
        vec[31] = if (isTelemarketing && vec[4] <= 0.70f) 1.0f else 0.0f

        // 32. Digit variance density
        if (natLen > 0) {
            val counts = IntArray(10)
            for (c in natNumStr.toCharArray()) {
                if (c in '0'..'9') counts[c - '0']++
            }
            val mean = natLen.toFloat() / 10.0f
            var sumSq = 0.0f
            for (count in counts) sumSq += (count - mean) * (count - mean)
            val v = sumSq / 10.0f
            vec[32] = min(v / 5.0f, 1.0f)
        }

        // 33. Consecutive diff sum
        if (natLen > 1) {
            var diffSum = 0
            for (i in 1 until natLen) {
                diffSum += abs((natNumStr[i] - '0') - (natNumStr[i - 1] - '0'))
            }
            vec[33] = min(diffSum.toFloat() / (9.0f * (natLen - 1).toFloat()), 1.0f)
        }

        vec[34] = 0.0f
        vec[35] = 0.0f

        return vec
    }

    fun explainFeatures(features: FloatArray): List<Pair<String, String>> {
        val list = ArrayList<Pair<String, String>>()
        if (features[20] > 0.5f) list.add(Pair(ReasonCodes.WANGIRI_HIGH_COST_DESTINATION, "International high-cost callback fraud prefix detected"))
        if (features[14] > 0.5f) list.add(Pair(ReasonCodes.PREMIUM_RATE_SERVICE, "High-charge premium rate destination range"))
        if (features[21] > 0.5f) list.add(Pair(ReasonCodes.REGISTERED_TELEMARKETER_SERIES, "Commercial telemarketing allocation range"))
        if (features[29] > 0.5f) list.add(Pair(ReasonCodes.LOW_ENTROPY_REPEATED_DIGITS, "Automated predictive dialer repetitive pattern"))
        if (features[24] > 0.5f) list.add(Pair(ReasonCodes.LEGITIMATE_BANK_CUSTOMER_CARE, "Verified public customer care line"))
        if (features[25] > 0.5f) list.add(Pair(ReasonCodes.EMERGENCY_HELPLINE, "Recognized national emergency helpline"))
        return list
    }

    private fun computeEntropy(s: String): Float {
        if (s.isEmpty()) return 0.0f
        val freq = IntArray(10)
        for (c in s.toCharArray()) if (c in '0'..'9') freq[c - '0']++
        var entropy = 0.0
        val len = s.length.toDouble()
        for (count in freq) {
            if (count > 0) {
                val p = count.toDouble() / len
                entropy -= p * log2(p)
            }
        }
        return entropy.toFloat()
    }

    private fun computeMaxRepeatRun(s: String): Int {
        if (s.isEmpty()) return 0
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

    private fun computeAscendingRun(s: String): Int {
        if (s.length < 2) return 0
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

    private fun computeDescendingRun(s: String): Int {
        if (s.length < 2) return 0
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

    private fun computeAlternatingDensity(s: String): Float {
        if (s.length < 4) return 0.0f
        var count = 0
        for (i in 0 until s.length - 2) {
            if (s[i] == s[i + 2] && s[i] != s[i + 1]) count++
        }
        return min(count.toFloat() / (s.length - 2).toFloat(), 1.0f)
    }

    private fun computeRepeatedBlockDensity(s: String): Float {
        if (s.length < 4) return 0.0f
        for (i in 0 until s.length - 3) {
            if (s.substring(i, i + 2) == s.substring(i + 2, i + 4)) return 1.0f
        }
        for (i in 0 until s.length - 5) {
            if (s.substring(i, i + 3) == s.substring(i + 3, i + 6)) return 1.0f
        }
        return 0.0f
    }

    private fun computePalindromeSymmetry(s: String): Float {
        if (s.length < 2) return 0.0f
        var matches = 0
        val len = s.length
        for (i in 0 until len) {
            if (s[i] == s[len - 1 - i]) matches++
        }
        return matches.toFloat() / len.toFloat()
    }
}