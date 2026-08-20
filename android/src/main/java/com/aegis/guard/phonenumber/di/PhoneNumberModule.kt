package com.aegis.guard.phonenumber.di

import android.content.Context
import com.aegis.guard.phonenumber.CallGuardEngine
import com.aegis.guard.phonenumber.PhoneNumberRiskModel
import java.io.InputStreamReader

/**
 * Dependency Injection Module for AEGIS Call Guard.
 * Provides Singleton instances of PhoneNumberRiskModel and CallGuardEngine.
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
    fun provideCallGuardEngine(context: Context): CallGuardEngine {
        if (engineInstance == null) {
            val model = providePhoneNumberRiskModel(context)
            engineInstance = CallGuardEngine(model)
        }
        return engineInstance!!
    }
}