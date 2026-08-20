package com.aegis.guard.phonenumber

import org.junit.Assert.*
import org.junit.Before
import org.junit.Test
import org.json.JSONObject

/**
 * Unit & Regression Test Suite for AEGIS-PNP2 Android Runtime.
 */
class PhoneNumberRiskModelTest {

    private lateinit var riskModel: PhoneNumberRiskModel

    @Before
    fun setUp() {
        riskModel = PhoneNumberRiskModel()
    }

    @Test
    fun testCorruptJsonFallbackDoesNotCrash() {
        val corruptJson = "{ \"invalid\": true }"
        val success = riskModel.loadModelFromJsonString(corruptJson)
        assertFalse(success)

        val verdict = riskModel.assessNumber("+919820481729", "IN")
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
}