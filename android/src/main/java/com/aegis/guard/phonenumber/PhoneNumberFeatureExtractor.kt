package com.aegis.guard.phonenumber

import java.util.HashSet
import java.util.Arrays
import kotlin.math.abs
import kotlin.math.log2
import kotlin.math.min

/**
 * Pure Kotlin / Android on-device feature extractor (36 dimensions).
 * 100% Deterministic Parity with Python AEGIS-PNP1 Feature Extractor.
 */
object PhoneNumberFeatureExtractor {

    private val WANGIRI_PREFIXES = HashSet(
        Arrays.asList(
            "881", "882", "883", "247", "232", "252", "224", "255", "257", "269", "239", "245", "674", "688", "870", "871", "872", "873"
        )
    )

    private val EMERGENCY_SHORTCODES = HashSet(
        Arrays.asList("112", "911", "999", "100", "101", "102", "108", "1091", "1930", "000")
    )

    private val TELEMARKETING_REGEXES = listOf(
        Regex("^\\+?91140\\d{7}$"),
        Regex("^\\+?4484[345]\\d{7}$"),
        Regex("^\\+?1(844|855|866|877|888)\\d{7}$"),
        Regex("^\\+?3389\\d{7}$")
    )

    private val BANK_REGEXES = listOf(
        Regex("^\\+?911800(112211|4253800|2026161|1080|229090|1802222|2098800|1234|2100).*"),
        Regex("^\\+?1800(9359935|4321000|8693557|2882020|8291040).*"),
        Regex("^\\+?911800\\d{4,7}$")
    )

