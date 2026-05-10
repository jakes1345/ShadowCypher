package site.shadowcypher.app.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val ColorBackground = Color(0xFF09090B)
val ColorSurface = Color(0xFF111113)
val ColorSurfaceVariant = Color(0xFF1A1A1E)
val ColorBorder = Color(0xFF1F1F23)
val ColorAccentPurple = Color(0xFFB44AFF)
val ColorAccentPurpleContainer = Color(0xFF2A1040)
val ColorTextPrimary = Color(0xFFF8FAFC)
val ColorTextSecondary = Color(0xFF94A3B8)

val ColorCritical = Color(0xFFEF4444)
val ColorHigh = Color(0xFFF97316)
val ColorMedium = Color(0xFFEAB308)
val ColorLow = Color(0xFF22C55E)
val ColorOnline = Color(0xFF22C55E)
val ColorOffline = Color(0xFFEAB308)

private val DarkColors = darkColorScheme(
    primary = ColorAccentPurple,
    onPrimary = ColorTextPrimary,
    primaryContainer = ColorAccentPurpleContainer,
    onPrimaryContainer = ColorAccentPurple,
    secondary = ColorTextSecondary,
    onSecondary = ColorTextPrimary,
    background = ColorBackground,
    onBackground = ColorTextPrimary,
    surface = ColorSurface,
    onSurface = ColorTextPrimary,
    surfaceVariant = ColorSurfaceVariant,
    onSurfaceVariant = ColorTextSecondary,
    outline = ColorBorder,
    error = ColorCritical,
    onError = ColorTextPrimary,
)

@Composable
fun GuardianTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = DarkColors,
        content = content
    )
}
