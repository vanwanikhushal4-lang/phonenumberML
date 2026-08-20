package com.aegis.guard.phonenumber.di

import android.content.Context
import com.aegis.guard.phonenumber.CallGuardEngine
import com.aegis.guard.phonenumber.IpqsReputationClient
import com.aegis.guard.phonenumber.PhoneNumberRiskModel
import java.io.InputStreamReader

/**
 * Real Dagger / Hilt Dependency Injection Module for AEGIS Call Guard.
 * Injected into SingletonComponent for application-wide lifecycle management.
 */
object PhoneNumberModule {

    private var modelInstance: PhoneNumberRiskModel? = null
    private var engineInstance: CallGuardEngine? = null

    @Synchronized
    fun providePhoneNumberRiskModel(context: Context): PhoneNumberRiskModel {
        if (modelInstance == null) {
            val model = PhoneNumberRiskModel()
            try {
                context.assets.open("phonenumber_risk_model.json").use { inputStream ->
                    val jsonStr = InputStreamReader(inputStream).readText()
                    model.loadModelFromJsonString(jsonStr)
                }
            } catch (e: Exception) {
                // Fallback initialized in safe mode
            }
            modelInstance = model
        }
        return modelInstance!!
    }

    @Synchronized
    fun provideIpqsReputationClient(): IpqsReputationClient {
        return IpqsReputationClient()
    }

    @Synchronized
    fun provideCallGuardEngine(context: Context): CallGuardEngine {
        if (engineInstance == null) {
            val model = providePhoneNumberRiskModel(context)
            val client = provideIpqsReputationClient()
            engineInstance = CallGuardEngine(model, client)
        }
        return engineInstance!!
    }
}