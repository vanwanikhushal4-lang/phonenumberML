# AEGIS Call Guard & Call Screening Service Integration Guide

## 1. Architecture Overview
The Aegis Call Guard system integrates with Android's native `CallScreeningService` API:

```
                      [ INCOMING CALL ]
                             │
                             ▼
              [ AegisCallScreeningService ]
                             │
                             ▼
                    [ CallGuardEngine ]
                     ├── Local PNP2 Model (< 0.05 ms)
                     └── In-Memory LRU Reputation Cache
                             │
                             ▼
                  [ CallResponse.Builder ]
                   - setDisallowCall(false)  // Advisory Mode
                   - setRejectCall(false)    // Advisory Mode
                   - setSilenceCall(false)   // Advisory Mode
```

---

## 2. Android Manifest Registration
```xml
<service
    android:name="com.aegis.guard.phonenumber.AegisCallScreeningService"
    android:permission="android.permission.BIND_SCREENING_SERVICE"
    android:exported="true">
    <intent-filter>
        <action android:name="android.telecom.CallScreeningService" />
    </intent-filter>
</service>
```

---

## 3. Dependency Injection with Dagger / Hilt
```kotlin
@Module
@InstallIn(SingletonComponent::class)
object CallGuardModule {

    @Provides
    @Singleton
    fun providePhoneNumberRiskModel(@ApplicationContext context: Context): PhoneNumberRiskModel {
        val model = PhoneNumberRiskModel()
        context.assets.open("phonenumber_risk_model.json").use { stream ->
            val json = stream.bufferedReader().readText()
            model.loadModelFromJsonString(json)
        }
        return model
    }

    @Provides
    @Singleton
    fun provideCallGuardEngine(model: PhoneNumberRiskModel): CallGuardEngine {
        return CallGuardEngine(model)
    }
}
```

---

## 4. Advisory Mode Notification Banner
When a call is screened and exhibits suspicious patterns, an advisory banner is rendered:
```kotlin
val verdict = callGuardEngine.screenIncomingCall(rawNumber)
if (verdict.isAdvisoryWarning) {
    val notification = NotificationCompat.Builder(context, CHANNEL_ID)
        .setSmallIcon(R.drawable.ic_shield_alert)
        .setContentTitle(verdict.advisoryTitle)
        .setContentText(verdict.advisoryDetails.firstOrNull())
        .setPriority(NotificationCompat.PRIORITY_HIGH)
        .build()
    notificationManager.notify(NOTIFICATION_ID, notification)
}
```