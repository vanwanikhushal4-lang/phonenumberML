package com.aegis.guard.phonenumber

import org.json.JSONObject
import kotlin.math.exp

/**
 * On-Device Phone Number Pattern Risk Model (AEGIS-PNP1).
 * Pure-Kotlin Gradient Boosted Trees Ensemble Evaluator.
 * Evaluates 150 decision trees in < 0.05 ms with zero JNI.
 */
class PhoneNumberRiskModel {

    private var isLoaded = false
    private var learningRate: Float = 0.08f
    private var initValue: Float = 0.0f
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

    fun loadModelFromJsonString(jsonString: String) {
        try {
            val json = JSONObject(jsonString)
            learningRate = json.getDouble("learning_rate").toFloat()
            initValue = json.getDouble("init_value").toFloat()

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
        } catch (e: Exception) {
            isLoaded = false
        }
    }

    fun assessNumber(rawNumber: String, defaultCountry: String = "IN"): PhoneNumberVerdict {
        val features = PhoneNumberFeatureExtractor.extractFeatures(rawNumber, defaultCountry)
        return predict(rawNumber, defaultCountry, features)
    }

    fun predict(rawNumber: String, defaultCountry: String, features: FloatArray): PhoneNumberVerdict {
        if (!isLoaded || trees.isEmpty()) {
            return PhoneNumberVerdict(
                rawNumber = rawNumber,
                country = defaultCountry,
                riskScore = 0,
                probability = 0.0f,
                tier = ThreatTier.UNKNOWN,
                confidence = ConfidenceLevel.LOW,
                isThreat = false,
                isAbstain = true,
                topReasonCodes = listOf(ReasonCodes.INSUFFICIENT_STRUCTURAL_EVIDENCE),
                topExplanations = listOf(ReasonCodes.DESCRIPTIONS[ReasonCodes.INSUFFICIENT_STRUCTURAL_EVIDENCE]!!)
            )
        }

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

        // Calibrated Sigmoid Logit -> Probability
        val prob = (1.0 / (1.0 + exp(-rawLogit.toDouble()))).toFloat()
        val score = (prob * 100).toInt().coerceIn(0, 100)

        val tier = when {
            prob >= 0.70f -> ThreatTier.SCAM
            prob >= 0.40f -> ThreatTier.SPAM
            prob >= 0.15f -> ThreatTier.UNKNOWN
            else -> ThreatTier.LEGITIMATE
        }

        val confidence = when {
            prob >= 0.75f || prob <= 0.10f -> ConfidenceLevel.HIGH
            prob in 0.40f..0.74f -> ConfidenceLevel.MEDIUM
            else -> ConfidenceLevel.LOW
        }

        val reasonCodes = mutableListOf<String>()
        if (features[20] > 0.5f || features[28] > 0.5f) reasonCodes.add(ReasonCodes.WANGIRI_HIGH_COST_RANGE)
        if (features[21] > 0.5f || features[31] > 0.5f) reasonCodes.add(ReasonCodes.TELEMARKETING_SERIES)
        if (features[14] > 0.5f) reasonCodes.add(ReasonCodes.PREMIUM_RATE_SERVICE)
        if (features[16] > 0.5f || features[29] > 0.5f) reasonCodes.add(ReasonCodes.VOIP_VIRTUAL_RANGE)
        if (features[5] >= 0.3f || features[6] >= 0.3f || features[7] >= 0.3f || features[8] >= 0.3f) reasonCodes.add(ReasonCodes.LOW_ENTROPY_REPETITION)
        if (features[24] > 0.5f) reasonCodes.add(ReasonCodes.LEGITIMATE_TOLLFREE_BANK)
        if (features[25] > 0.5f) reasonCodes.add(ReasonCodes.EMERGENCY_SERVICE)

        if (reasonCodes.isEmpty()) {
            reasonCodes.add(ReasonCodes.INSUFFICIENT_STRUCTURAL_EVIDENCE)
        }

        val explanations = reasonCodes.map { ReasonCodes.DESCRIPTIONS[it] ?: it }

        return PhoneNumberVerdict(
            rawNumber = rawNumber,
            country = defaultCountry,
            riskScore = score,
            probability = prob,
            tier = tier,
            confidence = confidence,
            isThreat = (tier == ThreatTier.SPAM || tier == ThreatTier.SCAM),
            isAbstain = (tier == ThreatTier.UNKNOWN),
            topReasonCodes = reasonCodes.take(3),
            topExplanations = explanations.take(3)
        )
    }
}