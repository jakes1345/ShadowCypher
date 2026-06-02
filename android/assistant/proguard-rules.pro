# ShadowCypher Shadow AI — ProGuard rules

-keepattributes SourceFile,LineNumberTable,Signature,*Annotation*
-renamesourcefileattribute SourceFile

# WebView JS interface — must keep all @JavascriptInterface methods
-keep class site.shadowcypher.assistant.** { *; }
-keepclassmembers class * {
    @android.webkit.JavascriptInterface <methods>;
}

# Vosk offline STT
-keep class org.vosk.** { *; }
-dontwarn org.vosk.**

# ONNX Runtime (wake word)
-keep class ai.onnxruntime.** { *; }
-dontwarn ai.onnxruntime.**

# Kotlin coroutines
-keepclassmembers class kotlinx.coroutines.** { *; }
-dontwarn kotlinx.coroutines.**

# AppCompat / AndroidX
-dontwarn androidx.**
