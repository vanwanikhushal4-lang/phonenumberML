import com.google.i18n.phonenumbers.PhoneNumberUtil;
import com.google.i18n.phonenumbers.PhoneNumberUtil.PhoneNumberFormat;
import com.google.i18n.phonenumbers.PhoneNumberUtil.PhoneNumberType;
import com.google.i18n.phonenumbers.Phonenumber.PhoneNumber;

import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;
import java.util.*;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

/**
 * Pure JVM production evaluator for AEGIS-PNP2 model.
 * 64-bit IEEE 754 float precision across all 150 GBT trees.
 */
public class JvmPhoneNumberEvaluator {

    static final PhoneNumberUtil phoneUtil = PhoneNumberUtil.getInstance();

    static final Set<String> WANGIRI_PREFIXES = new HashSet<>(Arrays.asList(
            "881", "882", "883", "247", "870", "871", "872", "873", "239", "245", "674", "688"
    ));

    static final Set<String> EMERGENCY_SHORTCODES = new HashSet<>(Arrays.asList(
            "112", "911", "999", "100", "101", "102", "108", "1091", "1930", "000", "110", "119", "17", "18"
    ));

    static final List<Pattern> TELEMARKETING_PATTERNS = Arrays.asList(
            Pattern.compile("^\\+?91140\\d{7}$"),
            Pattern.compile("^\\+?44(84[345]|87[01])\\d{7}$"),
            Pattern.compile("^\\+?3389\\d{7}$")
    );

    static final List<Pattern> BANK_PATTERNS = Arrays.asList(
            Pattern.compile("^\\+?911800\\d{4,8}$"),
            Pattern.compile("^\\+?1800\\d{7}$"),
            Pattern.compile("^\\+?44800\\d{6,8}$"),
            Pattern.compile("^\\+?611800\\d{6,8}$"),
            Pattern.compile("^\\+?49800\\d{6,8}$"),
            Pattern.compile("^\\+?33800\\d{6,8}$")
    );

    static class DecisionNode {
        boolean isLeaf;
        int featureIdx = -1;
        double threshold = 0.0;
        double leafValue = 0.0;
        int leftChild = -1;
        int rightChild = -1;
    }

    static class DecisionTree {
        List<DecisionNode> nodes = new ArrayList<>();

        double evaluate(double[] features) {
            int curr = 0;
            while (curr >= 0 && curr < nodes.size()) {
                DecisionNode n = nodes.get(curr);
                if (n.isLeaf) return n.leafValue;
                curr = (features[n.featureIdx] <= n.threshold) ? n.leftChild : n.rightChild;
            }
            return 0.0;
        }
    }

    static double initValue = 0.0;
    static double plattParamA = 25.464305;
    static double plattParamB = -10.880817;
    static List<DecisionTree> loadedTrees = new ArrayList<>();
    static boolean modelInitialized = false;

