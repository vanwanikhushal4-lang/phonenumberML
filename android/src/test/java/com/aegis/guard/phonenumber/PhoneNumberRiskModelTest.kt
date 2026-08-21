package com.aegis.guard.phonenumber

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.io.File
import kotlin.math.abs

/**
 * Unit, Parity & Negative Control Test Suite for AEGIS-PNP2 Android Kotlin Runtime.
 * Loads committed phonenumber_risk_model.json asset and asserts all 39 canonical golden test cases
 * against independent authored semantic expectations and reference numeric predictions.
 */
class PhoneNumberRiskModelTest {

    private lateinit var riskModel: PhoneNumberRiskModel

    @Before
    fun setUp() {
        riskModel = PhoneNumberRiskModel()
        val candidates = listOf(
            File("src/main/assets/phonenumber_risk_model.json"),
            File("android/src/main/assets/phonenumber_risk_model.json"),
            File("../android/src/main/assets/phonenumber_risk_model.json"),
            File("ml/export/phonenumber_risk_model.json"),
            File("../../ml/export/phonenumber_risk_model.json")
        )
        val modelFile = candidates.find { it.exists() }
        assertNotNull("phonenumber_risk_model.json asset must exist", modelFile)
        val jsonStr = modelFile!!.readText()
        val loaded = riskModel.loadModelFromJsonString(jsonStr)
        assertTrue("Model asset must successfully load and pass SHA-256 + AST verification", loaded)
    }

    @Test
    fun testAll39GoldenVectorsMatchReferenceOutputs() {
        val goldenCandidates = listOf(
            File("ml/export/golden_test_vectors.json"),
            File("../../ml/export/golden_test_vectors.json"),
            File("../ml/export/golden_test_vectors.json")
        )
        val goldenFile = goldenCandidates.find { it.exists() }
        assertNotNull("golden_test_vectors.json must exist", goldenFile)

        val goldenJson = JSONObject(goldenFile!!.readText())
        val testCases = goldenJson.getJSONArray("test_cases")
        assertEquals(39, testCases.length())

        val extractor = PhoneNumberFeatureExtractor()

        for (i in 0 until testCases.length()) {
            val caseObj = testCases.getJSONObject(i)
            val caseId = caseObj.getString("case_id")
            val rawNum = caseObj.getString("raw_number")
            val country = caseObj.getString("country")
            val expTier = caseObj.getString("expected_tier")
            val expIsThreat = caseObj.getBoolean("expected_is_threat")
            val expIsValid = caseObj.getBoolean("expected_is_valid")
            val expIsAbstain = caseObj.getBoolean("expected_is_abstain")
            val expIsInvalid = caseObj.getBoolean("expected_is_invalid")
            val expE164 = caseObj.getString("expected_normalized_e164")
            val expRawLogit = caseObj.getDouble("reference_raw_logit")
            val expCalProb = caseObj.getDouble("reference_calibrated_probability")
            val expScore = caseObj.getInt("reference_score")
            val expFeats = caseObj.getJSONArray("reference_features")

            val assessment = riskModel.assessNumber(rawNum, country)

            assertEquals("Case $caseId isValid mismatch", expIsValid, assessment.isValid)
            assertEquals("Case $caseId isInvalid mismatch", expIsInvalid, assessment.isInvalid)
            assertEquals("Case $caseId E.164 mismatch", expE164, assessment.normalizedE164)
            assertEquals("Case $caseId tier mismatch", expTier, assessment.threatTier.name)
            assertEquals("Case $caseId isThreat mismatch", expIsThreat, assessment.isThreat)
            assertEquals("Case $caseId isAbstain mismatch", expIsAbstain, assessment.isAbstain)

            if (expIsValid) {
                // Verify Feature Parity (all 36 features within 1e-4 tolerance)
                val ktFeats = extractor.extractFeatures(rawNum, country)
                assertEquals("Case $caseId feature count mismatch", 36, ktFeats.size)
                for (fIdx in 0 until 36) {
                    val expVal = expFeats.getDouble(fIdx)
                    val actVal = ktFeats[fIdx]
                    assertTrue(
                        "Case $caseId feat[$fIdx] mismatch: exp=$expVal, act=$actVal",
                        abs(expVal - actVal) < 1e-4
                    )
                }

                // Verify Numeric Prediction Parity (within 1e-4 tolerance)
                assertTrue(
                    "Case $caseId rawLogit mismatch: exp=$expRawLogit, act=${assessment.rawLogit}",
                    abs(expRawLogit - assessment.rawLogit) < 1e-4
                )
                assertTrue(
                    "Case $caseId calProb mismatch: exp=$expCalProb, act=${assessment.calibratedProbability}",
                    abs(expCalProb - assessment.calibratedProbability) < 1e-4
                )
                assertEquals("Case $caseId score mismatch", expScore, assessment.riskScore)
            }
        }
    }

