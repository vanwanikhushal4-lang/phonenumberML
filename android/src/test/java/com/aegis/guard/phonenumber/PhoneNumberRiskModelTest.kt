package com.aegis.guard.phonenumber

import org.json.JSONObject
import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.io.File

/**
 * Unit & Regression Test Suite for AEGIS-PNP2 Android Kotlin Runtime.
 * Loads committed phonenumber_risk_model.json asset and asserts all 20 independent golden test cases.
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
    fun testAll21GoldenVectorsMatchExactExpectedOutcomes() {
        val goldenCandidates = listOf(
            File("ml/export/golden_test_vectors.json"),
            File("../../ml/export/golden_test_vectors.json"),
            File("../ml/export/golden_test_vectors.json")
        )
        val goldenFile = goldenCandidates.find { it.exists() }
        assertNotNull("golden_test_vectors.json must exist", goldenFile)

        val goldenJson = JSONObject(goldenFile!!.readText())
        val testCases = goldenJson.getJSONArray("test_cases")
        assertEquals(21, testCases.length())

        for (i in 0 until testCases.length()) {
            val caseObj = testCases.getJSONObject(i)
            val caseId = caseObj.getString("case_id")
            val rawNum = caseObj.getString("raw_number")
            val country = caseObj.getString("country")
            val expTier = caseObj.getString("expected_tier")
            val expIsThreat = caseObj.getBoolean("expected_is_threat")

            val assessment = riskModel.assessNumber(rawNum, country)

            assertEquals("Case $caseId tier mismatch", expTier, assessment.threatTier.name)
            assertEquals("Case $caseId isThreat mismatch", expIsThreat, assessment.isThreat)
            if (expTier == "INVALID") {
                assertTrue("Case $caseId should be invalid", assessment.isInvalid)
                assertFalse("Case $caseId should not be valid", assessment.isValid)
            } else {
                assertFalse("Case $caseId should not be invalid", assessment.isInvalid)
                assertTrue("Case $caseId should be valid", assessment.isValid)
            }
        }
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
        val validJsonStr = modelFile!!.readText()

        // Tamper a single threshold in the JSON while retaining original sha256_checksum
        val tamperedJsonStr = validJsonStr.replaceFirst("\"threshold\": 0.", "\"threshold\": 0.99999999")
        assertNotEquals("JSON must be modified for tampering test", validJsonStr, tamperedJsonStr)

        val tamperModel = PhoneNumberRiskModel()
        val loaded = tamperModel.loadModelFromJsonString(tamperedJsonStr)
        assertFalse("Tampered tree thresholds must fail SHA-256 integrity verification and fail closed", loaded)

        // Verify fail-closed behavior on evaluation
        val assessment = tamperModel.assessNumber("+919820481729", "IN")
        assertTrue("Unloaded/tampered model must safely abstain", assessment.isAbstain)
        assertEquals(ThreatTier.UNKNOWN, assessment.threatTier)
    }
}