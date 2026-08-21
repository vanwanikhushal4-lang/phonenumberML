import java.io.*;
import java.util.*;

public class JvmPhoneNumberExtractor {

    private static final Set<String> WANGIRI_PREFIXES = new HashSet<>(Arrays.asList(
        "881", "882", "883", "247", "870", "871", "872", "873", "239", "245", "674", "688"
    ));

    private static final Set<String> EMERGENCY_SHORTCODES = new HashSet<>(Arrays.asList(
        "112", "911", "999", "100", "101", "102", "108", "1091", "1930", "000", "110", "119", "17", "18"
    ));

    private static final List<String> TELEMARKETING_PREFIXES = Arrays.asList(
        "^\\+?91140\\d{7}$",
        "^\\+?4484[345]\\d{7}$",
        "^\\+?3389\\d{7}$"
    );

    private static final List<String> LEGITIMATE_BANK_PATTERNS = Arrays.asList(
        "^\\+?911800\\d{4,8}$",
        "^\\+?1800\\d{7}$",
        "^\\+?44800\\d{6,8}$",
        "^\\+?611800\\d{6,8}$",
        "^\\+?49800\\d{6,8}$",
        "^\\+?33800\\d{6,8}$"
    );

    public static float[] extractFeatures(String rawNumber, String defaultCountry) {
        float[] vec = new float[36];
        if (rawNumber == null || rawNumber.trim().isEmpty()) return vec;

        String cleaned = rawNumber.trim().replaceAll("[^\\d+]", "");
        String onlyDigits = rawNumber.trim().replaceAll("[^\\d]", "");
        if (onlyDigits.isEmpty()) return vec;

        String countryCodeStr = "";
        String natNumStr = onlyDigits;
        int stdLength = 10;
        boolean isValid = false;

        if (EMERGENCY_SHORTCODES.contains(onlyDigits)) {
            countryCodeStr = defaultCountry;
            natNumStr = onlyDigits;
            stdLength = onlyDigits.length();
            isValid = true;
        } else {
            if (cleaned.startsWith("+91") || (defaultCountry.equals("IN") && onlyDigits.length() == 10)) {
                countryCodeStr = "91";
                natNumStr = cleaned.startsWith("+91") ? onlyDigits.substring(2) : onlyDigits;
                stdLength = 10;
                isValid = natNumStr.length() == 10;
            } else if (cleaned.startsWith("+1") || (defaultCountry.equals("US") && onlyDigits.length() == 10)) {
                countryCodeStr = "1";
                natNumStr = cleaned.startsWith("+1") ? onlyDigits.substring(1) : onlyDigits;
                stdLength = 10;
                isValid = natNumStr.length() == 10;
            } else if (cleaned.startsWith("+44") || defaultCountry.equals("GB")) {
                countryCodeStr = "44";
                natNumStr = cleaned.startsWith("+44") ? onlyDigits.substring(2) : (onlyDigits.length() >= 10 ? onlyDigits.substring(onlyDigits.length() - 10) : onlyDigits);
                stdLength = 10;
                isValid = natNumStr.length() == 10;
            } else if (cleaned.startsWith("+33") || defaultCountry.equals("FR")) {
                countryCodeStr = "33";
                natNumStr = cleaned.startsWith("+33") ? onlyDigits.substring(2) : (onlyDigits.length() >= 9 ? onlyDigits.substring(onlyDigits.length() - 9) : onlyDigits);
                stdLength = 9;
                isValid = natNumStr.length() == 9;
            } else if (cleaned.startsWith("+49") || defaultCountry.equals("DE")) {
                countryCodeStr = "49";
                natNumStr = cleaned.startsWith("+49") ? onlyDigits.substring(2) : (onlyDigits.length() >= 10 ? onlyDigits.substring(onlyDigits.length() - 10) : onlyDigits);
                stdLength = 10;
                isValid = natNumStr.length() >= 10 && natNumStr.length() <= 11;
            } else if (cleaned.startsWith("+61") || defaultCountry.equals("AU")) {
                countryCodeStr = "61";
                natNumStr = cleaned.startsWith("+61") ? onlyDigits.substring(2) : (onlyDigits.length() >= 9 ? onlyDigits.substring(onlyDigits.length() - 9) : onlyDigits);
                stdLength = 9;
                isValid = natNumStr.length() == 9;
            } else if (cleaned.startsWith("+81") || defaultCountry.equals("JP")) {
                countryCodeStr = "81";
                natNumStr = cleaned.startsWith("+81") ? onlyDigits.substring(2) : (onlyDigits.length() >= 10 ? onlyDigits.substring(onlyDigits.length() - 10) : onlyDigits);
                stdLength = 10;
                isValid = natNumStr.length() == 10;
            } else if (cleaned.startsWith("+55") || defaultCountry.equals("BR")) {
                countryCodeStr = "55";
                natNumStr = cleaned.startsWith("+55") ? onlyDigits.substring(2) : (onlyDigits.length() >= 11 ? onlyDigits.substring(onlyDigits.length() - 11) : onlyDigits);
                stdLength = 11;
                isValid = natNumStr.length() == 11;
            } else if (cleaned.startsWith("+62") || defaultCountry.equals("ID")) {
                countryCodeStr = "62";
                natNumStr = cleaned.startsWith("+62") ? onlyDigits.substring(2) : (onlyDigits.length() >= 10 ? onlyDigits.substring(onlyDigits.length() - 10) : onlyDigits);
                stdLength = 10;
                isValid = natNumStr.length() >= 10 && natNumStr.length() <= 12;
            } else if (cleaned.startsWith("+234") || defaultCountry.equals("NG")) {
                countryCodeStr = "234";
                natNumStr = cleaned.startsWith("+234") ? onlyDigits.substring(3) : (onlyDigits.length() >= 10 ? onlyDigits.substring(onlyDigits.length() - 10) : onlyDigits);
                stdLength = 10;
                isValid = natNumStr.length() == 10;
            }
        }

        int natLen = natNumStr.length();
        String fullE164 = "+" + countryCodeStr + natNumStr;

        // 0. Validity
        vec[0] = isValid ? 1.0f : 0.0f;

        // 1. National length normalized
        vec[1] = Math.min((float) natLen / 15.0f, 1.0f);

        // 2. Length discrepancy
        vec[2] = Math.min((float) Math.abs(natLen - stdLength) / 15.0f, 1.0f);

        // 3. Shannon Entropy
        float entropy = computeEntropy(natNumStr);
        vec[3] = Math.min(entropy / 3.321928f, 1.0f);

        // 4. Unique ratio
        Set<Character> uniqueDigits = new HashSet<>();
        for (char c : natNumStr.toCharArray()) uniqueDigits.add(c);
        vec[4] = natLen > 0 ? ((float) uniqueDigits.size() / (float) natLen) : 0.0f;

        // 5. Max repeat run
        int maxRun = computeMaxRepeatRun(natNumStr);
        vec[5] = Math.min((float) maxRun / 10.0f, 1.0f);

        // 6 & 7. Sequential asc / desc
        int maxAsc = computeAscendingRun(natNumStr);
        int maxDesc = computeDescendingRun(natNumStr);
        vec[6] = Math.min((float) maxAsc / 10.0f, 1.0f);
        vec[7] = Math.min((float) maxDesc / 10.0f, 1.0f);

        // 8. Alternating density
        vec[8] = computeAlternatingDensity(natNumStr);

        // 9. Repeated block density
        vec[9] = computeRepeatedBlockDensity(natNumStr);

        // 10. Palindrome symmetry
        vec[10] = computePalindromeSymmetry(natNumStr);

        // 11. Trailing zeros
        int trailingZeros = 0;
        for (int i = natLen - 1; i >= 0; i--) {
            if (natNumStr.charAt(i) == '0') trailingZeros++;
            else break;
        }
        vec[11] = Math.min((float) trailingZeros / 8.0f, 1.0f);

        // 12. Leading digit distribution anomaly
        if (natLen > 0 && (natNumStr.charAt(0) == '0' || natNumStr.charAt(0) == '1') && (countryCodeStr.equals("1") || countryCodeStr.equals("91")) && !EMERGENCY_SHORTCODES.contains(onlyDigits) && !natNumStr.startsWith("1800") && !natNumStr.startsWith("1900") && !natNumStr.startsWith("140")) {
            vec[12] = 1.0f;
        } else {
            vec[12] = 0.0f;
        }

        // 13 - 19. Number Types
        boolean isTollfree = natNumStr.startsWith("1800") || natNumStr.startsWith("800") || natNumStr.startsWith("888") || natNumStr.startsWith("877") || natNumStr.startsWith("866") || natNumStr.startsWith("855") || natNumStr.startsWith("844");
        boolean isPremium = (natNumStr.startsWith("1900") || (countryCodeStr.equals("1") && natNumStr.startsWith("900")) || (countryCodeStr.equals("44") && natNumStr.startsWith("900")) || (countryCodeStr.equals("33") && natNumStr.startsWith("89")));
        boolean isVoip = natNumStr.startsWith("140") || natNumStr.startsWith("843");
        boolean isMobile = (natLen == 10 && (natNumStr.charAt(0) == '6' || natNumStr.charAt(0) == '7' || natNumStr.charAt(0) == '8' || natNumStr.charAt(0) == '9') && countryCodeStr.equals("91")) ||
                           (natLen == 10 && countryCodeStr.equals("1") && !isTollfree && !isPremium) ||
                           (countryCodeStr.equals("44") && natNumStr.startsWith("7")) ||
                           (countryCodeStr.equals("81") && (natNumStr.startsWith("90") || natNumStr.startsWith("80") || natNumStr.startsWith("70")));
        boolean isFixed = !isMobile && !isTollfree && !isPremium;
        boolean isUan = natNumStr.startsWith("140") || EMERGENCY_SHORTCODES.contains(onlyDigits);

        vec[13] = isTollfree ? 1.0f : 0.0f;
        vec[14] = isPremium ? 1.0f : 0.0f;
        vec[15] = 0.0f;
        vec[16] = isVoip ? 1.0f : 0.0f;
        vec[17] = isMobile ? 1.0f : 0.0f;
        vec[18] = isFixed ? 1.0f : 0.0f;
        vec[19] = isUan ? 1.0f : 0.0f;

        // 20. Wangiri High Cost Prefix
        boolean isWangiri = WANGIRI_PREFIXES.contains(countryCodeStr);
        if (!isWangiri) {
            for (String wp : WANGIRI_PREFIXES) {
                if (onlyDigits.startsWith(wp)) { isWangiri = true; break; }
            }
        }
        vec[20] = isWangiri ? 1.0f : 0.0f;

        // 21. Telemarketing series
        boolean isTelemarketing = false;
        for (String pat : TELEMARKETING_PREFIXES) {
            if (fullE164.matches(pat) || cleaned.matches(pat)) { isTelemarketing = true; break; }
        }
        vec[21] = isTelemarketing ? 1.0f : 0.0f;

        // 22. Unallocated exchange code
        boolean isUnallocated = false;
        if (countryCodeStr.equals("1") && natLen == 10) {
            String nxx = natNumStr.substring(3, 6);
            if (nxx.endsWith("11") || nxx.equals("555")) isUnallocated = true;
        }
        vec[22] = isUnallocated ? 1.0f : 0.0f;

        // 23. Shortcode spoof
        vec[23] = (natLen <= 6 && cleaned.startsWith("+")) ? 1.0f : 0.0f;

        // 24. Hard Negative Bank
        boolean isBank = isTollfree;
        if (!isBank) {
            for (String bp : LEGITIMATE_BANK_PATTERNS) {
                if (fullE164.matches(bp) || cleaned.matches(bp)) { isBank = true; break; }
            }
        }
        vec[24] = isBank ? 1.0f : 0.0f;

        // 25. Hard Negative Emergency
        vec[25] = (EMERGENCY_SHORTCODES.contains(onlyDigits) || EMERGENCY_SHORTCODES.contains(natNumStr)) ? 1.0f : 0.0f;

        // 26. Same country
        boolean sameCountry = (defaultCountry.equals("IN") && countryCodeStr.equals("91")) ||
                              (defaultCountry.equals("US") && countryCodeStr.equals("1")) ||
                              (defaultCountry.equals("GB") && countryCodeStr.equals("44")) ||
                              (defaultCountry.equals("FR") && countryCodeStr.equals("33")) ||
                              (defaultCountry.equals("DE") && countryCodeStr.equals("49")) ||
                              (defaultCountry.equals("AU") && countryCodeStr.equals("61")) ||
                              (defaultCountry.equals("JP") && countryCodeStr.equals("81")) ||
                              (defaultCountry.equals("BR") && countryCodeStr.equals("55")) ||
                              (defaultCountry.equals("ID") && countryCodeStr.equals("62")) ||
                              (defaultCountry.equals("NG") && countryCodeStr.equals("234")) ||
                              (defaultCountry.equals("SO") && countryCodeStr.equals("252"));
        vec[26] = sameCountry ? 1.0f : 0.0f;

        // 27. Country risk tier
        if (isWangiri) vec[27] = 1.0f;
        else if (countryCodeStr.equals("91") || countryCodeStr.equals("1") || countryCodeStr.equals("44") || countryCodeStr.equals("61") || countryCodeStr.equals("49") || countryCodeStr.equals("33") || countryCodeStr.equals("81") || countryCodeStr.equals("55") || countryCodeStr.equals("62") || countryCodeStr.equals("234") || countryCodeStr.equals("252")) vec[27] = 0.10f;
        else vec[27] = 0.40f;

        // 28. Joint: Wangiri Trap
        vec[28] = (isWangiri && (vec[3] < 0.70f || vec[2] > 0.0f)) ? 1.0f : 0.0f;

        // 29. Joint: Low-Entropy Robocall
        vec[29] = ((vec[5] >= 0.50f || vec[6] >= 0.60f || vec[7] >= 0.60f || vec[8] >= 0.50f) && vec[24] == 0.0f && vec[25] == 0.0f) ? 1.0f : 0.0f;

        // 30. Joint: Spoofed Short Dialer
        vec[30] = (vec[2] >= 0.20f && (isPremium || isUnallocated)) ? 1.0f : 0.0f;

        // 31. Joint: Telemarketer Block
        vec[31] = (isTelemarketing && vec[4] <= 0.70f) ? 1.0f : 0.0f;

        // 32. Digit variance density
        if (natLen > 0) {
            int[] counts = new int[10];
            for (char c : natNumStr.toCharArray()) {
                if (c >= '0' && c <= '9') counts[c - '0']++;
            }
            float mean = (float) natLen / 10.0f;
            float sumSq = 0.0f;
            for (int count : counts) sumSq += (count - mean) * (count - mean);
            float var = sumSq / 10.0f;
            vec[32] = Math.min(var / 5.0f, 1.0f);
        }

        // 33. Consecutive diff sum
        if (natLen > 1) {
            int diffSum = 0;
            for (int i = 1; i < natLen; i++) {
                diffSum += Math.abs((natNumStr.charAt(i) - '0') - (natNumStr.charAt(i - 1) - '0'));
            }
            vec[33] = Math.min((float) diffSum / (9.0f * (float) (natLen - 1)), 1.0f);
        }

        // 34 & 35
        vec[34] = 0.0f;
        vec[35] = 0.0f;

        return vec;
    }

