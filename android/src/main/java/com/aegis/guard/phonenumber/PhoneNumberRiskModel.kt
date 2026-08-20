package com.aegis.guard.phonenumber

import org.json.JSONObject
import kotlin.math.exp

/**
 * On-Device Phone Number Pattern Risk Model (AEGIS-PNP2).
 * Pure-Kotlin 150-Tree Gradient Boosted Trees Ensemble with Exact Sigmoid Calibration.
 * Inference Latency: < 0.05 ms (Zero JNI).
 */
class PhoneNumberRiskModel {

    private var isLoaded = false
    private var modelVersion = "2.0.0"
    private var learningRate: Float = 0.08f
    private var initValue: Float = 0.0f
    private var paramA: Float = -1.317682f
    private var paramB: Float = -0.209460f
    private val trees = mutableListOf<DecisionNode>()
    private val featureNames = mutableListOf<String>()

    data class DecisionNode(
        val nodeCount: Int,
        val childrenLeft: IntArray,
        val childrenRight: IntArray,
        val feature: IntArray,
        val threshold: FloatArray,
        val value: FloatArray
    )

    fun loadModelFromJsonString(jsonString: String): Boolean {
        return try {
            val json = JSONObject(jsonString)
            modelVersion = json.optString("version", "2.0.0")
            learningRate = json.getDouble("learning_rate").toFloat()
            initValue = json.getDouble("init_value").toFloat()

            if (json.has("calibration")) {
                val calibObj = json.getJSONObject("calibration")
                paramA = calibObj.getDouble("param_A").toFloat()
                paramB = calibObj.getDouble("param_B").toFloat()
            }

            val treesArray = json.getJSONArray("trees")
            trees.clear()

            for (i in 0 until treesArray.length()) {
                val treeObj = treesArray.getJSONObject(i)
                val nodeCount = treeObj.getInt("node_count")

                val cLeft = treeObj.getJSONArray("children_left")
                val cRight = treeObj.getJSONArray("children_right")
                val feat = treeObj.getJSONArray("feature")
                val thresh = treeObj.getJSONArray("threshold")
                val vals = treeObj.getJSONArray("value")

                val childrenLeft = IntArray(nodeCount) { cLeft.getInt(it) }
                val childrenRight = IntArray(nodeCount) { cRight.getInt(it) }
                val feature = IntArray(nodeCount) { feat.getInt(it) }
                val threshold = FloatArray(nodeCount) { thresh.getDouble(it).toFloat() }
                val value = FloatArray(nodeCount) { vals.getDouble(it).toFloat() }

                trees.add(
                    DecisionNode(
                        nodeCount = nodeCount,
                        childrenLeft = childrenLeft,
                        childrenRight = childrenRight,
                        feature = feature,
                        threshold = threshold,
                        value = value
                    )
                )
            }

            val featNamesArray = json.getJSONArray("feature_names")
            featureNames.clear()
            for (i in 0 until featNamesArray.length()) {
                featureNames.add(featNamesArray.getString(i))
            }

            isLoaded = true
            true
        } catch (e: Exception) {
            isLoaded = false
            false
        }
    }

    fun assessNumber(rawNumber: String, defaultCountry: String = "IN"): PhoneNumberVerdict {
        val features = PhoneNumberFeatureExtractor.extractFeatures(rawNumber, defaultCountry)
        val normalizedE164 = PhoneNumberFeatureExtractor.getNormalizedE164(rawNumber, defaultCountry)
        return predict(rawNumber, normalizedE164, defaultCountry, features)
    }

