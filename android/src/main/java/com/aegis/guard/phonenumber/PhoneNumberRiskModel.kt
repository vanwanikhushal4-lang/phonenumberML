package com.aegis.guard.phonenumber

import org.json.JSONArray
import org.json.JSONObject
import java.security.MessageDigest
import java.util.Locale
import kotlin.math.exp
import kotlin.math.max
import kotlin.math.min
import kotlin.math.roundToInt

data class PhoneRiskAssessment(
    val rawNumber: String,
    val normalizedE164: String,
    val isValid: Boolean,
    val isThreat: Boolean,
    val isAbstain: Boolean,
    val isInvalid: Boolean,
    val threatTier: ThreatTier,
    val riskScore: Int,
    val rawLogit: Double,
    val calibratedProbability: Double,
    val confidence: String,
    val topReasonCodes: List<String> = emptyList(),
    val topExplanations: List<String> = emptyList(),
    val evaluationLatencyMs: Double = 0.0
) {
    val tier: ThreatTier get() = threatTier
}

/**
 * AEGIS Phone Number Pattern Risk Model (AEGIS-PNP2) Android Runtime.
 * Evaluates 150-tree Gradient Boosted Trees ensemble with continuous risk estimation and Platt calibration.
 * Performs rigorous SHA-256 integrity verification and AST validation on initialization.
 */