    private static float computeEntropy(String s) {
        if (s == null || s.isEmpty()) return 0.0f;
        int[] freq = new int[10];
        for (char c : s.toCharArray()) if (c >= '0' && c <= '9') freq[c - '0']++;
        double entropy = 0.0;
        double len = s.length();
        for (int count : freq) {
            if (count > 0) {
                double p = count / len;
                entropy -= p * (Math.log(p) / Math.log(2.0));
            }
        }
        return (float) entropy;
    }

    private static int computeMaxRepeatRun(String s) {
        if (s == null || s.isEmpty()) return 0;
        int maxRun = 1;
        int curr = 1;
        for (int i = 1; i < s.length(); i++) {
            if (s.charAt(i) == s.charAt(i - 1)) {
                curr++;
                if (curr > maxRun) maxRun = curr;
            } else curr = 1;
        }
        return maxRun;
    }

    private static int computeAscendingRun(String s) {
        if (s == null || s.length() < 2) return 0;
        int maxAsc = 1;
        int curr = 1;
        for (int i = 1; i < s.length(); i++) {
            if ((s.charAt(i) - '0') - (s.charAt(i - 1) - '0') == 1) {
                curr++;
                if (curr > maxAsc) maxAsc = curr;
            } else curr = 1;
        }
        return maxAsc;
    }

