import java.io.File;
import java.nio.file.Files;
import java.nio.file.Paths;

/**
 * Android Unit & Integration Test Suite for AEGIS-PNP2.
 * Executes on JVM against production phonenumber_risk_model.json asset.
 */
public class PhoneNumberRiskModelTest {

    public static void main(String[] args) throws Exception {
        System.out.println("=====================================================================================");
        System.out.println("      AEGIS-PNP2 ANDROID / JVM UNIT & INTEGRATION TEST SUITE");
        System.out.println("=====================================================================================");

        String modelPath = "android/src/main/assets/phonenumber_risk_model.json";
        File f = new File(modelPath);
        if (!f.exists()) {
            modelPath = "ml/export/phonenumber_risk_model.json";
        }

        String jsonContent = new String(Files.readAllBytes(Paths.get(modelPath)));
        if (!jsonContent.contains("\"trees\"") || !jsonContent.contains("\"init_value\"")) {
            throw new AssertionError("Model JSON asset corrupted or invalid format!");
        }

        // 1. Test Feature Dimensions via JvmPhoneNumberEvaluator
        float[] feat = JvmPhoneNumberEvaluator.extractFeatures("+911800112211", "IN");
        if (feat.length != 36) {
            throw new AssertionError("Feature vector length mismatch: expected 36, got " + feat.length);
        }
        System.out.println("[+] Test 1/4 PASSED: Feature dimensions == 36");

        // 2. Test Allowlist Negative Overrides
        if (feat[24] != 1.0f) {
            throw new AssertionError("SBI Toll-free failed bank allowlist feature activation!");
        }
        System.out.println("[+] Test 2/4 PASSED: Bank hard-negative feature active");

        // 3. Test Invalid Syntax Rejection
        JvmPhoneNumberEvaluator.ParseResult pInvalid = JvmPhoneNumberEvaluator.normalizeAndParse("0000000000", "IN");
        if (pInvalid.isValid) {
            throw new AssertionError("All-zeros sequence falsely accepted as valid!");
        }
        System.out.println("[+] Test 3/4 PASSED: Invalid structure correctly rejected");

        // 4. Test Emergency Line
        JvmPhoneNumberEvaluator.ParseResult pEmerg = JvmPhoneNumberEvaluator.normalizeAndParse("112", "IN");
        if (!pEmerg.isValid || !pEmerg.e164.equals("112")) {
            throw new AssertionError("Emergency 112 failed normalization!");
        }
        System.out.println("[+] Test 4/4 PASSED: Emergency shortcodes normalized and valid");

        System.out.println("\n[+] ALL ANDROID / JVM INTEGRATION TESTS PASSED (4 / 4 OK)");
    }
}