class PhoneNumberRiskModel(
    private val extractor: PhoneNumberFeatureExtractor = PhoneNumberFeatureExtractor()
) {

    private val trees = ArrayList<DecisionTree>()
    private var initValue: Double = 0.48885701
    private var plattParamA: Double = 25.464305
    private var plattParamB: Double = -10.880817
    private var isLoaded: Boolean = false
    private var schemaVersion: String = "2.1.0"
    private var expectedChecksum: String = ""

    companion object {
        const val EXPECTED_FEATURE_COUNT = 36
        const val EXPECTED_TREE_COUNT = 150
        const val THRESHOLD_LEGITIMATE_UPPER = 0.10
        const val THRESHOLD_UNKNOWN_LOWER = 0.10
        const val THRESHOLD_SPAM_LOWER = 0.60
        const val THRESHOLD_SCAM_LOWER = 0.98
    }

    data class DecisionNode(
        val isLeaf: Boolean,
        val featureIdx: Int = -1,
        val threshold: Double = 0.0,
        val leafValue: Double = 0.0,
        val leftChild: Int = -1,
        val rightChild: Int = -1
    )

    data class DecisionTree(
        val nodes: List<DecisionNode>
    ) {
        fun evaluate(features: DoubleArray): Double {
            var currIdx = 0
            while (currIdx >= 0 && currIdx < nodes.size) {
                val node = nodes[currIdx]
                if (node.isLeaf) {
                    return node.leafValue
                }
                currIdx = if (features[node.featureIdx] <= node.threshold) {
                    node.leftChild
                } else {
                    node.rightChild
                }
            }
            return 0.0
        }
    }

    @Synchronized
    fun loadModelFromJsonString(jsonString: String): Boolean {
        return try {
            val root = JSONObject(jsonString)

            // 1. Verify Schema Version
            schemaVersion = root.optString("schema_version", "")
            if (schemaVersion.isEmpty()) return false

            // 2. Verify Feature & Tree Counts
            val numFeatures = root.optInt("num_features", -1)
            val numTrees = root.optInt("num_trees", -1)
            if (numFeatures != EXPECTED_FEATURE_COUNT || numTrees != EXPECTED_TREE_COUNT) {
                return false
            }

            // 3. Extract init_value & Platt parameters
            initValue = root.optDouble("init_value", Double.NaN)
            if (initValue.isNaN() || initValue.isInfinite()) return false

            val plattObj = root.optJSONObject("platt_calibrator")
            if (plattObj != null) {
                plattParamA = plattObj.optDouble("param_a", 25.464305)
                plattParamB = plattObj.optDouble("param_b", -10.880817)
            }

            // 4. Extract and Validate Trees
            val treesArray = root.getJSONArray("trees")
            if (treesArray.length() != EXPECTED_TREE_COUNT) {
                return false
            }

            // 5. Verify SHA-256 Checksum
            expectedChecksum = root.optString("sha256_checksum", "")
            if (expectedChecksum.length != 64) {
                return false
            }

            val sb = StringBuilder()
            val parsedTrees = ArrayList<DecisionTree>()
            for (i in 0 until treesArray.length()) {
                val treeObj = treesArray.getJSONObject(i)
                val treeId = treeObj.getInt("tree_id")
                val nodesArray = treeObj.getJSONArray("nodes")
                val numNodes = nodesArray.length()
                if (numNodes < 1) return false

                sb.append("T:").append(treeId).append(":").append(numNodes).append("\n")

                val nodesList = ArrayList<DecisionNode>()
                for (j in 0 until numNodes) {
                    val nObj = nodesArray.getJSONObject(j)
                    val nodeId = nObj.optInt("node_id", -1)
                    if (nodeId != j) return false

                    val isLeaf = nObj.getBoolean("is_leaf")
                    if (isLeaf) {
                        val leafVal = nObj.getDouble("leaf_value")
                        if (leafVal.isNaN() || leafVal.isInfinite()) return false
                        sb.append("L:").append(nodeId).append(":").append(String.format(Locale.US, "%.8f", leafVal)).append("\n")
                        nodesList.add(DecisionNode(isLeaf = true, leafValue = leafVal))
                    } else {
                        val featIdx = nObj.getInt("feature_idx")
                        if (featIdx < 0 || featIdx >= EXPECTED_FEATURE_COUNT) return false

                        val th = nObj.getDouble("threshold")
                        if (th.isNaN() || th.isInfinite()) return false

                        val left = nObj.getInt("left_child")
                        val right = nObj.getInt("right_child")
                        if (left < 0 || left >= numNodes || right < 0 || right >= numNodes) return false

                        sb.append("N:").append(nodeId).append(":")
                            .append(featIdx).append(":")
                            .append(String.format(Locale.US, "%.8f", th)).append(":")
                            .append(left).append(":")
                            .append(right).append("\n")

                        nodesList.add(
                            DecisionNode(
                                isLeaf = false,
                                featureIdx = featIdx,
                                threshold = th,
                                leftChild = left,
                                rightChild = right
                            )
                        )
                    }
                }
                parsedTrees.add(DecisionTree(nodesList))
            }

            // Verify exact constant-time SHA-256 tree integrity
            val canonicalBytes = sb.toString().trimEnd().toByteArray(Charsets.UTF_8)
            val computedDigest = MessageDigest.getInstance("SHA-256").digest(canonicalBytes)
            val computedHex = computedDigest.joinToString("") { "%02x".format(it) }
            if (!MessageDigest.isEqual(computedHex.toByteArray(Charsets.UTF_8), expectedChecksum.toByteArray(Charsets.UTF_8))) {
                trees.clear()
                isLoaded = false
                return false
            }

            trees.clear()
            trees.addAll(parsedTrees)
            isLoaded = true
            true
        } catch (e: Exception) {
            isLoaded = false
            trees.clear()
            false
        }
    }

    fun assessNumber(rawNumber: String?, defaultCountry: String = "IN"): PhoneRiskAssessment {
        val t0 = System.nanoTime()
        val normParse = extractor.normalizeAndParse(rawNumber, defaultCountry)
        val rawClean = rawNumber ?: ""

        if (!normParse.isValid) {
            val latency = (System.nanoTime() - t0) / 1_000_000.0
            return PhoneRiskAssessment(
                rawNumber = rawClean,
                normalizedE164 = normParse.e164,
                isValid = false,
                isThreat = false,
                isAbstain = false,
                isInvalid = true,
                threatTier = ThreatTier.INVALID,
                riskScore = 0,
                rawLogit = 0.0,
                calibratedProbability = 0.0,
                confidence = "HIGH",
                topReasonCodes = listOf("num_is_valid_e164"),
                topExplanations = listOf("Invalid number syntax violating standard numbering plan"),
                evaluationLatencyMs = latency
            )
        }

        if (!isLoaded || trees.isEmpty()) {
            val latency = (System.nanoTime() - t0) / 1_000_000.0
            return PhoneRiskAssessment(
                rawNumber = rawClean,
                normalizedE164 = normParse.e164,
                isValid = true,
                isThreat = false,
                isAbstain = true,
                isInvalid = false,
                threatTier = ThreatTier.UNKNOWN,
                riskScore = 30,
                rawLogit = 0.30,
                calibratedProbability = 0.038,
                confidence = "LOW",
                topReasonCodes = listOf("uninitialized_model"),
                topExplanations = listOf("Model uninitialized - default safe fallback"),
                evaluationLatencyMs = latency
            )
        }

        val features = extractor.extractFeatures(rawNumber, defaultCountry)
        var rawLogit = initValue
        for (tree in trees) {
            rawLogit += tree.evaluate(features)
        }

        val calProb = 1.0 / (1.0 + exp(-(plattParamA * rawLogit + plattParamB)))
        val score = (max(0.0, min(1.0, rawLogit)) * 100.0).roundToInt()

        val (tier, confidence, isThreat, isAbstain) = when {
            calProb >= THRESHOLD_SCAM_LOWER -> Quad(ThreatTier.SCAM, "HIGH", true, false)
            calProb >= THRESHOLD_SPAM_LOWER -> Quad(ThreatTier.SPAM, "MEDIUM", true, false)
            calProb >= THRESHOLD_UNKNOWN_LOWER -> Quad(ThreatTier.UNKNOWN, "LOW", false, true)
            else -> Quad(ThreatTier.LEGITIMATE, "HIGH", false, false)
        }

        val reasonCodes = ArrayList<String>()
        val explanations = ArrayList<String>()
        if (features[20] > 0.5 || features[28] > 0.5) {
            reasonCodes.add("risk_wangiri_high_cost_prefix")
            explanations.add("High-risk international revenue-sharing callback trap (Wangiri scam)")
        }
        if (features[21] > 0.5 || features[31] > 0.5) {
            reasonCodes.add("risk_telemarketing_series")
            explanations.add("Matches registered commercial telemarketing / automated dialer series")
        }
        if (features[14] > 0.5) {
            reasonCodes.add("plan_is_premium_rate")
            explanations.add("High-charge premium rate number service")
        }
        if (features[29] > 0.5 || features[5] >= 0.5 || features[6] >= 0.6 || features[7] >= 0.6) {
            reasonCodes.add("digit_max_repeat_run")
            explanations.add("Unnatural low-entropy repetitive or sequential digit pattern typical of automated robocallers")
        }
        if (features[24] > 0.5) {
            reasonCodes.add("hard_neg_legitimate_bank_support")
            explanations.add("Verified legitimate customer care / banking institution toll-free line")
        }
        if (features[25] > 0.5) {
            reasonCodes.add("hard_neg_emergency_service")
            explanations.add("Recognized national emergency or public service line")
        }
        if (reasonCodes.isEmpty()) {
            reasonCodes.add("standard_entropy_structure")
            explanations.add("Standard number structure. Digits alone provide insufficient evidence.")
        }

        val latency = (System.nanoTime() - t0) / 1_000_000.0

        return PhoneRiskAssessment(
            rawNumber = rawClean,
            normalizedE164 = normParse.e164,
            isValid = true,
            isThreat = isThreat,
            isAbstain = isAbstain,
            isInvalid = false,
            threatTier = tier,
            riskScore = score,
            rawLogit = rawLogit,
            calibratedProbability = calProb,
            confidence = confidence,
            topReasonCodes = reasonCodes.take(3),
            topExplanations = explanations.take(3),
            evaluationLatencyMs = latency
        )
    }

    private data class Quad<A, B, C, D>(val first: A, val second: B, val third: C, val fourth: D)
}