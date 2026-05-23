package site.shadowcypher.app.ui.screen

import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import site.shadowcypher.app.data.GuardianSummary
import site.shadowcypher.app.data.Incident
import site.shadowcypher.app.ui.theme.*
import site.shadowcypher.app.viewmodel.GuardianViewModel

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DashboardScreen(
    viewModel: GuardianViewModel,
    onNavigateToSettings: () -> Unit
) {
    val summary by viewModel.summary.collectAsState()
    val me by viewModel.me.collectAsState()
    val isLoading by viewModel.isLoading.collectAsState()
    val error by viewModel.error.collectAsState()
    val apiKey by viewModel.apiKey.collectAsState()
    val scanTriggered by viewModel.scanTriggered.collectAsState()

    LaunchedEffect(scanTriggered) {
        if (scanTriggered) {
            viewModel.acknowledgeScanTriggered()
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .background(ColorBackground)
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 16.dp, vertical = 12.dp)
    ) {
        // Header
        Row(
            modifier = Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column {
                Text(
                    text = "SHADOWCYPHER",
                    color = ColorAccentPurple,
                    fontSize = 11.sp,
                    fontFamily = FontFamily.Monospace,
                    fontWeight = FontWeight.Bold,
                    letterSpacing = 2.sp
                )
                Text(
                    text = "Guardian",
                    color = ColorTextPrimary,
                    fontSize = 22.sp,
                    fontWeight = FontWeight.Bold
                )
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                if (isLoading) {
                    CircularProgressIndicator(
                        modifier = Modifier.size(20.dp),
                        color = ColorAccentPurple,
                        strokeWidth = 2.dp
                    )
                } else {
                    IconButton(onClick = { viewModel.refresh() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "Refresh", tint = ColorTextSecondary)
                    }
                }
            }
        }

        Spacer(Modifier.height(16.dp))

        // Setup card if no API key
        if (apiKey.isBlank()) {
            SetupCard(onNavigateToSettings)
            return@Column
        }

        // Error banner
        error?.let { errMsg ->
            Card(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(bottom = 12.dp),
                colors = CardDefaults.cardColors(containerColor = Color(0xFF2D0A0A)),
                shape = RoundedCornerShape(8.dp)
            ) {
                Row(
                    modifier = Modifier.padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(
                        text = errMsg,
                        color = ColorCritical,
                        fontSize = 13.sp,
                        modifier = Modifier.weight(1f)
                    )
                    TextButton(onClick = { viewModel.dismissError() }) {
                        Text("Dismiss", color = ColorTextSecondary, fontSize = 12.sp)
                    }
                }
            }
        }

        // Connection status
        summary?.let { s ->
            val anyOnline = s.agents.any { it.online }
            ConnectionStatusRow(anyOnline, s.agents.size)
            Spacer(Modifier.height(16.dp))
        }

        // Stat cards
        summary?.let { s ->
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                StatCard(
                    label = "DEVICES",
                    value = s.devices.size.toString(),
                    modifier = Modifier.weight(1f)
                )
                StatCard(
                    label = "INCIDENTS",
                    value = s.incidents.count { !it.resolved }.toString(),
                    valueColor = if (s.incidents.any { !it.resolved && it.severity == "CRITICAL" }) ColorCritical else ColorTextPrimary,
                    modifier = Modifier.weight(1f)
                )
            }
            Spacer(Modifier.height(8.dp))
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                StatCard(
                    label = "CVE ALERTS",
                    value = s.cve_alerts.size.toString(),
                    valueColor = if (s.cve_alerts.isNotEmpty()) ColorHigh else ColorTextPrimary,
                    modifier = Modifier.weight(1f)
                )
                StatCard(
                    label = "LAST SCAN",
                    value = s.last_scan_at?.take(10) ?: "—",
                    modifier = Modifier.weight(1f)
                )
            }
        } ?: run {
            if (!isLoading) {
                repeat(2) {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Box(modifier = Modifier.weight(1f).height(80.dp).background(ColorSurface, RoundedCornerShape(8.dp)))
                        Box(modifier = Modifier.weight(1f).height(80.dp).background(ColorSurface, RoundedCornerShape(8.dp)))
                    }
                    Spacer(Modifier.height(8.dp))
                }
            }
        }

        Spacer(Modifier.height(16.dp))

        // Trigger scan button
        Button(
            onClick = { viewModel.triggerScan() },
            modifier = Modifier.fillMaxWidth(),
            colors = ButtonDefaults.buttonColors(containerColor = ColorAccentPurple),
            shape = RoundedCornerShape(8.dp)
        ) {
            Text(
                text = if (isLoading) "SCANNING..." else "TRIGGER SCAN",
                fontFamily = FontFamily.Monospace,
                letterSpacing = 1.sp,
                fontWeight = FontWeight.Bold
            )
        }

        Spacer(Modifier.height(20.dp))

        // Recent incidents
        summary?.let { s ->
            val recent = s.incidents.filter { !it.resolved }.take(3)
            if (recent.isNotEmpty()) {
                SectionLabel("RECENT INCIDENTS")
                Spacer(Modifier.height(8.dp))
                recent.forEach { incident ->
                    IncidentPreviewRow(incident)
                    Spacer(Modifier.height(6.dp))
                }
                Spacer(Modifier.height(16.dp))
            }

            // Agent list
            if (s.agents.isNotEmpty()) {
                SectionLabel("AGENTS")
                Spacer(Modifier.height(8.dp))
                s.agents.forEach { agent ->
                    AgentRow(agent.hostname, agent.online, agent.last_seen_at)
                    Spacer(Modifier.height(6.dp))
                }
            }
        }

        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun SetupCard(onNavigateToSettings: () -> Unit) {
    Card(
        modifier = Modifier.fillMaxWidth(),
        colors = CardDefaults.cardColors(containerColor = ColorSurface),
        shape = RoundedCornerShape(12.dp),
        border = androidx.compose.foundation.BorderStroke(1.dp, ColorBorder)
    ) {
        Column(
            modifier = Modifier.padding(24.dp),
            horizontalAlignment = Alignment.CenterHorizontally
        ) {
            Text(
                text = "API KEY REQUIRED",
                color = ColorAccentPurple,
                fontSize = 11.sp,
                fontFamily = FontFamily.Monospace,
                letterSpacing = 2.sp,
                fontWeight = FontWeight.Bold
            )
            Spacer(Modifier.height(8.dp))
            Text(
                text = "Connect to ShadowCypher Guardian",
                color = ColorTextPrimary,
                fontSize = 16.sp,
                fontWeight = FontWeight.SemiBold
            )
            Spacer(Modifier.height(4.dp))
            Text(
                text = "Enter your API key in Settings to start monitoring your network.",
                color = ColorTextSecondary,
                fontSize = 13.sp
            )
            Spacer(Modifier.height(16.dp))
            Button(
                onClick = onNavigateToSettings,
                colors = ButtonDefaults.buttonColors(containerColor = ColorAccentPurple),
                shape = RoundedCornerShape(8.dp)
            ) {
                Icon(Icons.Default.Settings, contentDescription = null, modifier = Modifier.size(16.dp))
                Spacer(Modifier.width(8.dp))
                Text("Go to Settings", fontWeight = FontWeight.Bold)
            }
        }
    }
}