    fun extractFeatures(rawNumber: String?, defaultCountry: String = "IN"): FloatArray {
        val vec = FloatArray(36)
        if (rawNumber.isNullOrBlank()) return vec

        val cleaned = rawNumber.trim().replace(Regex("[^\\d+]"), "")
        val onlyDigits = rawNumber.trim().replace(Regex("[^\\d]"), "")
        if (onlyDigits.isEmpty()) return vec

        var countryCodeStr = ""
        var natNumStr = onlyDigits
        var stdLength = 10
        var isValid = false

        if (EMERGENCY_SHORTCODES.contains(onlyDigits)) {
            countryCodeStr = defaultCountry
            natNumStr = onlyDigits
            stdLength = onlyDigits.length
            isValid = true
        } else {
            var isWangiriPrefix = false
            for (wp in WANGIRI_PREFIXES) {
                if (cleaned.startsWith("+$wp") || onlyDigits.startsWith(wp)) {
                    countryCodeStr = wp
                    natNumStr = if (onlyDigits.length > wp.length) onlyDigits.substring(wp.length) else onlyDigits
                    stdLength = 10
                    isValid = true
                    isWangiriPrefix = true
                    break
                }
            }

            if (!isWangiriPrefix) {
                if (cleaned.startsWith("+91") || (defaultCountry == "IN" && onlyDigits.length >= 10)) {
                    countryCodeStr = "91"
                    natNumStr = if (cleaned.startsWith("+91") || (onlyDigits.startsWith("91") && onlyDigits.length == 12)) onlyDigits.substring(2) else (if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits)
                    stdLength = 10
                    isValid = true
                } else if (cleaned.startsWith("+1") || (defaultCountry == "US" && onlyDigits.length == 10)) {
                    countryCodeStr = "1"
                    natNumStr = if (cleaned.startsWith("+1") || (onlyDigits.startsWith("1") && onlyDigits.length == 11)) onlyDigits.substring(1) else (if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits)
                    stdLength = 10
                    isValid = true
                } else if (cleaned.startsWith("+44") || defaultCountry == "GB") {
                    countryCodeStr = "44"
                    natNumStr = if (cleaned.startsWith("+44") || (onlyDigits.startsWith("44") && onlyDigits.length == 12)) onlyDigits.substring(2) else (if (onlyDigits.length >= 10) onlyDigits.substring(onlyDigits.length - 10) else onlyDigits)
                    stdLength = 10
                    isValid = true
                } else {
                    countryCodeStr = if (onlyDigits.length >= 3) onlyDigits.substring(0, 3) else onlyDigits
                    natNumStr = if (onlyDigits.length > 3) onlyDigits.substring(3) else onlyDigits
                    stdLength = 10
                    isValid = (onlyDigits.length in 7..15)
                }
            }
        }

        val natLen = natNumStr.length
        val fullE164 = "+$countryCodeStr$natNumStr"

        // 0. Validity
        vec[0] = if (isValid) 1.0f else 0.0f

        // 1. National length normalized
        vec[1] = min(natLen.toFloat() / 15.0f, 1.0f)

        // 2. Length discrepancy
        vec[2] = min(abs(natLen - stdLength).toFloat() / 15.0f, 1.0f)

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
        if (natLen > 0 && (natNumStr[0] == '0' || natNumStr[0] == '1') && (countryCodeStr == "1" || countryCodeStr == "91") && !EMERGENCY_SHORTCODES.contains(onlyDigits)) {
            vec[12] = 1.0f
        } else {
            vec[12] = 0.0f
        }

        // 13 - 19. Number Types
        val isTollfree = natNumStr.startsWith("1800") || natNumStr.startsWith("800") || natNumStr.startsWith("888") || natNumStr.startsWith("877") || natNumStr.startsWith("866") || natNumStr.startsWith("855") || natNumStr.startsWith("844")
        val isPremium = natNumStr.startsWith("1900") || natNumStr.startsWith("900") || natNumStr.startsWith("0900")
        val isVoip = natNumStr.startsWith("140") || natNumStr.startsWith("843")
        val isMobile = (natLen == 10 && (natNumStr[0] in listOf('6', '7', '8', '9')) && countryCodeStr == "91") || (natLen == 10 && countryCodeStr == "1")
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
        val isTelemarketing = TELEMARKETING_REGEXES.any { it.containsMatchIn(fullE164) || it.containsMatchIn(cleaned) }
        vec[21] = if (isTelemarketing) 1.0f else 0.0f

        // 22. Unallocated exchange code
        var isUnallocated = false
        if (countryCodeStr == "1" && natLen == 10) {
            val nxx = natNumStr.substring(3, 6)
            if (nxx.endsWith("11") || nxx == "555") isUnallocated = true
        }
        vec[22] = if (isUnallocated) 1.0f else 0.0f

        // 23. Shortcode spoof
        vec[23] = if (natLen <= 6 && cleaned.startsWith("+")) 1.0f else 0.0f

        // 24. Hard Negative Bank
        val isBank = BANK_REGEXES.any { it.containsMatchIn(fullE164) || it.containsMatchIn(cleaned) }
        vec[24] = if (isBank) 1.0f else 0.0f

        // 25. Hard Negative Emergency
        vec[25] = if (EMERGENCY_SHORTCODES.contains(onlyDigits) || EMERGENCY_SHORTCODES.contains(natNumStr)) 1.0f else 0.0f

        // 26. Same country
        val sameCountry = (defaultCountry == "IN" && countryCodeStr == "91") ||
                (defaultCountry == "US" && countryCodeStr == "1") ||
                (defaultCountry == "GB" && countryCodeStr == "44")
        vec[26] = if (sameCountry) 1.0f else 0.0f

        // 27. Country risk tier
        if (isWangiri) vec[27] = 1.0f
        else if (countryCodeStr in listOf("91", "1", "44", "61", "49")) vec[27] = 0.10f
        else vec[27] = 0.40f

        // 28. Joint: Wangiri Trap
        vec[28] = if (isWangiri && (vec[3] < 0.70f || vec[2] > 0.0f)) 1.0f else 0.0f

        // 29. Joint: VoIP Robocall
        vec[29] = if (isVoip && (vec[5] >= 0.30f || vec[8] >= 0.30f || vec[6] >= 0.30f)) 1.0f else 0.0f

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