    fun predict(rawNumber: String, normalizedE164: String, defaultCountry: String, features: FloatArray): PhoneNumberVerdict {
        val isValid = features[0] > 0.5f

        if (!isValid) {
            return PhoneNumberVerdict(
                rawNumber = rawNumber,
                normalizedE164 = normalizedE164,
                country = defaultCountry,
                riskScore = 0,
                rawLogit = 0.0f,
                calibratedProbability = 0.0f,
                tier = ThreatTier.INVALID,
                confidence = ConfidenceLevel.HIGH,
                isThreat = false,
                isAbstain = true,
                isInvalid = true,
                topReasonCodes = listOf(ReasonCodes.INVALID_NUMBER_SYNTAX),
                topExplanations = listOf(ReasonCodes.DESCRIPTIONS[ReasonCodes.INVALID_NUMBER_SYNTAX]!!)
            )
        }

        if (!isLoaded || trees.isEmpty()) {
            return PhoneNumberVerdict(
                rawNumber = rawNumber,
                normalizedE164 = normalizedE164,
                country = defaultCountry,
                riskScore = 0,
                rawLogit = 0.0f,
                calibratedProbability = 0.0f,
                tier = ThreatTier.UNKNOWN,
                confidence = ConfidenceLevel.LOW,
                isThreat = false,
                isAbstain = true,
                isInvalid = false,
                topReasonCodes = listOf(ReasonCodes.STANDARD_ENTROPY_STRUCTURE),
                topExplanations = listOf(ReasonCodes.DESCRIPTIONS[ReasonCodes.STANDARD_ENTROPY_STRUCTURE]!!)
            )
        }

        // Tree Ensemble Raw Logit Evaluation
        var rawLogit = initValue
        for (tree in trees) {
            var currentNode = 0
            while (tree.childrenLeft[currentNode] != -1) {
                val featIdx = tree.feature[currentNode]
                val featVal = if (featIdx in features.indices) features[featIdx] else 0.0f
                val thresh = tree.threshold[currentNode]

                currentNode = if (featVal <= thresh) {
                    tree.childrenLeft[currentNode]
                } else {
                    tree.childrenRight[currentNode]
                }
            }

            val leafValue = tree.value[currentNode] * learningRate
            rawLogit += leafValue
        }

        // Exact Sigmoid Calibration: P(Threat | logit) = 1.0 / (1.0 + exp(paramA * rawLogit + paramB))
        val expTerm = exp((paramA * rawLogit + paramB).toDouble())
        val calibratedProb = (1.0 / (1.0 + expTerm)).toFloat()
        val score = (calibratedProb * 100).toInt().coerceIn(0, 100)

        val tier = when {
            calibratedProb >= 0.70f -> ThreatTier.SCAM
            calibratedProb >= 0.40f -> ThreatTier.SPAM
            calibratedProb >= 0.15f -> ThreatTier.UNKNOWN
            else -> ThreatTier.LEGITIMATE
        }

        val confidence = when {
            calibratedProb >= 0.75f || calibratedProb <= 0.10f -> ConfidenceLevel.HIGH
            calibratedProb in 0.40f..0.74f -> ConfidenceLevel.MEDIUM
            else -> ConfidenceLevel.LOW
        }

        // Per-Instance Active Feature Reason Codes
        val reasonCodes = mutableListOf<String>()
        if (features[20] > 0.5f || features[28] > 0.5f) reasonCodes.add(ReasonCodes.WANGIRI_HIGH_COST_RANGE)
        if (features[21] > 0.5f || features[31] > 0.5f) reasonCodes.add(ReasonCodes.TELEMARKETING_SERIES)
        if (features[14] > 0.5f) reasonCodes.add(ReasonCodes.PREMIUM_RATE_SERVICE)
        if (features[29] > 0.5f || features[5] >= 0.5f || features[6] >= 0.6f || features[7] >= 0.6f) reasonCodes.add(ReasonCodes.LOW_ENTROPY_REPETITION)
        if (features[24] > 0.5f) reasonCodes.add(ReasonCodes.LEGITIMATE_TOLLFREE_BANK)
        if (features[25] > 0.5f) reasonCodes.add(ReasonCodes.EMERGENCY_SERVICE)

        if (reasonCodes.isEmpty()) {
            reasonCodes.add(ReasonCodes.STANDARD_ENTROPY_STRUCTURE)
        }

        val explanations = reasonCodes.map { ReasonCodes.DESCRIPTIONS[it] ?: it }

        return PhoneNumberVerdict(
            rawNumber = rawNumber,
            normalizedE164 = normalizedE164,
            country = defaultCountry,
            riskScore = score,
            rawLogit = rawLogit,
            calibratedProbability = calibratedProb,
            tier = tier,
            confidence = confidence,
            isThreat = (tier == ThreatTier.SPAM || tier == ThreatTier.SCAM),
            isAbstain = (tier == ThreatTier.UNKNOWN),
            isInvalid = false,
            topReasonCodes = reasonCodes.take(3),
            topExplanations = explanations.take(3)
        )
    }
}