@Composable
private fun ConnectionStatusRow(anyOnline: Boolean, agentCount: Int) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(ColorSurface, RoundedCornerShape(8.dp))
            .border(1.dp, ColorBorder, RoundedCornerShape(8.dp))
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(10.dp)
                .clip(CircleShape)
                .background(if (anyOnline) ColorOnline else ColorOffline)
        )
        Spacer(Modifier.width(10.dp))
        Text(
            text = if (anyOnline) "CONNECTED" else "AGENT OFFLINE",
            color = if (anyOnline) ColorOnline else ColorOffline,
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold,
            letterSpacing = 1.sp
        )
        Spacer(Modifier.weight(1f))
        Text(
            text = "$agentCount agent${if (agentCount != 1) "s" else ""}",
            color = ColorTextSecondary,
            fontSize = 12.sp
        )
    }
}

@Composable
private fun StatCard(
    label: String,
    value: String,
    modifier: Modifier = Modifier,
    valueColor: Color = ColorTextPrimary
) {
    Column(
        modifier = modifier
            .background(ColorSurface, RoundedCornerShape(8.dp))
            .border(1.dp, ColorBorder, RoundedCornerShape(8.dp))
            .padding(14.dp)
    ) {
        Text(
            text = label,
            color = ColorTextSecondary,
            fontSize = 10.sp,
            fontFamily = FontFamily.Monospace,
            letterSpacing = 1.5.sp,
            fontWeight = FontWeight.Medium
        )
        Spacer(Modifier.height(6.dp))
        Text(
            text = value,
            color = valueColor,
            fontSize = 26.sp,
            fontWeight = FontWeight.Bold
        )
    }
}