    static void loadModelJson(String modelPath) {
        if (modelInitialized) return;
        try {
            String content = new String(Files.readAllBytes(Paths.get(modelPath)));
            
            Matcher mInit = Pattern.compile("\"init_value\"\\s*:\\s*([-+]?[0-9]*\\.?[0-9]+(?:[eE][-+]?[0-9]+)?)").matcher(content);
            if (mInit.find()) {
                initValue = Double.parseDouble(mInit.group(1));
            }

            Matcher mA = Pattern.compile("\"param_a\"\\s*:\\s*([-+]?[0-9]*\\.?[0-9]+(?:[eE][-+]?[0-9]+)?)").matcher(content);
            if (mA.find()) {
                plattParamA = Double.parseDouble(mA.group(1));
            }

            Matcher mB = Pattern.compile("\"param_b\"\\s*:\\s*([-+]?[0-9]*\\.?[0-9]+(?:[eE][-+]?[0-9]+)?)").matcher(content);
            if (mB.find()) {
                plattParamB = Double.parseDouble(mB.group(1));
            }

            loadedTrees.clear();
            String[] treeSplits = content.split("\\{\\s*\"tree_id\"");
            for (int i = 1; i < treeSplits.length; i++) {
                String chunk = treeSplits[i];
                DecisionTree dt = new DecisionTree();
                
                Pattern nodePattern = Pattern.compile("\\{[^{}]*?\"node_id\"[^{}]*?\\}");
                Matcher nm = nodePattern.matcher(chunk);
                while (nm.find()) {
                    String nStr = nm.group();
                    DecisionNode n = new DecisionNode();
                    n.isLeaf = nStr.contains("\"is_leaf\": true") || nStr.contains("\"is_leaf\":true");
                    if (n.isLeaf) {
                        Matcher ml = Pattern.compile("\"leaf_value\"\\s*:\\s*([-+]?[0-9]*\\.?[0-9]+(?:[eE][-+]?[0-9]+)?)").matcher(nStr);
                        if (ml.find()) n.leafValue = Double.parseDouble(ml.group(1));
                    } else {
                        Matcher mf = Pattern.compile("\"feature_idx\"\\s*:\\s*(\\d+)").matcher(nStr);
                        Matcher mt = Pattern.compile("\"threshold\"\\s*:\\s*([-+]?[0-9]*\\.?[0-9]+(?:[eE][-+]?[0-9]+)?)").matcher(nStr);
                        Matcher ml = Pattern.compile("\"left_child\"\\s*:\\s*(\\d+)").matcher(nStr);
                        Matcher mr = Pattern.compile("\"right_child\"\\s*:\\s*(\\d+)").matcher(nStr);
                        if (mf.find()) n.featureIdx = Integer.parseInt(mf.group(1));
                        if (mt.find()) n.threshold = Double.parseDouble(mt.group(1));
                        if (ml.find()) n.leftChild = Integer.parseInt(ml.group(1));
                        if (mr.find()) n.rightChild = Integer.parseInt(mr.group(1));
                    }
                    dt.nodes.add(n);
                }
                loadedTrees.add(dt);
            }
            modelInitialized = true;
        } catch (Exception e) {
            modelInitialized = false;
        }
    }

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
        String onlyDigits = rawClean.replaceAll("[^0-9]", "");
        String cleaned = rawClean.replaceAll("[^0-9+]", "");

        if (EMERGENCY_SHORTCODES.contains(onlyDigits)) {
            r.e164 = onlyDigits;
            r.countryCode = defaultCountry;
            r.nationalNumber = onlyDigits;
            r.stdLength = onlyDigits.length();
            r.isValid = true;
            r.type = PhoneNumberType.UAN;
            return r;
        }

        boolean allZeros = onlyDigits.length() > 0 && onlyDigits.matches("^0+$");
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

