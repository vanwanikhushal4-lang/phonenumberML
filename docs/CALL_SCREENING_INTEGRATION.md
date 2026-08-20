# AEGIS Call Guard & Call Screening Service Integration Guide

## 1. Android Telecom CallScreeningService Architecture
Android `CallScreeningService` allows Aegis to inspect incoming phone calls in real time before the phone rings.

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
```

## 2. Advisory Mode Implementation
The service must strictly operate in Advisory Mode by default. It displays a notification/overlay warning the user of suspicious patterns while allowing the call to ring:

```kotlin
val verdict = callGuardEngine.screenIncomingCall(rawNumber)
if (verdict.isAdvisoryWarning) {
    // Show advisory overlay banner
    showWarningNotification(verdict.advisoryTitle, verdict.advisoryDetails)
}
```