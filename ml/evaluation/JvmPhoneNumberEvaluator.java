import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.regex.*;
import com.google.i18n.phonenumbers.PhoneNumberUtil;
import com.google.i18n.phonenumbers.PhoneNumberUtil.PhoneNumberFormat;
import com.google.i18n.phonenumbers.PhoneNumberUtil.PhoneNumberType;
import com.google.i18n.phonenumbers.Phonenumber.PhoneNumber;

/**
 * Pure Java 17 Complete End-to-End Evaluator for AEGIS-PNP2.
 * Uses official Google libphonenumber library.
 */
public class JvmPhoneNumberEvaluator {

    private static final PhoneNumberUtil phoneUtil = PhoneNumberUtil.getInstance();

    private static final Set<String> WANGIRI_PREFIXES = new HashSet<>(Arrays.asList(
        "881", "882", "883", "247", "232", "252", "224", "255", "257", "269", "239", "245", "674", "688", "870", "871", "872", "873"
    ));

    private static final Set<String> EMERGENCY_SHORTCODES = new HashSet<>(Arrays.asList(
        "112", "911", "999", "100", "101", "102", "108", "1091", "1930", "000", "110", "119", "17", "18"
    ));

    private static final List<String> TELEMARKETING_PREFIXES = Arrays.asList(
        "^\\+?91140\\d{7}$",
        "^\\+?4484[345]\\d{7}$",
        "^\\+?1(844|855|866)\\d{7}$",
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

    static class ParseResult {
        String e164 = "";
        String countryCode = "";
        String nationalNumber = "";
        int stdLength = 10;
        boolean isValid = false;
        PhoneNumberType type = PhoneNumberType.UNKNOWN;
    }

    public static ParseResult normalizeAndParse(String rawNumber, String defaultCountry) {
        ParseResult r = new ParseResult();
        if (rawNumber == null || rawNumber.trim().isEmpty()) {
            return r;
        }

        String rawClean = rawNumber.trim();
        String onlyDigits = rawClean.replaceAll("[^\\d]", "");
        String cleaned = rawClean.replaceAll("[^\\d+]", "");

        if (EMERGENCY_SHORTCODES.contains(onlyDigits)) {
            r.e164 = onlyDigits;
            r.countryCode = defaultCountry;
            r.nationalNumber = onlyDigits;
            r.stdLength = onlyDigits.length();
            r.isValid = true;
            r.type = PhoneNumberType.UAN;
            return r;
        }

        // All zeros or malformed check
        boolean allZeros = true;
        for (char c : onlyDigits.toCharArray()) {
            if (c != '0') { allZeros = false; break; }
        }
        if (allZeros || onlyDigits.length() < 3 || onlyDigits.length() > 15) {
            r.e164 = rawClean;
            r.countryCode = defaultCountry.equals("IN") ? "91" : (defaultCountry.equals("US") ? "1" : "44");
            r.nationalNumber = onlyDigits;
            r.stdLength = 10;
            r.isValid = false;
            return r;
        }

        try {
            PhoneNumber parsed = phoneUtil.parse(rawClean, defaultCountry);
            r.isValid = phoneUtil.isValidNumber(parsed);
            r.e164 = phoneUtil.format(parsed, PhoneNumberFormat.E164);
            r.countryCode = String.valueOf(parsed.getCountryCode());
            r.nationalNumber = String.valueOf(parsed.getNationalNumber());
            r.type = phoneUtil.getNumberType(parsed);
            r.stdLength = 10;
            if (r.countryCode.equals("33") || r.countryCode.equals("61")) r.stdLength = 9;
            else if (r.countryCode.equals("55")) r.stdLength = 11;
            return r;
        } catch (Exception e) {
            for (String wp : WANGIRI_PREFIXES) {
                if (cleaned.startsWith("+" + wp) || onlyDigits.startsWith(wp)) {
                    r.countryCode = wp;
                    r.nationalNumber = onlyDigits.length() > wp.length() ? onlyDigits.substring(wp.length()) : onlyDigits;
                    r.e164 = "+" + wp + r.nationalNumber;
                    r.stdLength = 10;
                    r.isValid = true;
                    return r;
                }
            }

            if (cleaned.startsWith("+91") || (defaultCountry.equals("IN") && onlyDigits.length() >= 10)) {
                r.countryCode = "91";
                r.nationalNumber = cleaned.startsWith("+91") || (onlyDigits.startsWith("91") && onlyDigits.length() >= 12) ? onlyDigits.substring(2) : (onlyDigits.length() >= 10 ? onlyDigits.substring(onlyDigits.length() - 10) : onlyDigits);
                r.e164 = "+91" + r.nationalNumber;
                r.stdLength = 10;
                r.isValid = (r.nationalNumber.length() >= 10 && r.nationalNumber.length() <= 11);
            } else if (cleaned.startsWith("+1") || (defaultCountry.equals("US") && onlyDigits.length() == 10)) {
                r.countryCode = "1";
                r.nationalNumber = cleaned.startsWith("+1") || (onlyDigits.startsWith("1") && onlyDigits.length() == 11) ? onlyDigits.substring(1) : (onlyDigits.length() >= 10 ? onlyDigits.substring(onlyDigits.length() - 10) : onlyDigits);
                r.e164 = "+1" + r.nationalNumber;
                r.stdLength = 10;
                r.isValid = (r.nationalNumber.length() == 10);
            } else {
                r.countryCode = onlyDigits.length() >= 3 ? onlyDigits.substring(0, 3) : onlyDigits;
                r.nationalNumber = onlyDigits.length() > 3 ? onlyDigits.substring(3) : onlyDigits;
                r.e164 = "+" + r.countryCode + r.nationalNumber;
                r.stdLength = 10;
                r.isValid = (onlyDigits.length() >= 7 && onlyDigits.length() <= 15);
            }
            return r;
        }
    }

    public static float[] extractFeatures(String rawNumber, String defaultCountry) {
        float[] vec = new float[36];
        ParseResult p = normalizeAndParse(rawNumber, defaultCountry);
        if (p.nationalNumber == null || p.nationalNumber.isEmpty()) return vec;

        String onlyDigits = rawNumber.trim().replaceAll("[^\\d]", "");
        int natLen = p.nationalNumber.length();
        String fullE164 = p.e164;

        // 0. Validity
        vec[0] = p.isValid ? 1.0f : 0.0f;

        // 1. National length normalized
        vec[1] = Math.min((float) natLen / 15.0f, 1.0f);

        // 2. Length discrepancy
        vec[2] = Math.min((float) Math.abs(natLen - p.stdLength) / 15.0f, 1.0f);

        // 3. Shannon Entropy
        float entropy = computeEntropy(p.nationalNumber);
        vec[3] = Math.min(entropy / 3.321928f, 1.0f);

        // 4. Unique ratio
        Set<Character> uniqueDigits = new HashSet<>();
        for (char c : p.nationalNumber.toCharArray()) uniqueDigits.add(c);
        vec[4] = natLen > 0 ? ((float) uniqueDigits.size() / (float) natLen) : 0.0f;

        // 5. Max repeat run
        int maxRun = computeMaxRepeatRun(p.nationalNumber);
        vec[5] = Math.min((float) maxRun / 10.0f, 1.0f);

        // 6 & 7. Sequential asc / desc
        int maxAsc = computeAscendingRun(p.nationalNumber);
        int maxDesc = computeDescendingRun(p.nationalNumber);
        vec[6] = Math.min((float) maxAsc / 10.0f, 1.0f);
        vec[7] = Math.min((float) maxDesc / 10.0f, 1.0f);

        // 8. Alternating density
        vec[8] = computeAlternatingDensity(p.nationalNumber);

        // 9. Repeated block density
        vec[9] = computeRepeatedBlockDensity(p.nationalNumber);

        // 10. Palindrome symmetry
        vec[10] = computePalindromeSymmetry(p.nationalNumber);

        // 11. Trailing zeros
        int trailingZeros = 0;
        for (int i = natLen - 1; i >= 0; i--) {
            if (p.nationalNumber.charAt(i) == '0') trailingZeros++;
            else break;
        }
        vec[11] = Math.min((float) trailingZeros / 8.0f, 1.0f);

        // 12. Leading digit anomaly
        if (natLen > 0 && (p.nationalNumber.charAt(0) == '0' || p.nationalNumber.charAt(0) == '1') && (p.countryCode.equals("1") || p.countryCode.equals("91")) && !EMERGENCY_SHORTCODES.contains(onlyDigits) && !p.nationalNumber.startsWith("1800") && !p.nationalNumber.startsWith("1900") && !p.nationalNumber.startsWith("140")) {
            vec[12] = 1.0f;
        } else {
            vec[12] = 0.0f;
        }

        // 13 - 19. Number Types
        boolean isTollfree = (p.type == PhoneNumberType.TOLL_FREE) || p.nationalNumber.startsWith("1800") || p.nationalNumber.startsWith("800") || p.nationalNumber.startsWith("888") || p.nationalNumber.startsWith("877") || p.nationalNumber.startsWith("866") || p.nationalNumber.startsWith("855") || p.nationalNumber.startsWith("844");
        boolean isPremium = (p.type == PhoneNumberType.PREMIUM_RATE) || (p.nationalNumber.startsWith("1900") || (p.countryCode.equals("1") && p.nationalNumber.startsWith("900")) || (p.countryCode.equals("44") && p.nationalNumber.startsWith("900")) || (p.countryCode.equals("33") && p.nationalNumber.startsWith("89")));
        boolean isVoip = (p.type == PhoneNumberType.VOIP) || p.nationalNumber.startsWith("140") || p.nationalNumber.startsWith("843");
        boolean isMobile = (p.type == PhoneNumberType.MOBILE) || ((natLen == 10 && (p.nationalNumber.charAt(0) == '6' || p.nationalNumber.charAt(0) == '7' || p.nationalNumber.charAt(0) == '8' || p.nationalNumber.charAt(0) == '9') && p.countryCode.equals("91")) ||
                           (natLen == 10 && p.countryCode.equals("1") && !isTollfree && !isPremium) ||
                           (p.countryCode.equals("44") && p.nationalNumber.startsWith("7")) ||
                           (p.countryCode.equals("81") && (p.nationalNumber.startsWith("90") || p.nationalNumber.startsWith("80") || p.nationalNumber.startsWith("70"))));
        boolean isFixed = (p.type == PhoneNumberType.FIXED_LINE) || (!isMobile && !isTollfree && !isPremium);
        boolean isUan = (p.type == PhoneNumberType.UAN) || p.nationalNumber.startsWith("140") || EMERGENCY_SHORTCODES.contains(onlyDigits);

        vec[13] = isTollfree ? 1.0f : 0.0f;
        vec[14] = isPremium ? 1.0f : 0.0f;
        vec[15] = (p.type == PhoneNumberType.SHARED_COST) ? 1.0f : 0.0f;
        vec[16] = isVoip ? 1.0f : 0.0f;
        vec[17] = isMobile ? 1.0f : 0.0f;
        vec[18] = isFixed ? 1.0f : 0.0f;
        vec[19] = isUan ? 1.0f : 0.0f;

        // 20. Wangiri Prefix
        boolean isWangiri = WANGIRI_PREFIXES.contains(p.countryCode);
        if (!isWangiri) {
            for (String wp : WANGIRI_PREFIXES) {
                if (onlyDigits.startsWith(wp)) { isWangiri = true; break; }
            }
        }
        vec[20] = isWangiri ? 1.0f : 0.0f;

        // 21. Telemarketing series
        boolean isTelemarketing = false;
        for (String pat : TELEMARKETING_PREFIXES) {
            if (fullE164.matches(pat) || rawNumber.matches(pat)) { isTelemarketing = true; break; }
        }
        vec[21] = isTelemarketing ? 1.0f : 0.0f;

        // 22. Unallocated exchange
        boolean isUnallocated = false;
        if (p.countryCode.equals("1") && natLen == 10) {
            String nxx = p.nationalNumber.substring(3, 6);
            if (nxx.endsWith("11") || nxx.equals("555")) isUnallocated = true;
        }
        vec[22] = isUnallocated ? 1.0f : 0.0f;

        // 23. Shortcode spoof
        vec[23] = (natLen <= 6 && rawNumber.trim().startsWith("+")) ? 1.0f : 0.0f;

        // 24. Hard Negative Bank
        boolean isBank = isTollfree;
        if (!isBank) {
            for (String bp : LEGITIMATE_BANK_PATTERNS) {
                if (fullE164.matches(bp) || rawNumber.matches(bp)) { isBank = true; break; }
            }
        }
        vec[24] = isBank ? 1.0f : 0.0f;

        // 25. Hard Negative Emergency
        vec[25] = (EMERGENCY_SHORTCODES.contains(onlyDigits) || EMERGENCY_SHORTCODES.contains(p.nationalNumber)) ? 1.0f : 0.0f;

        // 26. Same country
        boolean sameCountry = (defaultCountry.equals("IN") && p.countryCode.equals("91")) ||
                              (defaultCountry.equals("US") && p.countryCode.equals("1")) ||
                              (defaultCountry.equals("GB") && p.countryCode.equals("44")) ||
                              (defaultCountry.equals("FR") && p.countryCode.equals("33")) ||
                              (defaultCountry.equals("DE") && p.countryCode.equals("49")) ||
                              (defaultCountry.equals("AU") && p.countryCode.equals("61")) ||
                              (defaultCountry.equals("JP") && p.countryCode.equals("81")) ||
                              (defaultCountry.equals("BR") && p.countryCode.equals("55")) ||
                              (defaultCountry.equals("ID") && p.countryCode.equals("62")) ||
                              (defaultCountry.equals("NG") && p.countryCode.equals("234"));
        vec[26] = sameCountry ? 1.0f : 0.0f;

        // 27. Country risk tier
        if (isWangiri) vec[27] = 1.0f;
        else if (p.countryCode.equals("91") || p.countryCode.equals("1") || p.countryCode.equals("44") || p.countryCode.equals("61") || p.countryCode.equals("49") || p.countryCode.equals("33") || p.countryCode.equals("81") || p.countryCode.equals("55") || p.countryCode.equals("62") || p.countryCode.equals("234")) vec[27] = 0.10f;
        else vec[27] = 0.40f;

        // 28. Joint Wangiri Trap
        vec[28] = (isWangiri && (vec[3] < 0.70f || vec[2] > 0.0f)) ? 1.0f : 0.0f;

        // 29. Joint Low-Entropy Robocall
        vec[29] = ((vec[5] >= 0.50f || vec[6] >= 0.60f || vec[7] >= 0.60f || vec[8] >= 0.50f) && vec[24] == 0.0f && vec[25] == 0.0f) ? 1.0f : 0.0f;

        // 30. Joint Spoofed Short Dialer
        vec[30] = (vec[2] >= 0.20f && (isPremium || isUnallocated)) ? 1.0f : 0.0f;

        // 31. Joint Telemarketer Block
        vec[31] = (isTelemarketing && vec[4] <= 0.70f) ? 1.0f : 0.0f;

        // 32. Digit variance
        if (natLen > 0) {
            int[] counts = new int[10];
            for (char c : p.nationalNumber.toCharArray()) {
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
                diffSum += Math.abs((p.nationalNumber.charAt(i) - '0') - (p.nationalNumber.charAt(i - 1) - '0'));
            }
            vec[33] = Math.min((float) diffSum / (9.0f * (float) (natLen - 1)), 1.0f);
        }

        // 34. Personal Number & 35. Pager
        vec[34] = (p.type == PhoneNumberType.PERSONAL_NUMBER) ? 1.0f : 0.0f;
        vec[35] = (p.type == PhoneNumberType.PAGER) ? 1.0f : 0.0f;

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
                double prob = count / len;
                entropy -= prob * (Math.log(prob) / Math.log(2.0));
            }
        }
        return (float) entropy;
    }

    private static int computeMaxRepeatRun(String s) {
        if (s == null || s.isEmpty()) return 0;
        int maxRun = 1; int curr = 1;
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
        int maxAsc = 1; int curr = 1;
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
        int maxDesc = 1; int curr = 1;
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
        int matches = 0; int len = s.length();
        for (int i = 0; i < len; i++) {
            if (s.charAt(i) == s.charAt(len - 1 - i)) matches++;
        }
        return (float) matches / (float) len;
    }

    public static void main(String[] args) {
        String num = args.length > 0 ? args[0] : "+911800112211";
        String country = args.length > 1 ? args[1] : "IN";

        ParseResult p = normalizeAndParse(num, country);
        float[] features = extractFeatures(num, country);

        StringBuilder sb = new StringBuilder();
        sb.append("{");
        sb.append("\"normalizedE164\":\"").append(p.e164).append("\",");
        sb.append("\"isValid\":").append(p.isValid).append(",");
        sb.append("\"numberType\":\"").append(p.type.name()).append("\",");
        sb.append("\"features\":[");
        for (int i = 0; i < features.length; i++) {
            sb.append(String.format(Locale.US, "%.4f", features[i]));
            if (i < features.length - 1) sb.append(",");
        }
        sb.append("]}");
        System.out.println(sb.toString());
    }
}