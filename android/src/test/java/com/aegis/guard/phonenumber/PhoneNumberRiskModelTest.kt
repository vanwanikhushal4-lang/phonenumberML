package com.aegis.guard.phonenumber

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import java.io.File

/**
 * Unit & Regression Test Suite for AEGIS-PNP2 Android Runtime.
 * Loads actual phonenumber_risk_model.json and validates behavior across all tiers.
 */
class PhoneNumberRiskModelTest {

    private lateinit var riskModel: PhoneNumberRiskModel

    @Before
    fun setUp() {
        riskModel = PhoneNumberRiskModel()
        val modelFile = File("../../ml/export/phonenumber_risk_model.json")
        if (modelFile.exists()) {
            val jsonStr = modelFile.readText()
            riskModel.loadModelFromJsonString(jsonStr)
        }
    }

    @Test
    fun testCorruptJsonFallbackDoesNotCrash() {
        val corruptModel = PhoneNumberRiskModel()
        val corruptJson = "{ \"invalid\": true }"
        val success = corruptModel.loadModelFromJsonString(corruptJson)
        assertFalse(success)

        val verdict = corruptModel.assessNumber("+919820481729", "IN")
        assertNotNull(verdict)
        assertTrue(verdict.isAbstain)
        assertEquals(ThreatTier.UNKNOWN, verdict.tier)
    }

    @Test
    fun testInvalidNumberHandling() {
        val verdict1 = riskModel.assessNumber("0000000000", "IN")
        assertTrue(verdict1.isInvalid)
        assertEquals(ThreatTier.INVALID, verdict1.tier)

        val verdict2 = riskModel.assessNumber("123", "IN")
        assertTrue(verdict2.isInvalid)
        assertEquals(ThreatTier.INVALID, verdict2.tier)
    }

    @Test
    fun testHardNegativeBankSupport() {
        val verdict = riskModel.assessNumber("+911800112211", "IN")
        assertEquals(ThreatTier.LEGITIMATE, verdict.tier)
        assertTrue(verdict.riskScore <= 10)
        assertFalse(verdict.isThreat)
    }

    @Test
    fun testEmergencyNumberHandling() {
        val verdict = riskModel.assessNumber("112", "IN")
        assertEquals(ThreatTier.LEGITIMATE, verdict.tier)
        assertTrue(verdict.riskScore <= 5)
    }

    @Test
    fun testTelemarketerDetection() {
        val verdict = riskModel.assessNumber("+911409988776", "IN")
        assertTrue(verdict.isThreat)
        assertTrue(verdict.riskScore >= 40)
        assertTrue(verdict.tier == ThreatTier.SPAM || verdict.tier == ThreatTier.SCAM)
    }
}