            if (r.countryCode.equals("33") || r.countryCode.equals("61")) r.stdLength = 9;
            else if (r.countryCode.equals("55")) r.stdLength = 11;
            else r.stdLength = 10;
            return r;
        } catch (Exception e) {
            if (cleaned.startsWith("+91") || (defaultCountry.equals("IN") && onlyDigits.length() == 10)) {
                r.countryCode = "91";
                r.nationalNumber = cleaned.startsWith("+91") ? onlyDigits.substring(2) : onlyDigits;
                r.e164 = "+91" + r.nationalNumber;
                r.isValid = r.nationalNumber.length() == 10;
                r.type = PhoneNumberType.MOBILE;
            } else if (cleaned.startsWith("+1") || (defaultCountry.equals("US") && onlyDigits.length() == 10)) {
                r.countryCode = "1";
                r.nationalNumber = cleaned.startsWith("+1") ? onlyDigits.substring(1) : onlyDigits;
                r.e164 = "+1" + r.nationalNumber;
                r.isValid = r.nationalNumber.length() == 10;
                r.type = PhoneNumberType.FIXED_LINE_OR_MOBILE;
            } else {
                r.e164 = cleaned.startsWith("+") ? cleaned : ("+" + onlyDigits);
                r.countryCode = onlyDigits.length() >= 3 ? onlyDigits.substring(0, 3) : onlyDigits;
                r.nationalNumber = onlyDigits.length() > 3 ? onlyDigits.substring(3) : onlyDigits;
                r.isValid = false;
                r.type = PhoneNumberType.UNKNOWN;
            }
            return r;
        }
    }

    public static double[] extractFeatures(String rawNumber, String defaultCountry) {
        double[] vec = new double[36];
        ParseResult p = normalizeAndParse(rawNumber, defaultCountry);
        if (p.nationalNumber.isEmpty()) return vec;

        String onlyDigits = rawNumber != null ? rawNumber.replaceAll("[^0-9]", "") : "";
        int natLen = p.nationalNumber.length();
        String fullE164 = p.e164;
        String countryCodeStr = p.countryCode;
        String natNumStr = p.nationalNumber;

        // 0. num_is_valid_e164
        vec[0] = p.isValid ? 1.0 : 0.0;

        // 1. num_national_length_normalized
        vec[1] = Math.min((double) natLen / 15.0, 1.0);

        // 2. num_length_discrepancy
        vec[2] = Math.min((double) Math.abs(natLen - p.stdLength) / 15.0, 1.0);

        // 3. digit_shannon_entropy
        double entropy = computeEntropy(natNumStr);
        vec[3] = Math.min(entropy / 3.321928, 1.0);

        // 4. digit_unique_ratio
        Set<Character> uniqueDigits = new HashSet<>();
        for (char c : natNumStr.toCharArray()) uniqueDigits.add(c);
        vec[4] = natLen > 0 ? ((double) uniqueDigits.size() / (double) natLen) : 0.0;

        // 5. digit_max_repeat_run
        int maxRun = computeMaxRepeatRun(natNumStr);
        vec[5] = Math.min((double) maxRun / 10.0, 1.0);

        // 6 & 7. digit_max_sequential_asc / desc
        int maxAsc = computeAscendingRun(natNumStr);
        int maxDesc = computeDescendingRun(natNumStr);
        vec[6] = Math.min((double) maxAsc / 10.0, 1.0);
        vec[7] = Math.min((double) maxDesc / 10.0, 1.0);

        // 8. digit_alternating_pattern_density
        vec[8] = computeAlternatingDensity(natNumStr);

        // 9. digit_repeated_block_density
        vec[9] = computeRepeatedBlockDensity(natNumStr);

        // 10. digit_palindrome_symmetry
        vec[10] = computePalindromeSymmetry(natNumStr);

        // 11. digit_trailing_zeros_count
        int trailingZeros = 0;
        for (int i = natLen - 1; i >= 0; i--) {
            if (natNumStr.charAt(i) == '0') trailingZeros++;
            else break;
        }
        vec[11] = Math.min((double) trailingZeros / 8.0, 1.0);

        // 12. digit_leading_zero_or_one
        if (natLen > 0 && (natNumStr.charAt(0) == '0' || natNumStr.charAt(0) == '1')
                && (countryCodeStr.equals("1") || countryCodeStr.equals("91"))
                && !EMERGENCY_SHORTCODES.contains(onlyDigits)
                && !natNumStr.startsWith("1800") && !natNumStr.startsWith("1900") && !natNumStr.startsWith("140")) {
            vec[12] = 1.0;
        } else {
            vec[12] = 0.0;
        }

        // 13 - 19. plan types
        boolean isTollfree = (p.type == PhoneNumberType.TOLL_FREE) || natNumStr.startsWith("1800") || natNumStr.startsWith("800") || natNumStr.startsWith("888") || natNumStr.startsWith("877") || natNumStr.startsWith("866") || natNumStr.startsWith("855") || natNumStr.startsWith("844");
        boolean isPremium = (p.type == PhoneNumberType.PREMIUM_RATE) || natNumStr.startsWith("1900") || (countryCodeStr.equals("1") && natNumStr.startsWith("900")) || (countryCodeStr.equals("44") && natNumStr.startsWith("900")) || (countryCodeStr.equals("33") && natNumStr.startsWith("89"));
        boolean isShared = (p.type == PhoneNumberType.SHARED_COST);
        boolean isVoip = (p.type == PhoneNumberType.VOIP) || natNumStr.startsWith("140") || natNumStr.startsWith("843");
        boolean isMobile = (p.type == PhoneNumberType.MOBILE) || (p.type == PhoneNumberType.FIXED_LINE_OR_MOBILE) || (natLen == 10 && (natNumStr.charAt(0) >= '6' && natNumStr.charAt(0) <= '9') && countryCodeStr.equals("91")) || (natLen == 10 && countryCodeStr.equals("1") && !isTollfree && !isPremium) || (countryCodeStr.equals("44") && natNumStr.startsWith("7")) || (countryCodeStr.equals("81") && (natNumStr.startsWith("90") || natNumStr.startsWith("80") || natNumStr.startsWith("70")));
        boolean isFixed = (p.type == PhoneNumberType.FIXED_LINE) || (!isMobile && !isTollfree && !isPremium);
        boolean isUan = (p.type == PhoneNumberType.UAN) || natNumStr.startsWith("140") || EMERGENCY_SHORTCODES.contains(onlyDigits);

        vec[13] = isTollfree ? 1.0 : 0.0;
        vec[14] = isPremium ? 1.0 : 0.0;
        vec[15] = isShared ? 1.0 : 0.0;
        vec[16] = isVoip ? 1.0 : 0.0;
        vec[17] = isMobile ? 1.0 : 0.0;
        vec[18] = isFixed ? 1.0 : 0.0;
        vec[19] = isUan ? 1.0 : 0.0;

        // 20. risk_wangiri_high_cost_prefix
        boolean isWangiri = WANGIRI_PREFIXES.contains(countryCodeStr);
        if (!isWangiri) {
            for (String wp : WANGIRI_PREFIXES) {
                if (onlyDigits.startsWith(wp)) { isWangiri = true; break; }
            }
        }
        vec[20] = isWangiri ? 1.0 : 0.0;

        // 21. risk_telemarketing_series
        boolean isTelemarketing = false;
        for (Pattern pat : TELEMARKETING_PATTERNS) {
            if (pat.matcher(fullE164).find() || (rawNumber != null && pat.matcher(rawNumber).find())) {
                isTelemarketing = true; break;
            }
        }
        vec[21] = isTelemarketing ? 1.0 : 0.0;

        // 22. risk_unallocated_exchange_code
        boolean isUnallocated = false;
        if (countryCodeStr.equals("1") && natLen == 10) {
            String nxx = natNumStr.substring(3, 6);
            if (nxx.endsWith("11") || nxx.equals("555")) isUnallocated = true;
        }
        vec[22] = isUnallocated ? 1.0 : 0.0;

        // 23. risk_shortcode_spoof_candidate
        vec[23] = (natLen <= 6 && rawNumber != null && rawNumber.trim().startsWith("+")) ? 1.0 : 0.0;

        // 24. hard_neg_legitimate_bank_support
        boolean isBank = false;
        for (Pattern pat : BANK_PATTERNS) {
            if (pat.matcher(fullE164).find() || (rawNumber != null && pat.matcher(rawNumber).find())) {
                isBank = true; break;
            }
        }
        vec[24] = isBank ? 1.0 : 0.0;

        // 25. hard_neg_emergency_service
        vec[25] = (EMERGENCY_SHORTCODES.contains(onlyDigits) || EMERGENCY_SHORTCODES.contains(natNumStr)) ? 1.0 : 0.0;

        // 26. geo_is_same_country
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
        vec[26] = sameCountry ? 1.0 : 0.0;

        // 27. geo_country_risk_tier
        if (isWangiri) vec[27] = 1.0;
        else if (Arrays.asList("91", "1", "44", "61", "49", "33", "81", "55", "62", "234", "252").contains(countryCodeStr)) vec[27] = 0.10;
        else vec[27] = 0.40;

        // 28. joint_wangiri_callback_trap
        vec[28] = (isWangiri && (vec[3] < 0.70 || vec[2] > 0.0)) ? 1.0 : 0.0;

        // 29. joint_low_entropy_robocall
        vec[29] = ((vec[5] >= 0.50 || vec[6] >= 0.60 || vec[7] >= 0.60 || vec[8] >= 0.50) && vec[24] == 0.0 && vec[25] == 0.0) ? 1.0 : 0.0;

        // 30. joint_spoofed_short_dialer
        vec[30] = (vec[2] >= 0.20 && (isPremium || isUnallocated)) ? 1.0 : 0.0;

        // 31. joint_telemarketer_block
        vec[31] = (isTelemarketing && vec[4] <= 0.70) ? 1.0 : 0.0;

        // 32. digit_variance_density
        if (natLen > 0) {
            int[] counts = new int[10];
            for (char c : natNumStr.toCharArray()) {
                if (c >= '0' && c <= '9') counts[c - '0']++;
            }
            double mean = (double) natLen / 10.0;
            double sumSq = 0.0;
            for (int count : counts) sumSq += (count - mean) * (count - mean);
            double v = sumSq / 10.0;
            vec[32] = Math.min(v / 5.0, 1.0);
        }

        // 33. digit_consecutive_diff_sum
        if (natLen > 1) {
            int diffSum = 0;
            for (int i = 1; i < natLen; i++) {
                diffSum += Math.abs((natNumStr.charAt(i) - '0') - (natNumStr.charAt(i - 1) - '0'));
            }
            vec[33] = Math.min((double) diffSum / (9.0 * (double) (natLen - 1)), 1.0);
        }

        vec[34] = 0.0;
        vec[35] = 0.0;

        return vec;
    }

    private static double computeEntropy(String s) {
        if (s == null || s.isEmpty()) return 0.0;
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
        return entropy;
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

    private static double computeAlternatingDensity(String s) {
        if (s == null || s.length() < 4) return 0.0;
        int count = 0;
        for (int i = 0; i < s.length() - 2; i++) {
            if (s.charAt(i) == s.charAt(i + 2) && s.charAt(i) != s.charAt(i + 1)) count++;
        }
        return Math.min((double) count / (double) (s.length() - 2), 1.0);
    }

    private static double computeRepeatedBlockDensity(String s) {
        if (s == null || s.length() < 4) return 0.0;
        for (int i = 0; i < s.length() - 3; i++) {
            if (s.substring(i, i + 2).equals(s.substring(i + 2, i + 4))) return 1.0;
        }
        for (int i = 0; i < s.length() - 5; i++) {
            if (s.substring(i, i + 3).equals(s.substring(i + 3, i + 6))) return 1.0;
        }
        return 0.0;
    }

    private static double computePalindromeSymmetry(String s) {
        if (s == null || s.length() < 2) return 0.0;
        int matches = 0; int len = s.length();
        for (int i = 0; i < len; i++) {
            if (s.charAt(i) == s.charAt(len - 1 - i)) matches++;
        }
        return (double) matches / (double) len;
    }

    public static void main(String[] args) {
        String num = args.length > 0 ? args[0] : "+911800112211";
        String country = args.length > 1 ? args[1] : "IN";
        String modelPath = args.length > 2 ? args[2] : "ml/export/phonenumber_risk_model.json";

        loadModelJson(modelPath);

        ParseResult p = normalizeAndParse(num, country);
        double[] features = extractFeatures(num, country);

        double rawLogit = 0.0;
        double calProb = 0.0;
        int score = 0;
        String tier = "INVALID";
        String confidence = "HIGH";

        if (!p.isValid) {
            tier = "INVALID";
            confidence = "HIGH";
            score = 0;
            calProb = 0.0;
            rawLogit = 0.0;
        } else {
            rawLogit = initValue;
            for (DecisionTree t : loadedTrees) {
                rawLogit += t.evaluate(features);
            }
            calProb = 1.0 / (1.0 + Math.exp(-(plattParamA * rawLogit + plattParamB)));
            score = (int) Math.round(Math.max(0.0, Math.min(1.0, rawLogit)) * 100.0);

            if (rawLogit >= 0.70) {
                tier = "SCAM";
                confidence = "HIGH";
            } else if (rawLogit >= 0.40) {
                tier = "SPAM";
                confidence = "MEDIUM";
            } else if (rawLogit >= 0.15) {
                tier = "UNKNOWN";
                confidence = "LOW";
            } else {
                tier = "LEGITIMATE";
                confidence = "HIGH";
            }
        }

        StringBuilder sb = new StringBuilder();
        sb.append("{");
        sb.append("\"normalizedE164\":\"").append(p.e164).append("\",");
        sb.append("\"isValid\":").append(p.isValid).append(",");
        sb.append("\"numberType\":\"").append(p.type.name()).append("\",");
        sb.append("\"rawLogit\":").append(String.format(Locale.US, "%.6f", rawLogit)).append(",");
        sb.append("\"calibratedProbability\":").append(String.format(Locale.US, "%.6f", calProb)).append(",");
        sb.append("\"riskScore\":").append(score).append(",");
        sb.append("\"threatTier\":\"").append(tier).append("\",");
        sb.append("\"confidence\":\"").append(confidence).append("\",");
        sb.append("\"features\":[");
        for (int i = 0; i < features.length; i++) {
            sb.append(String.format(Locale.US, "%.4f", features[i]));
            if (i < features.length - 1) sb.append(",");
        }
        sb.append("]}");
        System.out.println(sb.toString());
    }
}