@Composable
private fun SectionLabel(text: String) {
    Text(
        text = text,
        color = ColorTextSecondary,
        fontSize = 10.sp,
        fontFamily = FontFamily.Monospace,
        letterSpacing = 2.sp,
        fontWeight = FontWeight.Bold
    )
}

@Composable
private fun IncidentPreviewRow(incident: Incident) {
    val severityColor = when (incident.severity.orEmpty().uppercase()) {
        "CRITICAL" -> ColorCritical
        "HIGH" -> ColorHigh
        "MEDIUM" -> ColorMedium
        else -> ColorLow
    }
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(ColorSurface, RoundedCornerShape(8.dp))
            .border(1.dp, ColorBorder, RoundedCornerShape(8.dp))
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .width(3.dp)
                .height(36.dp)
                .background(severityColor, RoundedCornerShape(2.dp))
        )
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                SeverityBadge(incident.severity.orEmpty())
                Text(
                    text = incident.type.orEmpty(),
                    color = ColorTextPrimary,
                    fontSize = 13.sp,
                    fontWeight = FontWeight.SemiBold,
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            Spacer(Modifier.height(2.dp))
            Text(
                text = incident.description.orEmpty(),
                color = ColorTextSecondary,
                fontSize = 12.sp,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
        }
    }
}

@Composable
private fun AgentRow(hostname: String, online: Boolean, lastSeen: String?) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(ColorSurface, RoundedCornerShape(8.dp))
            .border(1.dp, ColorBorder, RoundedCornerShape(8.dp))
            .padding(12.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Box(
            modifier = Modifier
                .size(8.dp)
                .clip(CircleShape)
                .background(if (online) ColorOnline else ColorOffline)
        )
        Spacer(Modifier.width(10.dp))
        Text(
            text = hostname,
            color = ColorTextPrimary,
            fontSize = 13.sp,
            fontFamily = FontFamily.Monospace,
            modifier = Modifier.weight(1f)
        )
        Text(
            text = if (online) "ONLINE" else lastSeen?.take(10) ?: "OFFLINE",
            color = if (online) ColorOnline else ColorTextSecondary,
            fontSize = 11.sp,
            fontFamily = FontFamily.Monospace,
            letterSpacing = 0.5.sp
        )
    }
}

@Composable
fun SeverityBadge(severity: String) {
    val (color, bg) = when (severity.orEmpty().uppercase()) {
        "CRITICAL" -> ColorCritical to Color(0xFF2D0A0A)
        "HIGH" -> ColorHigh to Color(0xFF2D1500)
        "MEDIUM" -> ColorMedium to Color(0xFF2D2200)
        else -> ColorLow to Color(0xFF0A2D0A)
    }
    Box(
        modifier = Modifier
            .background(bg, RoundedCornerShape(4.dp))
            .padding(horizontal = 6.dp, vertical = 2.dp)
    ) {
        Text(
            text = severity.orEmpty().uppercase(),
            color = color,
            fontSize = 9.sp,
            fontFamily = FontFamily.Monospace,
            fontWeight = FontWeight.Bold,
            letterSpacing = 0.5.sp
        )
    }
}