    @Test
    fun testBenignToSpamNegativeControlFailsAssertion() {
        val sbiAssessment = riskModel.assessNumber("+911800112211", "IN")
        assertEquals("SBI Bank must evaluate to LEGITIMATE", ThreatTier.LEGITIMATE, sbiAssessment.threatTier)
        assertNotEquals("Flawed SPAM classification must not equal nominal outcome", ThreatTier.SPAM, sbiAssessment.threatTier)
    }

    @Test
    fun testWangiriToLegitimateNegativeControlFailsAssertion() {
        val wangiriAssessment = riskModel.assessNumber("+881631555123", "IN")
        assertEquals("Wangiri trap must evaluate to SCAM", ThreatTier.SCAM, wangiriAssessment.threatTier)
        assertNotEquals("Flawed LEGITIMATE classification must not equal nominal outcome", ThreatTier.LEGITIMATE, wangiriAssessment.threatTier)
    }

    @Test
    fun testCorruptJsonRejectionAndSafeFallback() {
        val corruptModel = PhoneNumberRiskModel()
        assertFalse("Malformed JSON must be rejected", corruptModel.loadModelFromJsonString("{ \"corrupt\": true }"))

        val verdict = corruptModel.assessNumber("+919820481729", "IN")
        assertNotNull(verdict)
        assertTrue("Uninitialized model must abstain", verdict.isAbstain)
        assertEquals(ThreatTier.UNKNOWN, verdict.threatTier)
    }

    @Test
    fun testAstValidationRejection() {
        val invalidModel = PhoneNumberRiskModel()
        val badAstJson = """{
            "schema_version": "2.1.0",
            "num_features": 20,
            "num_trees": 150,
            "init_value": 0.48,
            "trees": []
        }"""
        assertFalse("Invalid feature count must fail AST validation", invalidModel.loadModelFromJsonString(badAstJson))
    }

    @Test
    fun testModelTamperingThresholdModificationFailsClosed() {
        val candidates = listOf(
            File("src/main/assets/phonenumber_risk_model.json"),
            File("android/src/main/assets/phonenumber_risk_model.json"),
            File("../android/src/main/assets/phonenumber_risk_model.json"),
            File("ml/export/phonenumber_risk_model.json"),
            File("../../ml/export/phonenumber_risk_model.json")
        )
        val modelFile = candidates.find { it.exists() }
        assertNotNull("phonenumber_risk_model.json asset must exist", modelFile)
        val originalJsonStr = modelFile!!.readText()

        val json = JSONObject(originalJsonStr)
        val treesArray = json.getJSONArray("trees")
        val firstTree = treesArray.getJSONObject(0)
        val nodesArray = firstTree.getJSONArray("nodes")
        val rootNode = nodesArray.getJSONObject(0)

        // Tamper with root node threshold while keeping original checksum in metadata
        rootNode.put("threshold", 0.99999999)

        val tamperedRiskModel = PhoneNumberRiskModel()
        val loadResult = tamperedRiskModel.loadModelFromJsonString(json.toString())

        assertFalse("Tampered model payload must fail SHA-256 verification and return false on load", loadResult)

        // Safe fail-closed check
        val fallbackAssessment = tamperedRiskModel.assessNumber("+919820481729", "IN")
        assertTrue("Tampered model assessment must fail closed to abstain", fallbackAssessment.isAbstain)
        assertEquals(ThreatTier.UNKNOWN, fallbackAssessment.threatTier)
    }
}