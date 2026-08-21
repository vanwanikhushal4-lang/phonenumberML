plugins {
    id("com.android.library") version "8.2.2"
    id("org.jetbrains.kotlin.android") version "1.9.22"
}

android {
    namespace = "com.aegis.guard.phonenumber"
    compileSdk = 34

    defaultConfig {
        minSdk = 26
        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }
}

dependencies {
    implementation("com.googlecode.libphonenumber:libphonenumber:8.13.52")
    implementation("com.google.dagger:hilt-android:2.48")
    implementation("androidx.core:core-ktx:1.12.0")
    
    testImplementation("junit:junit:4.13.2")
    testImplementation("org.json:json:20231013")
}