    private static int computeDescendingRun(String s) {
        if (s == null || s.length() < 2) return 0;
        int maxDesc = 1;
        int curr = 1;
        for (int i = 1; i < s.length(); i++) {
            if ((s.charAt(i) - '0') - (s.charAt(i - 1) - '0') == -1) {
                curr++;
                if (curr > maxDesc) maxDesc = curr;
            } else curr = 1;
        }
        return maxDesc;
    }

    private static float computeAlternatingDensity(String s) {
        if (s == null || s.length() < 4) return 0.0f;
        int count = 0;
        for (int i = 0; i < s.length() - 2; i++) {
            if (s.charAt(i) == s.charAt(i + 2) && s.charAt(i) != s.charAt(i + 1)) count++;
        }
        return Math.min((float) count / (float) (s.length() - 2), 1.0f);
    }

    private static float computeRepeatedBlockDensity(String s) {
        if (s == null || s.length() < 4) return 0.0f;
        for (int i = 0; i < s.length() - 3; i++) {
            if (s.substring(i, i + 2).equals(s.substring(i + 2, i + 4))) return 1.0f;
        }
        for (int i = 0; i < s.length() - 5; i++) {
            if (s.substring(i, i + 3).equals(s.substring(i + 3, i + 6))) return 1.0f;
        }
        return 0.0f;
    }

    private static float computePalindromeSymmetry(String s) {
        if (s == null || s.length() < 2) return 0.0f;
        int matches = 0;
        int len = s.length();
        for (int i = 0; i < len; i++) {
            if (s.charAt(i) == s.charAt(len - 1 - i)) matches++;
        }
        return (float) matches / (float) len;
    }

    public static void main(String[] args) {
        String num = args.length > 0 ? args[0] : "+911800112211";
        String country = args.length > 1 ? args[1] : "IN";
        float[] features = extractFeatures(num, country);

        StringBuilder sb = new StringBuilder();
        sb.append("[");
        for (int i = 0; i < features.length; i++) {
            sb.append(String.format(Locale.US, "%.4f", features[i]));
            if (i < features.length - 1) sb.append(", ");
        }
        sb.append("]");
        System.out.println(sb.toString());
    }
}