package site.shadowcypher.app.ui.screen

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.*
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import site.shadowcypher.app.ui.theme.*

@Composable
fun EcosystemScreen() {
    val context = LocalContext.current

    fun openUrl(url: String) {
        context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(url)))
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ColorBackground)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 8.dp)
    ) {
        // Header
        Text(
            "SHADOWCYPHER",
            fontSize = 10.sp,
            letterSpacing = 3.sp,
            color = ColorAccentPurple,
            fontFamily = FontFamily.Monospace,
            modifier = Modifier.padding(top = 8.dp, bottom = 2.dp)
        )
        Text(
            "Ecosystem",
            fontSize = 28.sp,
            fontWeight = FontWeight.Bold,
            color = ColorTextPrimary,
            modifier = Modifier.padding(bottom = 4.dp)
        )
        Text(
            "Sovereign security tools. Local-first. No cloud middleman.",
            fontSize = 13.sp,
            color = ColorTextSecondary,
            modifier = Modifier.padding(bottom = 24.dp)
        )

        // Website card
        EcoCard(
            icon = Icons.Default.Language,
            title = "shadowcypher.site",
            subtitle = "Account, API key, dashboard",
            accent = ColorAccentPurple,
            onClick = { openUrl("https://shadowcypher.site") }
        )

        Spacer(Modifier.height(10.dp))

        // Apps section
        SectionLabel("APPS")
        Spacer(Modifier.height(8.dp))

        EcoCard(
            icon = Icons.Default.Shield,
            title = "Guardian",
            subtitle = "Network monitor · Devices · Incidents · CVEs",
            accent = ColorAccentPurple,
            badge = "Installed",
            badgeColor = ColorOnline,
            onClick = null
        )

        Spacer(Modifier.height(8.dp))

        EcoCard(
            icon = Icons.Default.Mic,
            title = "Shadow AI",
            subtitle = "Voice assistant · Security-aware · Always ready",
            accent = Color(0xFF00E0A4),
            onClick = {
                runCatching {
                    val intent = context.packageManager
                        .getLaunchIntentForPackage("site.shadowcypher.assistant")
                    if (intent != null) context.startActivity(intent)
                    else openUrl("https://shadowcypher.site/shadow-ai")
                }
            }
        )

        Spacer(Modifier.height(16.dp))

        // ShadowOS section
        SectionLabel("SHADOWOS")
        Spacer(Modifier.height(8.dp))

        EcoCard(
            icon = Icons.Default.Computer,
            title = "ShadowOS",
            subtitle = "Arch-based sovereign Linux distro. Dev · Normal · Pentest modes.",
            accent = Color(0xFF00D4FF),
            onClick = { openUrl("https://shadowcypher.site/shadowos") }
        )

        Spacer(Modifier.height(8.dp))

        EcoCard(
            icon = Icons.Default.Download,
            title = "Download ShadowOS ISO",
            subtitle = "Latest release · Bootable USB · x86_64",
            accent = Color(0xFF00D4FF),
            onClick = { openUrl("https://shadowcypher.site/shadowos#download") }
        )

        Spacer(Modifier.height(16.dp))

        // Guardian Agent section
        SectionLabel("GUARDIAN AGENT")
        Spacer(Modifier.height(8.dp))

        EcoCard(
            icon = Icons.Default.Terminal,
            title = "Install Agent on Linux",
            subtitle = "One command — systemd service that powers this app",
            accent = ColorAccentPurple,
            onClick = { openUrl("https://shadowcypher.site/agent") }
        )

        Spacer(Modifier.height(8.dp))

        // Install command box
        Box(
            modifier = Modifier
                .fillMaxWidth()
                .clip(RoundedCornerShape(10.dp))
                .background(ColorSurfaceVariant)
                .border(1.dp, ColorBorder, RoundedCornerShape(10.dp))
                .padding(14.dp)
        ) {
            Column {
                Text(
                    "INSTALL COMMAND",
                    fontSize = 9.sp,
                    letterSpacing = 2.sp,
                    color = ColorTextSecondary,
                    fontFamily = FontFamily.Monospace,
                    modifier = Modifier.padding(bottom = 6.dp)
                )
                Text(
                    "curl -sSL https://shadowcypher.site/agent/install.sh | bash",
                    fontSize = 11.sp,
                    color = Color(0xFF00E0A4),
                    fontFamily = FontFamily.Monospace,
                    lineHeight = 16.sp
                )
            }
        }

        Spacer(Modifier.height(16.dp))

        // Open source section
        SectionLabel("OPEN SOURCE")
        Spacer(Modifier.height(8.dp))

        EcoCard(
            icon = Icons.Default.Code,
            title = "GitHub",
            subtitle = "github.com/jakes1345/ShadowCypher",
            accent = ColorTextSecondary,
            onClick = { openUrl("https://github.com/jakes1345/ShadowCypher") }
        )

        Spacer(Modifier.height(24.dp))

        // Version footer
        Text(
            "Guardian v2.1  ·  shadowcypher.site",
            fontSize = 11.sp,
            color = Color(0xFF3A3A4A),
            fontFamily = FontFamily.Monospace,
            modifier = Modifier
                .align(Alignment.CenterHorizontally)
                .padding(bottom = 16.dp)
        )
    }
}

@Composable
private fun SectionLabel(text: String) {
    Text(
        text,
        fontSize = 9.sp,
        letterSpacing = 2.sp,
        color = ColorTextSecondary.copy(alpha = 0.6f),
        fontFamily = FontFamily.Monospace
    )
}

@Composable
private fun EcoCard(
    icon: ImageVector,
    title: String,
    subtitle: String,
    accent: Color,
    badge: String? = null,
    badgeColor: Color = ColorOnline,
    onClick: (() -> Unit)?
) {
    val modifier = Modifier
        .fillMaxWidth()
        .clip(RoundedCornerShape(12.dp))
        .background(ColorSurface)
        .border(1.dp, ColorBorder, RoundedCornerShape(12.dp))
        .then(if (onClick != null) Modifier.clickable { onClick() } else Modifier)
        .padding(14.dp)

    Row(modifier = modifier, verticalAlignment = Alignment.CenterVertically) {
        Box(
            modifier = Modifier
                .size(44.dp)
                .clip(RoundedCornerShape(10.dp))
                .background(accent.copy(alpha = 0.12f)),
            contentAlignment = Alignment.Center
        ) {
            Icon(icon, contentDescription = null, tint = accent, modifier = Modifier.size(22.dp))
        }

        Spacer(Modifier.width(12.dp))

        Column(modifier = Modifier.weight(1f)) {
            Text(title, fontSize = 14.sp, fontWeight = FontWeight.SemiBold, color = ColorTextPrimary)
            Text(subtitle, fontSize = 12.sp, color = ColorTextSecondary, lineHeight = 16.sp)
        }

        if (badge != null) {
            Text(
                badge,
                fontSize = 9.sp,
                letterSpacing = 1.sp,
                color = badgeColor,
                fontFamily = FontFamily.Monospace,
                modifier = Modifier
                    .clip(RoundedCornerShape(4.dp))
                    .background(badgeColor.copy(alpha = 0.1f))
                    .padding(horizontal = 6.dp, vertical = 3.dp)
            )
        } else if (onClick != null) {
            Icon(
                Icons.Default.ChevronRight,
                contentDescription = null,
                tint = ColorTextSecondary.copy(alpha = 0.4f),
                modifier = Modifier.size(18.dp)
            )
        }
    }
}
